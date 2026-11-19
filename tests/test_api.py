from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models import *
from app.core.security import create_access_token, hash_password


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=__import__("sqlalchemy").pool.StaticPool)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def token(client, role_email, password):
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter(User.email == role_email).first()
    assert user is not None
    return {"Authorization": f"Bearer {create_access_token(user)}"}


def setup_users(db):
    admin = User(email="admin@test", password_hash=hash_password("Password1"), full_name="Admin",
                 phone="9000000001", role=Role.ADMIN)
    owner = User(email="owner@test", password_hash=hash_password("Password1"), full_name="Owner",
                 phone="9000000002", role=Role.RESTAURANT_OWNER)
    owner2 = User(email="owner2@test", password_hash=hash_password("Password1"), full_name="Owner Two",
                  phone="9000000003", role=Role.RESTAURANT_OWNER)
    customer = User(email="customer@test", password_hash=hash_password("Password1"), full_name="Customer",
                    phone="9000000004", role=Role.CUSTOMER)
    agent = User(email="agent@test", password_hash=hash_password("Password1"), full_name="Agent",
                 phone="9000000005", role=Role.DELIVERY_AGENT)
    db.add_all([admin, owner, owner2, customer, agent])
    db.flush()
    return admin, owner, owner2, customer, agent


def test_register_login_health(client):
    assert client.get("/health").status_code == 200
    response = client.post("/auth/register", json={
        "email": "new@test.com", "password": "Password1", "full_name": "New User", "phone": "9000000010"})
    assert response.status_code == 201
    login = client.post("/auth/login", data={"username": "new@test.com", "password": "Password1"})
    assert login.status_code == 200


def test_auth_failure_and_role(client):
    assert client.post("/auth/login", data={"username": "none@test", "password": "bad"}).status_code == 401
    response = client.post("/auth/register", json={
        "email": "customer@test.com", "password": "Password1", "full_name": "Customer", "phone": "9000000011"})
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.post("/restaurants", json={
        "name": "Forbidden", "cuisine": "Indian", "city": "Chennai", "address": "Main Road",
        "opens_at": "08:00:00", "closes_at": "23:00:00"}, headers=headers).status_code == 403


def test_validation_failure(client):
    response = client.post("/auth/register", json={
        "email": "invalid", "password": "x", "full_name": "x", "phone": "1"})
    assert response.status_code == 422


def test_admin_can_onboard_managed_accounts(client):
    db = next(app.dependency_overrides[get_db]())
    setup_users(db)
    admin_headers = token(client, "admin@test", "Password1")
    customer_headers = token(client, "customer@test", "Password1")
    created = client.post("/auth/users", headers=admin_headers, json={
        "email": "new.agent@example.com", "password": "Password1", "full_name": "New Agent",
        "phone": "9000000012", "role": "DELIVERY_AGENT"})
    assert created.status_code == 201
    assert created.json()["role"] == "DELIVERY_AGENT"
    denied = client.post("/auth/users", headers=customer_headers, json={
        "email": "other.agent@example.com", "password": "Password1", "full_name": "Other Agent",
        "phone": "9000000013", "role": "DELIVERY_AGENT"})
    assert denied.status_code == 403


