from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.exceptions import AppException
from app.models import (Address, MenuItem, Order, OrderItem, OrderStatus,
                        OrderStatusHistory, Restaurant, User, Role)


TRANSITIONS = {
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY_FOR_PICKUP},
    OrderStatus.READY_FOR_PICKUP: {OrderStatus.PICKED_UP},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERED},
}


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def place_order(db: Session, customer: User, data):
    address = db.get(Address, data.address_id)
    if not address or address.user_id != customer.id:
        raise AppException(404, "ADDRESS_NOT_FOUND", "Delivery address not found")
    restaurant = db.get(Restaurant, data.restaurant_id)
    if not restaurant:
        raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant not found")
    if not restaurant.is_open:
        raise AppException(409, "RESTAURANT_CLOSED", "Restaurant is closed")
    item_total = Decimal("0")
    snapshots = []
    for requested in data.items:
        item = db.get(MenuItem, requested.menu_item_id)
        if not item or item.is_deleted or not item.is_available:
            raise AppException(409, "ITEM_UNAVAILABLE", "Menu item unavailable")
        if item.restaurant_id != restaurant.id:
            raise AppException(400, "INVALID_RESTAURANT_ITEMS", "All items must belong to one restaurant")
        line = money(item.price * requested.quantity)
        item_total += line
        snapshots.append((item, requested.quantity, line))
    tax = money(item_total * Decimal(str(settings.tax_percent)) / Decimal("100"))
    delivery_fee = Decimal("0") if item_total >= Decimal(str(settings.free_delivery_minimum)) else money(Decimal(str(settings.delivery_fee)))
    grand = money(item_total + tax + delivery_fee)
    order = Order(order_no=f"FD-{uuid4().hex.upper()}",
                  customer_id=customer.id, restaurant_id=restaurant.id, address_id=address.id,
                  status=OrderStatus.PLACED, item_total=item_total, tax_amount=tax,
                  delivery_fee=delivery_fee, grand_total=grand)
    db.add(order)
    db.flush()
    for item, quantity, line in snapshots:
        db.add(OrderItem(order_id=order.id, menu_item_id=item.id, item_name_snapshot=item.name,
                         unit_price_snapshot=item.price, quantity=quantity, line_total=line))
    db.add(OrderStatusHistory(order_id=order.id, from_status=OrderStatus.PLACED,
                              to_status=OrderStatus.PLACED, changed_by=customer.id, remark="Order placed"))
    db.commit()
    db.refresh(order)
    return order


def participant_order(db: Session, order_id: int, user: User) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise AppException(404, "ORDER_NOT_FOUND", "Order not found")
    restaurant = db.get(Restaurant, order.restaurant_id)
    allowed = (user.role == Role.ADMIN or order.customer_id == user.id or
               (user.role == Role.RESTAURANT_OWNER and restaurant.owner_id == user.id) or
               (user.role == Role.DELIVERY_AGENT and order.agent_id == user.id))
    if not allowed:
        raise AppException(403, "FORBIDDEN", "Order is not accessible")
    return order


def transition(db: Session, order: Order, target: OrderStatus, user: User, allowed_from, remark=None):
    if order.status not in allowed_from or target not in TRANSITIONS.get(order.status, set()):
        raise AppException(409, "INVALID_TRANSITION", f"Cannot move order from {order.status.value} to {target.value}")
    old = order.status
    order.status = target
    if target == OrderStatus.DELIVERED:
        order.delivered_at = datetime.now(timezone.utc)
    db.add(OrderStatusHistory(order_id=order.id, from_status=old, to_status=target,
                              changed_by=user.id, remark=remark))
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: int, user: User):
    order = participant_order(db, order_id, user)
    if order.customer_id != user.id:
        raise AppException(403, "FORBIDDEN", "Only the ordering customer can cancel")
    return transition(db, order, OrderStatus.CANCELLED, user,
                      {OrderStatus.PLACED, OrderStatus.CONFIRMED})


def owner_transition(db: Session, order_id: int, user: User, target: OrderStatus, remark):
    order = participant_order(db, order_id, user)
    restaurant = db.get(Restaurant, order.restaurant_id)
    if user.role != Role.RESTAURANT_OWNER or restaurant.owner_id != user.id:
        raise AppException(403, "FORBIDDEN", "Only the receiving restaurant owner may change status")
    return transition(db, order, target, user,
                      {OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING})


