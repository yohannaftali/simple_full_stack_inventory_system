"""Application config ORM model — a singleton row of app-wide display settings
(home screen title/footer). Only one row is ever expected to exist."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class AppConfigModel(Base):
    """Database model for the singleton application config row."""

    __tablename__ = "app_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_title: Mapped[str] = mapped_column(String(100), nullable=False, default="SFSIS")
    footer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
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
