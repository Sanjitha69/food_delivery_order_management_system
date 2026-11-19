from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_role
from app.models import User, Role
from app.schemas.catalogue import *
from app.services.catalogue_service import (
    create_category,
    create_item,
    owned_item,
    update_item as update_menu_item,
)

router = APIRouter(tags=["Menu"], dependencies=[Depends(require_role(Role.RESTAURANT_OWNER))])

@router.post("/restaurants/me/menu-categories", response_model=CategoryOut, status_code=201)
def create_category_route(data: CategoryCreate, db: Session = Depends(get_db),
                          user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return create_category(db, user, data)

@router.post("/restaurants/me/menu-items", response_model=ItemOut, status_code=201)
def create_item_route(data: ItemCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return create_item(db, user, data)

@router.put("/menu-items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    return update_menu_item(db, user, item_id, data)

@router.patch("/menu-items/{item_id}/availability", response_model=ItemOut)
def availability(item_id: int, data: AvailabilityUpdate, db: Session = Depends(get_db),
                 user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    item = owned_item(db, user, item_id)
    item.is_available = data.is_available
    db.commit()
    db.refresh(item)
    return item

@router.delete("/menu-items/{item_id}", status_code=204)
def soft_delete_item(item_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_role(Role.RESTAURANT_OWNER))):
    item = owned_item(db, user, item_id)
    item.is_deleted = True
    item.is_available = False
    db.commit()
    return None
