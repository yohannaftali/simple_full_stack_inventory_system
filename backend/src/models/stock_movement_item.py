"""Stock movement item ORM model — one transfer line (material, origin
location -> destination location, qty) within a stock movement header.

`plan_qty` is reserved for a future two-step plan/confirm workflow (issue
#31) - this first rollout is direct/immediate movement only, so `plan_qty`
is always set equal to `movement_qty` on create, with no separate UI input
for it. A movement item creates a brand new stock lot at the destination
(see `services.inventory_service.create_stock_movement_item`) - it does not
touch `inventory_values.qty`/`average_price` for the material, since a
transfer between two of that material's own locations changes neither its
total on-hand quantity nor its cost."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class StockMovementItemModel(Base):
    """Database model for stock movement (transfer) line items."""

    __tablename__ = "stock_movement_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_movement_header_id: Mapped[int] = mapped_column(
        ForeignKey("stock_movement_headers.id"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False, index=True
    )
    origin_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    destination_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    plan_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    movement_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remarks: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime, default=utcnow, nullable=False
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        AwareDateTime, onupdate=utcnow, nullable=True
    )
