"""Receiving item ORM model — one received line (material/location/qty/price)
within a receiving header. Each item owns exactly one `StockModel` lot row.

`qty_plan` (issue #33) is reserved for a future two-step plan/confirm
workflow, same precedent as `stock_movement_items.plan_qty` (issue #31) -
this rollout has no plan/confirm split yet, so `qty_plan` is always set
equal to `qty_received` on create (see `services.inventory_service`), with
no separate UI input for it."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class ReceivingItemModel(Base):
    """Database model for receiving (stock in) line items."""

    __tablename__ = "receiving_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    receiving_header_id: Mapped[int] = mapped_column(
        ForeignKey("receiving_headers.id"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    price_buy: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_plan: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remarks: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