def test_pricing_ignores_tampered_price_and_transition(client):
    db = next(app.dependency_overrides[get_db]())
    _, owner, _, customer, agent = setup_users(db)
    restaurant = Restaurant(owner_id=owner.id, name="Test Kitchen", cuisine="Indian", city="Chennai",
                            address="Main Road", opens_at=time(8, 0), closes_at=time(23, 0),
                            is_open=True, avg_rating=0)
    db.add(restaurant)
    db.flush()
    category = MenuCategory(restaurant_id=restaurant.id, name="Meals", display_order=1)
    db.add(category)
    db.flush()
    item = MenuItem(restaurant_id=restaurant.id, category_id=category.id, name="Biryani",
                    price=Decimal("100.00"), is_available=True, is_deleted=False)
    db.add(item)
    address = Address(user_id=customer.id, line1="10 Road", city="Chennai", pincode="600001", is_default=True)
    db.add(address)
    db.commit()
    owner_headers = token(client, "owner@test", "Password1")
    customer_headers = token(client, "customer@test", "Password1")
    response = client.post("/orders", headers=customer_headers, json={
        "restaurant_id": restaurant.id, "address_id": address.id,
        "items": [{"menu_item_id": item.id, "quantity": 2, "price": "1"}]})
    assert response.status_code == 201
    order = response.json()
    assert Decimal(order["item_total"]) == Decimal("200.00")
    assert Decimal(order["grand_total"]) == Decimal("250.00")

    bad = client.patch(f"/orders/{order['id']}/status", headers=owner_headers,
                       json={"status": "DELIVERED"})
    assert bad.status_code == 409


def test_owner_cannot_edit_another_restaurants_menu(client):
    db = next(app.dependency_overrides[get_db]())
    _, owner, owner2, _, _ = setup_users(db)
    owner_headers = token(client, "owner@test", "Password1")
    owner2_headers = token(client, "owner2@test", "Password1")

    def create_restaurant(headers, name):
        response = client.post("/restaurants", headers=headers, json={
            "name": name, "cuisine": "Indian", "city": "Chennai", "address": "Main Road",
            "opens_at": "08:00:00", "closes_at": "23:00:00"})
        assert response.status_code == 201

    create_restaurant(owner_headers, "First Kitchen")
    create_restaurant(owner2_headers, "Second Kitchen")
    category = client.post("/restaurants/me/menu-categories", headers=owner_headers,
                           json={"name": "Meals", "display_order": 1})
    other_category = client.post("/restaurants/me/menu-categories", headers=owner2_headers,
                                 json={"name": "Other Meals"})
    item = client.post("/restaurants/me/menu-items", headers=owner_headers, json={
        "category_id": category.json()["id"], "name": "Rice", "price": "25.00"})
    assert category.status_code == other_category.status_code == item.status_code == 201

    response = client.put(f"/menu-items/{item.json()['id']}", headers=owner2_headers,
                          json={"name": "Hacked", "price": "1.00"})
    assert response.status_code == 404
    assert response.json()["code"] == "MENU_ITEM_NOT_FOUND"
    invalid_category = client.put(f"/menu-items/{item.json()['id']}", headers=owner_headers,
                                  json={"category_id": other_category.json()["id"]})
    assert invalid_category.status_code == 404
    assert invalid_category.json()["code"] == "CATEGORY_NOT_FOUND"


def test_customer_addresses_can_be_updated_and_default_is_exclusive(client):
    db = next(app.dependency_overrides[get_db]())
    _, _, _, customer, _ = setup_users(db)
    headers = token(client, "customer@test", "Password1")
    first = client.post("/addresses", headers=headers, json={
        "line1": "First Road", "city": "Chennai", "pincode": "600001", "is_default": True})
    second = client.post("/addresses", headers=headers, json={
        "line1": "Second Road", "city": "Chennai", "pincode": "600002", "is_default": True})
    assert first.status_code == second.status_code == 201
    addresses = client.get("/addresses", headers=headers).json()
    assert [address["is_default"] for address in addresses] == [True, False]

    response = client.patch(f"/addresses/{first.json()['id']}", headers=headers,
                            json={"line1": "Updated Road", "is_default": True})
    assert response.status_code == 200
    addresses = client.get("/addresses", headers=headers).json()
    assert addresses[0]["id"] == first.json()["id"]
    assert addresses[0]["line1"] == "Updated Road"
    assert [address["is_default"] for address in addresses] == [True, False]

    profile = client.get("/customers/me", headers=headers)
    assert profile.status_code == 200
    assert "password_hash" not in profile.json()
    updated_profile = client.put("/customers/me", headers=headers, json={
        "full_name": "Updated Customer", "phone": "9000000099"})
    assert updated_profile.status_code == 200
    assert updated_profile.json()["full_name"] == "Updated Customer"
    assert "password_hash" not in updated_profile.json()

    other_user_headers = token(client, "owner@test", "Password1")
    hidden = client.patch(f"/addresses/{first.json()['id']}", headers=other_user_headers,
                          json={"line1": "Private"})
    assert hidden.status_code == 403


