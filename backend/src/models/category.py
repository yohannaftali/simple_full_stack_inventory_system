"""Category ORM model (master data — classifies materials into groups)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class CategoryModel(Base):
    """Database model for categories."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
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
