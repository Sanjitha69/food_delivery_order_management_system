from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.exceptions import AppException
from app.models import Order, OrderStatus, Rating, Restaurant, User
from app.schemas.ratings import RatingCreate
from app.services.order_service import participant_order


def create_order_rating(db: Session, order_id: int, customer: User, data: RatingCreate) -> Rating:
    order = participant_order(db, order_id, customer)
    if order.customer_id != customer.id:
        raise AppException(403, "FORBIDDEN", "Only the ordering customer may rate")
    if order.status != OrderStatus.DELIVERED:
        raise AppException(409, "NOT_DELIVERED", "Rating requires a delivered order")
    if order.rating:
        raise AppException(409, "RATING_EXISTS", "Order has already been rated")
    rating = Rating(order_id=order.id, **data.model_dump())
    db.add(rating)
    db.flush()
    restaurant = db.get(Restaurant, order.restaurant_id)
    ratings = db.scalars(select(Rating).join(Order).where(Order.restaurant_id == restaurant.id)).all()
    average = sum(entry.restaurant_rating for entry in ratings) / len(ratings)
    restaurant.avg_rating = Decimal(str(average)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    db.commit()
    db.refresh(rating)
    return rating
