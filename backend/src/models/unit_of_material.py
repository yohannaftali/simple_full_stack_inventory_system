"""Unit of material ORM model (master data — e.g. Pieces, Kilogram, Liter)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class UnitOfMaterialModel(Base):
    """Database model for units of material."""

    __tablename__ = "units_of_material"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
