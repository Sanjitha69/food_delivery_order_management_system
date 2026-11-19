from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import require_role
from app.db.session import get_db
from app.models import Role, User
from app.schemas.ratings import RatingCreate, RatingOut
from app.services.rating_service import create_order_rating


router = APIRouter(prefix="/orders", tags=["Ratings"])


@router.post("/{order_id}/rating", response_model=RatingOut, status_code=201)
def create_rating(
    order_id: int,
    data: RatingCreate,
    db: Session = Depends(get_db),
    customer: User = Depends(require_role(Role.CUSTOMER)),
):
    return create_order_rating(db, order_id, customer, data)
