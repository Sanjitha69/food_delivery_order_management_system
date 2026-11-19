from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models import OrderStatus


class OrderItemRequest(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)
    price: Decimal | None = Field(default=None, description="Ignored; server pricing is authoritative")


class OrderCreate(BaseModel):
    restaurant_id: int = Field(gt=0)
    address_id: int = Field(gt=0)
    items: list[OrderItemRequest] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    line_total: Decimal


class StatusUpdate(BaseModel):
    status: OrderStatus
    remark: str | None = Field(default=None, max_length=255)


class OrderStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    from_status: OrderStatus
    to_status: OrderStatus
    changed_by: int
    changed_at: datetime
    remark: str | None


class OrderAddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    line1: str
    line2: str | None
    city: str
    pincode: str


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    status: OrderStatus
    item_total: Decimal
    tax_amount: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    placed_at: datetime
    delivered_at: datetime | None
    customer_id: int
    restaurant_id: int
    address_id: int
    agent_id: int | None
    address: OrderAddressOut
    customer_phone: str | None = None
    items: list[OrderItemOut] = Field(default_factory=list)
    history: list[OrderStatusHistoryOut] = Field(default_factory=list)


class OrderPage(BaseModel):
    items: list[OrderOut]
    page: int
    size: int
    total: int
