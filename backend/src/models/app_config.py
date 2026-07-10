"""Application config ORM model — a singleton row of app-wide display settings
(home screen title/footer). Only one row is ever expected to exist."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class AppConfigModel(Base):
    """Database model for the singleton application config row."""

    __tablename__ = "app_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_title: Mapped[str] = mapped_column(String(100), nullable=False, default="SFSIS")
    footer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
