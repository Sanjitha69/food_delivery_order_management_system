from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models import Restaurant, User, Role, MenuCategory, MenuItem
from app.exceptions import AppException


def owner_restaurant(db: Session, user: User) -> Restaurant:
    restaurant = db.scalar(select(Restaurant).where(Restaurant.owner_id == user.id))
    if not restaurant:
        raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant profile not found")
    return restaurant


def create_restaurant(db: Session, user: User, data):
    if db.scalar(select(Restaurant).where(Restaurant.owner_id == user.id)):
        raise AppException(409, "RESTAURANT_EXISTS", "Restaurant profile already exists")
    restaurant = Restaurant(owner_id=user.id, avg_rating=0, **data.model_dump())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def update_restaurant(db: Session, user: User, data):
    restaurant = owner_restaurant(db, user)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(restaurant, key, value)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def set_open(db: Session, user: User, is_open: bool):
    restaurant = owner_restaurant(db, user)
    restaurant.is_open = is_open
    db.commit()
    db.refresh(restaurant)
    return restaurant


def search_restaurants(db: Session, city, cuisine, name, page, size, sort):
    query = select(Restaurant)
    if city:
        query = query.where(Restaurant.city.ilike(f"%{city}%"))
    if cuisine:
        query = query.where(Restaurant.cuisine.ilike(f"%{cuisine}%"))
    if name:
        query = query.where(Restaurant.name.ilike(f"%{name}%"))
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = {"name": Restaurant.name, "rating": Restaurant.avg_rating}.get(sort, Restaurant.id)
    items = db.scalars(query.order_by(sort_column.desc() if sort == "rating" else sort_column).offset((page - 1) * size).limit(size)).all()
    return {"items": items, "page": page, "size": size, "total": count}


def menu(db: Session, restaurant_id: int):
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise AppException(404, "RESTAURANT_NOT_FOUND", "Restaurant not found")
    categories = db.scalars(select(MenuCategory).where(MenuCategory.restaurant_id == restaurant_id).order_by(MenuCategory.display_order)).all()
    return [{"id": c.id, "name": c.name, "display_order": c.display_order,
             "items": db.scalars(select(MenuItem).where(MenuItem.category_id == c.id, MenuItem.is_deleted == False)).all()} for c in categories]


def create_category(db: Session, user: User, data):
    restaurant = owner_restaurant(db, user)
    category = MenuCategory(restaurant_id=restaurant.id, **data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_item(db: Session, user: User, data):
    restaurant = owner_restaurant(db, user)
    category = db.get(MenuCategory, data.category_id)
    if not category or category.restaurant_id != restaurant.id:
        raise AppException(404, "CATEGORY_NOT_FOUND", "Menu category not found")
    item = MenuItem(restaurant_id=restaurant.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def owned_item(db: Session, user: User, item_id: int) -> MenuItem:
    restaurant = owner_restaurant(db, user)
    item = db.get(MenuItem, item_id)
    if not item or item.restaurant_id != restaurant.id:
        raise AppException(404, "MENU_ITEM_NOT_FOUND", "Menu item not found")
    return item


def update_item(db: Session, user: User, item_id: int, data):
    item = owned_item(db, user, item_id)
    changes = data.model_dump(exclude_unset=True)
    category_id = changes.get("category_id")
    if category_id is not None:
        category = db.get(MenuCategory, category_id)
        if not category or category.restaurant_id != item.restaurant_id:
            raise AppException(404, "CATEGORY_NOT_FOUND", "Menu category not found")
    for key, value in changes.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item
