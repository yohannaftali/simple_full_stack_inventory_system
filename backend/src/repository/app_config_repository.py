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
        self,
        app_title: str,
        footer: str,
        timezone: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> AppConfigModel:
        """Update the single row if one exists, otherwise create it.
        `timezone` is optional (defaults to the model's own column default,
        `config.APP_TIMEZONE_STR`) so existing callers/tests that don't pass
        one still work."""
        with SessionLocal() as session:
            config = session.query(AppConfigModel).first()
            if config is None:
                kwargs = {"app_title": app_title, "footer": footer, "created_by": actor_id}
                if timezone is not None:
                    kwargs["timezone"] = timezone
                config = AppConfigModel(**kwargs)
                session.add(config)
            else:
                config.app_title = app_title
                config.footer = footer
                if timezone is not None:
                    config.timezone = timezone
                config.updated_by = actor_id
            session.commit()
            session.refresh(config)
            return config
