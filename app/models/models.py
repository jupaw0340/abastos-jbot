from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    price_kg_loose: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_kg_10plus: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_kg_bulk: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    bulk_label: Mapped[str] = mapped_column(String(40), default="arpÃ­a/bulto/caja")

    warehouse = relationship("Warehouse")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    default_delivery_place: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    delivery_place: Mapped[str | None] = mapped_column(String(200))
    pickup: Mapped[bool] = mapped_column(Boolean, default=True)

    status: Mapped[str] = mapped_column(String(40), default="pendiente")
    payment_status: Mapped[str] = mapped_column(String(40), default="pendiente")

    in_queue: Mapped[bool] = mapped_column(Boolean, default=False)
    has_prices: Mapped[bool] = mapped_column(Boolean, default=True)

    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))

    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class SystemState(Base):
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    orders_open: Mapped[bool] = mapped_column(Boolean, default=True)
    current_folio: Mapped[int] = mapped_column(Integer, default=1)
    prices_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)


