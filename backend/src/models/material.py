"""Material ORM model (master data — what can be received/stocked/issued)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class MaterialModel(Base):
    """Database model for materials."""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
