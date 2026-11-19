from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_role
from app.exceptions import AppException
from app.models import Order, OrderStatus, Restaurant, Role, User
from app.schemas.orders import (
    OrderCreate,
    OrderPage,
    OrderOut,
    StatusUpdate,
)
from app.services.order_service import (
    cancel_order,
    owner_transition,
    participant_order,
    place_order,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("", response_model=OrderOut, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_role(Role.CUSTOMER))):
    return place_order(db, user, data)

@router.get("/me", response_model=OrderPage)
def my_orders(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
              status: OrderStatus | None = None, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.CUSTOMER))):
    query = select(Order).where(Order.customer_id == user.id)
    if status:
        query = query.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Order.placed_at.desc()).offset((page - 1) * size).limit(size)).all()
    return {"items": items, "page": page, "size": size, "total": total}

@router.patch("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, db: Session = Depends(get_db),
           user: User = Depends(require_role(Role.CUSTOMER))):
    return cancel_order(db, order_id, user)


@router.get("/restaurant", response_model=OrderPage)
def restaurant_orders(status: OrderStatus | None = None, page: int = Query(1, ge=1),
                      size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    restaurant = db.scalar(select(Restaurant).where(Restaurant.owner_id == user.id))
    if not restaurant:
        raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant profile not found")
    query = select(Order).where(Order.restaurant_id == restaurant.id)
    if status:
        query = query.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(Order.placed_at.desc()).offset((page - 1) * size).limit(size)).all()
    return {"items": items, "page": page, "size": size, "total": total}


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.ADMIN, Role.RESTAURANT_OWNER, Role.CUSTOMER, Role.DELIVERY_AGENT))):
    order = participant_order(db, order_id, user)
    result = OrderOut.model_validate(order)
    if user.role == Role.DELIVERY_AGENT and order.status in {OrderStatus.PICKED_UP, OrderStatus.DELIVERED}:
        result.customer_phone = db.scalar(select(User.phone).where(User.id == order.customer_id))
    return result


@router.patch("/{order_id}/status", response_model=OrderOut)
def restaurant_status(order_id: int, data: StatusUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return owner_transition(db, order_id, user, data.status, data.remark)
