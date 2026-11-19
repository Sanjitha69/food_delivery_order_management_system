from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_role
from app.models import User, Role
from app.schemas.catalogue import (
    CategoryMenuOut,
    OpenStatus,
    RestaurantCreate,
    RestaurantOut,
    RestaurantUpdate,
)
from app.services.catalogue_service import *

router = APIRouter(tags=["Restaurants"])

@router.post("/restaurants", response_model=RestaurantOut, status_code=201,
             dependencies=[Depends(require_role(Role.RESTAURANT_OWNER))])
def create(data: RestaurantCreate, db: Session = Depends(get_db),
           user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return create_restaurant(db, user, data)

@router.put("/restaurants/me", response_model=RestaurantOut,
            dependencies=[Depends(require_role(Role.RESTAURANT_OWNER))])
def update(data: RestaurantUpdate, db: Session = Depends(get_db),
           user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return update_restaurant(db, user, data)

@router.patch("/restaurants/me/open-status", response_model=RestaurantOut,
              dependencies=[Depends(require_role(Role.RESTAURANT_OWNER))])
def open_status(data: OpenStatus, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return set_open(db, user, data.is_open)

@router.get("/restaurants")
def search(city: str | None = None, cuisine: str | None = None, name: str | None = None,
           page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           sort: str = Query("id", pattern="^(id|name|rating)$"), db: Session = Depends(get_db)):
    return search_restaurants(db, city, cuisine, name, page, size, sort)

@router.get("/restaurants/{restaurant_id}/menu", response_model=list[CategoryMenuOut])
def get_menu(restaurant_id: int, db: Session = Depends(get_db)):
    return menu(db, restaurant_id)
