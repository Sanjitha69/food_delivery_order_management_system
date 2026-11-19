from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_role
from app.models import User, Role, Restaurant, Order, OrderStatus, Rating
from app.exceptions import AppException

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/restaurant-sales")
def restaurant_sales(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                     sort: str = Query("grand_total", pattern="^(grand_total|order_count)$"),
                     db: Session = Depends(get_db),
                     user: User = Depends(require_role(Role.RESTAURANT_OWNER, Role.ADMIN))):
    if user.role == Role.ADMIN:
        restaurant_ids = select(Restaurant.id)
    else:
        restaurant = db.scalar(select(Restaurant).where(Restaurant.owner_id == user.id))
        if not restaurant:
            raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant profile not found")
        restaurant_ids = select(Restaurant.id).where(Restaurant.id == restaurant.id)
    query = (select(Order.restaurant_id,
                    func.count(Order.id).label("order_count"),
                    func.coalesce(func.sum(Order.grand_total), 0).label("grand_total"))
             .where(Order.restaurant_id.in_(restaurant_ids))
             .where(Order.status == OrderStatus.DELIVERED)
             .group_by(Order.restaurant_id))
    ordered = query.order_by(
        func.sum(Order.grand_total).desc()
        if sort == "grand_total"
        else func.count(Order.id).desc()
    )
    rows = db.execute(ordered.offset((page - 1) * size).limit(size)).all()
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {"items": [{"restaurant_id": r.restaurant_id, "order_count": r.order_count,
                       "grand_total": r.grand_total} for r in rows],
            "page": page, "size": size, "total": total}


@router.get("/agent-performance")
def agent_performance(db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.DELIVERY_AGENT, Role.ADMIN))):
    query = (
        select(
            User.id.label("agent_id"),
            User.full_name,
            func.count(Order.id).filter(Order.status == OrderStatus.DELIVERED).label("delivered_orders"),
            func.avg(Rating.agent_rating).label("average_rating"),
        )
        .outerjoin(Order, Order.agent_id == User.id)
        .outerjoin(Rating, Rating.order_id == Order.id)
        .where(User.role == Role.DELIVERY_AGENT)
        .group_by(User.id, User.full_name)
    )
    if user.role == Role.DELIVERY_AGENT:
        query = query.where(User.id == user.id)
    rows = db.execute(query.order_by(User.id)).all()
    return {
        "items": [
            {
                "agent_id": row.agent_id,
                "full_name": row.full_name,
                "delivered_orders": row.delivered_orders,
                "average_rating": row.average_rating,
            }
            for row in rows
        ]
    }


@router.get("/cancellation-rate")
def cancellation_rate(db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.RESTAURANT_OWNER, Role.ADMIN))):
    query = select(
        Order.restaurant_id,
        func.count(Order.id).label("total_orders"),
        func.count(Order.id).filter(Order.status == OrderStatus.CANCELLED).label("cancelled_orders"),
    ).group_by(Order.restaurant_id)
    if user.role == Role.RESTAURANT_OWNER:
        restaurant = db.scalar(select(Restaurant).where(Restaurant.owner_id == user.id))
        if not restaurant:
            raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant profile not found")
        query = query.where(Order.restaurant_id == restaurant.id)
    rows = db.execute(query).all()
    return {
        "items": [
            {
                "restaurant_id": row.restaurant_id,
                "total_orders": row.total_orders,
                "cancelled_orders": row.cancelled_orders,
                "cancellation_rate": round(row.cancelled_orders * 100 / row.total_orders, 2),
            }
            for row in rows
        ]
    }