def test_order_lifecycle_contact_privacy_rating_and_reports(client):
    db = next(app.dependency_overrides[get_db]())
    _, owner, _, customer, agent = setup_users(db)
    admin_headers = token(client, "admin@test", "Password1")
    owner_headers = token(client, "owner@test", "Password1")
    customer_headers = token(client, "customer@test", "Password1")
    agent_headers = token(client, "agent@test", "Password1")

    restaurant = client.post("/restaurants", headers=owner_headers, json={
        "name": "Lifecycle Kitchen", "cuisine": "Indian", "city": "Chennai", "address": "Main Road",
        "opens_at": "08:00:00", "closes_at": "23:00:00"}).json()
    category = client.post("/restaurants/me/menu-categories", headers=owner_headers,
                           json={"name": "Meals"}).json()
    item = client.post("/restaurants/me/menu-items", headers=owner_headers, json={
        "category_id": category["id"], "name": "Biryani", "price": "100.00"}).json()
    address = client.post("/addresses", headers=customer_headers, json={
        "line1": "10 Road", "city": "Chennai", "pincode": "600001"}).json()

    def place_order():
        return client.post("/orders", headers=customer_headers, json={
            "restaurant_id": restaurant["id"], "address_id": address["id"],
            "items": [{"menu_item_id": item["id"], "quantity": 1, "price": "0.01"}]})

    closed = client.patch("/restaurants/me/open-status", headers=owner_headers,
                          json={"is_open": False})
    assert closed.status_code == 200
    assert place_order().json()["code"] == "RESTAURANT_CLOSED"
    client.patch("/restaurants/me/open-status", headers=owner_headers, json={"is_open": True})
    availability = client.patch(f"/menu-items/{item['id']}/availability", headers=owner_headers,
                                json={"is_available": False})
    assert availability.status_code == 200
    assert place_order().json()["code"] == "ITEM_UNAVAILABLE"
    client.patch(f"/menu-items/{item['id']}/availability", headers=owner_headers,
                json={"is_available": True})

    first = place_order()
    second = place_order()
    assert first.status_code == second.status_code == 201
    assert first.json()["order_no"] != second.json()["order_no"]
    first_id, second_id = first.json()["id"], second.json()["id"]
    assert first.json()["address"]["line1"] == "10 Road"
    assert [row["to_status"] for row in first.json()["history"]] == ["PLACED"]
    updated_item = client.put(f"/menu-items/{item['id']}", headers=owner_headers,
                              json={"price": "120.00"})
    assert updated_item.status_code == 200
    historical_order = client.get(f"/orders/{first.json()['id']}", headers=customer_headers).json()
    assert historical_order["items"][0]["unit_price_snapshot"] == "100.00"
    assert historical_order["item_total"] == "100.00"

    stranger_response = client.post("/auth/register", json={
        "email": "stranger@example.com", "password": "Password1",
        "full_name": "Stranger", "phone": "9000000098"})
    assert stranger_response.status_code == 201
    stranger_headers = {"Authorization": f"Bearer {stranger_response.json()['access_token']}"}
    assert client.get(f"/orders/{first_id}", headers=stranger_headers).status_code == 403
    assert client.get(f"/orders/{first_id}", headers=agent_headers).status_code == 403

    owner_orders = client.get("/orders/restaurant", headers=owner_headers)
    assert owner_orders.status_code == 200
    assert len(owner_orders.json()["items"]) == 2
    agent_orders = client.get("/orders/agent", headers=agent_headers)
    assert agent_orders.status_code == 200
    assert agent_orders.json()["items"] == []

    for next_status in ("CONFIRMED", "PREPARING", "READY_FOR_PICKUP"):
        changed = client.patch(f"/orders/{first_id}/status", headers=owner_headers,
                               json={"status": next_status})
        assert changed.status_code == 200
        second_changed = client.patch(f"/orders/{second_id}/status", headers=owner_headers,
                                      json={"status": next_status})
        assert second_changed.status_code == 200
    assigned = client.patch(f"/orders/{first_id}/assign-agent", headers=admin_headers,
                            json={"agent_id": agent.id})
    assert assigned.status_code == 200
    not_available = client.patch(f"/orders/{second_id}/assign-agent", headers=admin_headers,
                                 json={"agent_id": agent.id})
    assert not_available.status_code == 409
    assert not_available.json()["code"] == "AGENT_UNAVAILABLE"

    before_pickup = client.get(f"/orders/{first_id}", headers=agent_headers)
    assert before_pickup.status_code == 200
    assert before_pickup.json()["customer_phone"] is None
    pickup = client.patch(f"/orders/{first_id}/delivery-status", headers=agent_headers,
                          json={"status": "PICKED_UP"})
    assert pickup.status_code == 200
    after_pickup = client.get(f"/orders/{first_id}", headers=agent_headers)
    assert after_pickup.json()["customer_phone"] == customer.phone
    delivered = client.patch(f"/orders/{first_id}/delivery-status", headers=agent_headers,
                             json={"status": "DELIVERED"})
    assert delivered.status_code == 200
    assigned_second = client.patch(f"/orders/{second_id}/assign-agent", headers=admin_headers,
                                   json={"agent_id": agent.id})
    assert assigned_second.status_code == 200
    assert client.patch(f"/orders/{second_id}/delivery-status", headers=agent_headers,
                        json={"status": "PICKED_UP"}).status_code == 200
    assert client.patch(f"/orders/{second_id}/delivery-status", headers=agent_headers,
                        json={"status": "DELIVERED"}).status_code == 200
    history = client.get(f"/orders/{first_id}", headers=customer_headers).json()["history"]
    assert [row["to_status"] for row in history] == [
        "PLACED", "CONFIRMED", "PREPARING", "READY_FOR_PICKUP", "PICKED_UP", "DELIVERED"]

    rating = client.post(f"/orders/{first_id}/rating", headers=customer_headers, json={
        "restaurant_rating": 5, "agent_rating": 4, "comment": "Great"})
    assert rating.status_code == 201
    assert client.post(f"/orders/{first_id}/rating", headers=customer_headers, json={
        "restaurant_rating": 5, "agent_rating": 5}).status_code == 409
    second_rating = client.post(f"/orders/{second_id}/rating", headers=customer_headers, json={
        "restaurant_rating": 4, "agent_rating": 4})
    assert second_rating.status_code == 201
    public_restaurant = client.get(f"/restaurants/{restaurant['id']}/menu")
    assert public_restaurant.status_code == 200
    search = client.get("/restaurants?city=Chennai&cuisine=Indian&name=Lifecycle")
    assert search.json()["total"] == 1
    assert float(search.json()["items"][0]["avg_rating"]) == 4.5

    third = place_order().json()
    cancel_order = client.patch(f"/orders/{third['id']}/cancel", headers=customer_headers)
    assert cancel_order.status_code == 200
    assert client.get("/orders/me", headers=customer_headers).json()["total"] == 3
    sales = client.get("/reports/restaurant-sales", headers=owner_headers).json()
    assert sales["total"] == 1
    assert sales["items"][0]["order_count"] == 2
    cancellation = client.get("/reports/cancellation-rate", headers=owner_headers).json()
    assert round(cancellation["items"][0]["cancellation_rate"], 1) == 33.3
    performance = client.get("/reports/agent-performance", headers=agent_headers).json()
    assert performance["items"][0]["delivered_orders"] == 2
    assert performance["items"][0]["average_rating"] == 4.0
