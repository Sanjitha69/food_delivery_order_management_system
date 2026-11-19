from datetime import datetime, time, timezone
from decimal import Decimal
import enum
from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    RESTAURANT_OWNER = "RESTAURANT_OWNER"
    CUSTOMER = "CUSTOMER"
    DELIVERY_AGENT = "DELIVERY_AGENT"


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[Role] = mapped_column(Enum(Role), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    restaurant: Mapped["Restaurant | None"] = relationship(back_populates="owner", uselist=False)
    addresses: Mapped[list["Address"]] = relationship(back_populates="user")


class Restaurant(Base, TimestampMixin):
    __tablename__ = "restaurants"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    cuisine: Mapped[str] = mapped_column(String(80), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    address: Mapped[str] = mapped_column(String(255))
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0"))
    owner: Mapped[User] = relationship(back_populates="restaurant")
    categories: Mapped[list["MenuCategory"]] = relationship(back_populates="restaurant")
    items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant")


class Address(Base, TimestampMixin):
    __tablename__ = "addresses"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    line1: Mapped[str] = mapped_column(String(255))
    line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(80))
    pincode: Mapped[str] = mapped_column(String(20))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship(back_populates="addresses")


class MenuCategory(Base, TimestampMixin):
    __tablename__ = "menu_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    restaurant: Mapped[Restaurant] = relationship(back_populates="categories")
    items: Mapped[list["MenuItem"]] = relationship(back_populates="category")


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    restaurant: Mapped[Restaurant] = relationship(back_populates="items")
    category: Mapped[MenuCategory] = relationship(back_populates="items")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PLACED, index=True)
    item_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    placed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    address: Mapped["Address"] = relationship()
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.id",
    )
    rating: Mapped["Rating | None"] = relationship(back_populates="order", uselist=False)


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    item_name_snapshot: Mapped[str] = mapped_column(String(120))
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    from_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    to_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), index=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order: Mapped[Order] = relationship(back_populates="history")


class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    restaurant_rating: Mapped[int] = mapped_column(Integer)
    agent_rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[Order] = relationship(back_populates="rating")
