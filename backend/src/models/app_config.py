"""Application config ORM model — a singleton row of app-wide display settings
(home screen title/footer) plus the app-wide timezone (issue #47 — see
core/timezone.py's module docstring). Only one row is ever expected to
exist."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core import config
from core.timezone import AwareDateTime, utcnow
from models.base import Base


class AppConfigModel(Base):
    """Database model for the singleton application config row."""

    __tablename__ = "app_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_title: Mapped[str] = mapped_column(String(100), nullable=False, default="SFSIS")
    footer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # The live, admin-editable IANA timezone name (e.g. "Asia/Jakarta") -
    # core.timezone.get_app_timezone() reads this row directly rather than
    # caching it, so a change here takes effect on the very next request,
    # no restart needed. config.APP_TIMEZONE_STR only seeds this column's
    # default for a fresh install.
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default=config.APP_TIMEZONE_STR
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
