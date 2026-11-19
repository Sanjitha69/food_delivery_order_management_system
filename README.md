# Food Delivery Order Management API

FastAPI backend for a regional food-delivery aggregator. It implements JWT authentication and RBAC for admins, restaurant owners, customers, and delivery agents.

## Setup

Python 3.11+ is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\seed.py
python -m uvicorn app.main:app --reload --port 8001
```

Open Swagger at `http://127.0.0.1:8001/docs`.

## Environment

Copy `.env.example` to `.env`. `DATABASE_URL` defaults to a local SQLite file for development. Set `JWT_SECRET` securely in production. Database, tax, delivery fee, token expiry, and CORS settings are environment-driven.

## Database migrations

The default database is created at startup for convenience. Alembic is configured for explicit migration workflows:

```powershell
alembic upgrade head
```

Generate migrations from model changes with `alembic revision --autogenerate -m "describe change"`.

## Demo users

The seed script creates:

| Role | Email | Password |
|---|---|---|
| Admin | admin@food.test | Admin123! |
| Restaurant owner | owner@food.test | Owner123! |
| Customer | customer@food.test | Customer123! |
| Delivery agent | agent@food.test | Agent123! |

## Tests

```powershell
python -m pytest -q --cov=app --cov-report=term-missing
```

Tests cover registration/login, admin onboarding, role authorization, validation, pricing, menu ownership, customer addresses/profile, order status history, delivery privacy, ratings, and reports. The current suite passes with 94% coverage.

## Module layout

```text
app/
  core/       settings, JWT/password security, shared rate limiter
  db/         SQLAlchemy base, engine, and session dependency
  models/     relational entities and enums
  schemas/    request/response validation, separated by feature
  routers/    auth, restaurants, menu, customers, orders, delivery, ratings, reports
  services/   catalogue, customer, order, delivery, and rating business rules
tests/
  test_api.py  end-to-end API and authorization tests
```

Delivery and rating are independent feature modules:

- Delivery routes/schemas/business logic: `app/routers/delivery.py`, `app/schemas/delivery.py`, `app/services/delivery_service.py`.
- Rating routes/schemas/business logic: `app/routers/ratings.py`, `app/schemas/ratings.py`, `app/services/rating_service.py`.

## API notes

- List endpoints accept `page`, `size`, and where applicable `sort`.
- `/auth/users` is restricted to admins and creates restaurant-owner or delivery-agent accounts.
- Customers can update their profile and maintain multiple addresses; `PATCH /addresses/{id}` updates an address and can make it the default.
- Restaurant owners manage their own restaurant and menu. Menu ownership is derived from the JWT user, and moving an item into another restaurant's category is rejected.
- Orders are server-priced, save item name/price snapshots, and expose their address and transition history to authorized participants.
- Customer contact numbers are withheld from delivery agents until the order is picked up.
- The order lifecycle is validated and audited; admin assignment is limited to active delivery agents without another active order.
- Restaurant sales count delivered orders; cancellation-rate and agent-performance reports are available under `/reports`.
- Menu deletion is soft (`is_deleted`), and item availability and restaurant open status are checked before order placement.
- Login is limited to five attempts per minute per IP. Use a unique `JWT_SECRET` outside local development.

## Main endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/users` (admin) |
| Restaurants | `POST /restaurants`, `PUT /restaurants/me`, `PATCH /restaurants/me/open-status`, `GET /restaurants`, `GET /restaurants/{id}/menu` |
| Menu | `POST /restaurants/me/menu-categories`, `POST /restaurants/me/menu-items`, `PUT /menu-items/{id}`, `PATCH /menu-items/{id}/availability`, `DELETE /menu-items/{id}` |
| Customers | `GET/POST /addresses`, `PATCH /addresses/{id}`, `GET/PUT /customers/me` |
| Orders | `POST /orders`, `GET /orders/me`, `GET /orders/restaurant`, `GET /orders/{id}`, `PATCH /orders/{id}/status`, `PATCH /orders/{id}/cancel` |
| Delivery | `GET /orders/agent`, `PATCH /orders/{id}/assign-agent` (admin), `PATCH /orders/{id}/delivery-status` (assigned agent: pickup/delivery) |
| Ratings | `POST /orders/{id}/rating` (ordering customer, delivered order, once per order); restaurant averages are recalculated |
| Reports | `GET /reports/restaurant-sales`, `GET /reports/cancellation-rate`, `GET /reports/agent-performance` |

### Delivery and rating responses

Successful delivery-status updates return the updated order, including its current status and audit history:

```json
{
  "id": 42,
  "order_no": "FD-AB12CD34EF56AB78CD90EF12AB34CD56",
  "status": "PICKED_UP",
  "item_total": "200.00",
  "tax_amount": "10.00",
  "delivery_fee": "40.00",
  "grand_total": "250.00",
  "placed_at": "2026-11-19T10:00:00Z",
  "delivered_at": null,
  "customer_id": 21,
  "restaurant_id": 3,
  "address_id": 14,
  "agent_id": 8,
  "address": {
    "line1": "10 Main Road",
    "line2": null,
    "city": "Chennai",
    "pincode": "600001"
  },
  "customer_phone": null,
  "items": [
    {
      "id": 88,
      "item_name_snapshot": "Biryani",
      "unit_price_snapshot": "200.00",
      "quantity": 1,
      "line_total": "200.00"
    }
  ],
  "history": [
    {
      "from_status": "PLACED",
      "to_status": "PLACED",
      "changed_by": 21,
      "changed_at": "2026-11-19T10:00:00Z",
      "remark": "Order placed"
    },
    {
      "from_status": "PLACED",
      "to_status": "CONFIRMED",
      "changed_by": 6,
      "changed_at": "2026-11-19T10:05:00Z",
      "remark": null
    },
    {
      "from_status": "CONFIRMED",
      "to_status": "PREPARING",
      "changed_by": 6,
      "changed_at": "2026-11-19T10:10:00Z",
      "remark": null
    },
    {
      "from_status": "PREPARING",
      "to_status": "READY_FOR_PICKUP",
      "changed_by": 6,
      "changed_at": "2026-11-19T10:20:00Z",
      "remark": null
    },
    {
      "from_status": "READY_FOR_PICKUP",
      "to_status": "PICKED_UP",
      "changed_by": 8,
      "changed_at": "2026-11-19T10:25:00Z",
      "remark": null
    }
  ]
}
```

After pickup, the assigned agent can retrieve the customer's phone with `GET /orders/{id}`. A successful rating submission returns:

```json
{
  "id": 12,
  "restaurant_rating": 5,
  "agent_rating": 4,
  "comment": "Great delivery"
}
```
