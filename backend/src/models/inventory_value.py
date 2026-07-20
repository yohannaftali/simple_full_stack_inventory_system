"""Inventory value ORM model — one row per material: qty on hand + moving
average price (MAP) across all locations. Maintained by `services.inventory_service`,
never written to directly by routers."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class InventoryValueModel(Base):
    """Database model for per-material inventory valuation."""

    __tablename__ = "inventory_values"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id"), unique=True, nullable=False, index=True
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )
