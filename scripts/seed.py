import sys
from pathlib import Path
from datetime import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.security import hash_password
from app.models import *

Base.metadata.create_all(engine)
db = SessionLocal()

if db.query(User).count() == 0:
    users = [
        User(email="admin@food.test", password_hash=hash_password("Admin123!"), full_name="System Admin",
             phone="9000000001", role=Role.ADMIN),
        User(email="owner@food.test", password_hash=hash_password("Owner123!"), full_name="Restaurant Owner",
             phone="9000000002", role=Role.RESTAURANT_OWNER),
        User(email="customer@food.test", password_hash=hash_password("Customer123!"), full_name="Demo Customer",
             phone="9000000003", role=Role.CUSTOMER),
        User(email="agent@food.test", password_hash=hash_password("Agent123!"), full_name="Delivery Agent",
             phone="9000000004", role=Role.DELIVERY_AGENT),
    ]
    db.add_all(users)
    db.flush()
    restaurant = Restaurant(owner_id=users[1].id, name="Tasty Bites", cuisine="Indian",
                            city="Chennai", address="12 Main Road", opens_at=time(8, 0),
                            closes_at=time(23, 0), is_open=True, avg_rating=0)
    db.add(restaurant)
    db.flush()
    category = MenuCategory(restaurant_id=restaurant.id, name="Main Course", display_order=1)
    db.add(category)
    db.flush()
    db.add_all([
        MenuItem(restaurant_id=restaurant.id, category_id=category.id, name="Veg Biryani",
                 description="Fragrant vegetable biryani", price=180, is_veg=True,
                 is_available=True, is_deleted=False),
        MenuItem(restaurant_id=restaurant.id, category_id=category.id, name="Chicken Curry",
                 description="Home-style chicken curry", price=220, is_veg=False,
                 is_available=True, is_deleted=False),
    ])
    db.commit()
print("Seed completed")
db.close()
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

