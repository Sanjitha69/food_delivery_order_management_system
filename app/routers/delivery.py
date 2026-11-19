from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.security import require_role
from app.db.session import get_db
from app.models import Order, OrderStatus, Role, User
from app.schemas.delivery import AssignAgent, DeliveryStatusUpdate
from app.schemas.orders import OrderOut, OrderPage
from app.services.delivery_service import assign_agent, update_delivery_status


router = APIRouter(prefix="/orders", tags=["Delivery"])


@router.get("/agent", response_model=OrderPage)
def agent_orders(
    status: OrderStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    agent: User = Depends(require_role(Role.DELIVERY_AGENT)),
):
    query = select(Order).where(Order.agent_id == agent.id)
    if status:
        query = query.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Order.placed_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return {"items": items, "page": page, "size": size, "total": total}


@router.patch("/{order_id}/assign-agent", response_model=OrderOut)
def assign(
    order_id: int,
    data: AssignAgent,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(Role.ADMIN)),
):
    return assign_agent(db, order_id, data.agent_id, admin)


@router.patch("/{order_id}/delivery-status", response_model=OrderOut)
def delivery_status(
    order_id: int,
    data: DeliveryStatusUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(require_role(Role.DELIVERY_AGENT)),
):
    return update_delivery_status(db, order_id, agent, data.status, data.remark)
