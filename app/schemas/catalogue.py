from datetime import time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cuisine: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=80)
    address: str = Field(min_length=5, max_length=255)
    opens_at: time
    closes_at: time


class RestaurantUpdate(RestaurantCreate):
    pass


class RestaurantOut(RestaurantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_open: bool
    avg_rating: Decimal


class OpenStatus(BaseModel):
    is_open: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    display_order: int = Field(default=0, ge=0)


class CategoryOut(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ItemCreate(BaseModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_veg: bool = True


class ItemOut(ItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_available: bool


class CategoryMenuOut(CategoryOut):
    items: list[ItemOut] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    is_veg: bool | None = None


class AvailabilityUpdate(BaseModel):
    is_available: bool
