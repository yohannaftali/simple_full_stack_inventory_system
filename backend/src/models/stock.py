"""Stock ORM model — one lot row per receiving item: how much of that specific
receipt remains at its location. Not edited directly; maintained by
`services.inventory_service` (upserted 1:1 with its receiving item on stock in,
decremented FIFO-within-location on stock out)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class StockModel(Base):
    """Database model for stock lots (one row per receiving item)."""

    __tablename__ = "stocks"
    __table_args__ = (
        UniqueConstraint(
            "receiving_item_id", "material_id", "location_id", name="uq_stock_lot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    receiving_item_id: Mapped[int] = mapped_column(
        ForeignKey("receiving_items.id"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
