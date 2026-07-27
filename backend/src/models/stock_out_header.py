"""Stock out header ORM model — groups a stock-out transaction (date + description)."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class StockOutHeaderModel(Base):
    """Database model for stock out headers."""

    __tablename__ = "stock_out_headers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True, index=True
    )
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
