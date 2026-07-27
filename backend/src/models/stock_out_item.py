"""Stock out item ORM model — one issued line (material/location/qty) within a
stock out header. Captures the material's moving average price at the moment
of issue, since MAP is not retroactively editable.

`qty_plan` (issue #33) is reserved for a future two-step plan/confirm
workflow, same precedent as `stock_movement_items.plan_qty` (issue #31) -
this rollout has no plan/confirm split yet, so `qty_plan` is always set
equal to `qty_out` on create (see `services.inventory_service`), with no
separate UI input for it."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class StockOutItemModel(Base):
    """Database model for stock out (issue) line items."""

    __tablename__ = "stock_out_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_out_header_id: Mapped[int] = mapped_column(
        ForeignKey("stock_out_headers.id"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    qty_plan: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_out: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
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
