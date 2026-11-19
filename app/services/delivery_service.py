from sqlalchemy import select
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models import Order, OrderStatus, Role, User
from app.services.order_service import participant_order, transition


def assign_agent(db: Session, order_id: int, agent_id: int, admin: User) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise AppException(404, "ORDER_NOT_FOUND", "Order not found")
    agent = db.get(User, agent_id)
    if not agent or agent.role != Role.DELIVERY_AGENT or not agent.is_active:
        raise AppException(404, "AGENT_NOT_FOUND", "Delivery agent not found")
    if order.status != OrderStatus.READY_FOR_PICKUP:
        raise AppException(409, "INVALID_TRANSITION", "Agent assignment requires READY_FOR_PICKUP")
    if order.agent_id is not None:
        raise AppException(409, "AGENT_ALREADY_ASSIGNED", "Order already has a delivery agent")
    active_order = db.scalar(
        select(Order.id).where(
            Order.agent_id == agent.id,
            Order.status.in_({OrderStatus.READY_FOR_PICKUP, OrderStatus.PICKED_UP}),
        ).limit(1)
    )
    if active_order is not None:
        raise AppException(409, "AGENT_UNAVAILABLE", "Delivery agent already has an active order")
    order.agent_id = agent.id
    db.commit()
    db.refresh(order)
    return order


def update_delivery_status(
    db: Session,
    order_id: int,
    agent: User,
    target: OrderStatus,
    remark: str | None = None,
) -> Order:
    order = participant_order(db, order_id, agent)
    if order.agent_id != agent.id:
        raise AppException(403, "FORBIDDEN", "Only the assigned agent may update delivery")
    return transition(
        db,
        order,
        target,
        agent,
        {OrderStatus.READY_FOR_PICKUP, OrderStatus.PICKED_UP},
        remark,
    )
