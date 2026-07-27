"""Application config singleton screen (frontend module `master_config`).

Unlike every other admin module, this is a single-record settings screen —
no list, no delete, just get/submit against the one `app_configs` row
(`app_config_repository.py` creates it lazily if it's ever missing, though
the seed migration already creates one so that shouldn't happen in
practice). `routers/home.py` reads this row for the `title`/`footer` fields
in `GET C_home/home`. `timezone` (issue #47) is the live, admin-editable
IANA name `core/timezone.py::get_app_timezone()` reads on every request —
see that module's docstring for why display timestamps should be converted
through it rather than left as raw UTC.

Contract:
- GET  C_master_config/get -> {"app_title", "footer", "timezone"}.
- POST C_master_config/submit (form: app_title, footer, timezone) ->
  {"message": "..."} or {"error": "..."} (invalid/unrecognized IANA name).
- GET  C_master_config/call_timezone_select -> options for the `timezone`
  select field (core.timezone.common_timezones()).

Gated by `require_module_access("master_config")`.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Form

from core import config
from core.timezone import common_timezones
from models.user import UserModel
from repository.app_config_repository import AppConfigRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_config", tags=["master-config"])
_app_config_repository = AppConfigRepository()

_require_access = require_module_access("master_config")


@router.get("/get")
def get(user: UserModel = Depends(_require_access)) -> dict:
    app_config = _app_config_repository.get_config()
    if app_config is None:
        return {"app_title": "SFSIS", "footer": "", "timezone": config.APP_TIMEZONE_STR}
    return {
        "app_title": app_config.app_title,
        "footer": app_config.footer,
        "timezone": app_config.timezone,
    }


@router.post("/submit")
def submit(
    app_title: str = Form("SFSIS"),
    footer: str = Form(""),
    timezone: str = Form(config.APP_TIMEZONE_STR),
    user: UserModel = Depends(_require_access),
) -> dict:
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return {"error": f"Unrecognized timezone: {timezone}"}

    _app_config_repository.upsert_config(
        app_title=app_title or "SFSIS", footer=footer, timezone=timezone, actor_id=user.id
    )
    return {"message": "Application config updated successfully"}


@router.get("/call_timezone_select")
def call_timezone_select(user: UserModel = Depends(_require_access)) -> list:
    return [{"value": name, "label": name} for name in common_timezones()]
