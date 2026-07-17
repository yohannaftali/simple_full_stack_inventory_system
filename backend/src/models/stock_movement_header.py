"""Stock movement header ORM model — groups a stock-transfer transaction
(date + description). Unlike `receiving_headers`/`stock_out_headers`, this
header carries `created_by`/`updated_by` (nullable FKs to `users.id`) - the
first header table in this codebase to track who performed the action,
populated from the authenticated session user at write time (issue #31)."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class StockMovementHeaderModel(Base):
    """Database model for stock movement headers."""

    __tablename__ = "stock_movement_headers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
