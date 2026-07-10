"""Application config singleton screen (frontend module `master_config`).

Unlike every other admin module, this is a single-record settings screen —
no list, no delete, just get/submit against the one `app_configs` row
(`app_config_repository.py` creates it lazily if it's ever missing, though
the seed migration already creates one so that shouldn't happen in
practice). `routers/home.py` reads this row for the `title`/`footer` fields
in `GET C_home/home`.

Contract:
- GET  C_master_config/get -> {"app_title", "footer"}.
- POST C_master_config/submit (form: app_title, footer) -> {"message": "..."}.

Gated by `require_module_access("master_config")`.
"""

from fastapi import APIRouter, Depends, Form

from models.user import UserModel
from repository.app_config_repository import AppConfigRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_config", tags=["master-config"])
_app_config_repository = AppConfigRepository()

_require_access = require_module_access("master_config")


@router.get("/get")
def get(user: UserModel = Depends(_require_access)) -> dict:
    config = _app_config_repository.get_config()
    if config is None:
        return {"app_title": "SFSIS", "footer": ""}
    return {"app_title": config.app_title, "footer": config.footer}


@router.post("/submit")
def submit(
    app_title: str = Form("SFSIS"),
    footer: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    _app_config_repository.upsert_config(app_title=app_title or "SFSIS", footer=footer)
    return {"message": "Application config updated successfully"}
