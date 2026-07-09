"""Module ORM model — adopted from the legacy PHP `ap_module` table."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

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
    module_group_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, index=True
    )
    icon: Mapped[str] = mapped_column(String(255), nullable=False, default="chevron_right")
    mdi: Mapped[str] = mapped_column(String(255), nullable=False, default="chevron_right")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
