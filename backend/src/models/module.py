"""Module ORM model — adopted from the legacy PHP `ap_module` table."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.timezone import AwareDateTime, utcnow
from models.base import Base


class ModuleModel(Base):
    """Database model for registered application modules (home tiles)."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sort_mobile: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    module_type: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, index=True)
    module_group_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("module_groups.id"), nullable=True, index=True
    )
    icon: Mapped[str] = mapped_column(String(255), nullable=False, default="chevron_right")
    mdi: Mapped[str] = mapped_column(String(255), nullable=False, default="chevron_right")
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
