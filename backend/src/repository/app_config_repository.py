"""Application config repository — a singleton settings row (home screen
title/footer). There is always at most one row; the seed migration creates
the first one so `get_config` never has to synthesize defaults."""

from typing import Optional

from models.app_config import AppConfigModel
from models.base import SessionLocal


class AppConfigRepository:
    """Repository class for the singleton application config row."""

    def get_config(self) -> Optional[AppConfigModel]:
        with SessionLocal() as session:
            return session.query(AppConfigModel).first()

    def upsert_config(
        self, app_title: str, footer: str, actor_id: Optional[int] = None
    ) -> AppConfigModel:
        """Update the single row if one exists, otherwise create it."""
        with SessionLocal() as session:
            config = session.query(AppConfigModel).first()
            if config is None:
                config = AppConfigModel(
                    app_title=app_title, footer=footer, created_by=actor_id
                )
                session.add(config)
            else:
                config.app_title = app_title
                config.footer = footer
                config.updated_by = actor_id
            session.commit()
            session.refresh(config)
            return config
