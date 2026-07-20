"""Mail (SMTP) config singleton screen (frontend module `mail_config`).

Same single-record shape as `app_config.py` — see that file's docstring.
Nothing currently sends mail using these settings; this just stores them
for whenever that's wired up.

Contract:
- GET  C_mail_config/get -> {"smtp_host", "smtp_port", "smtp_username",
  "smtp_password", "sender_name", "sender_email", "use_tls"} (`use_tls` as
  the string "true"/"false", same convention as `is_active`/`is_superuser`
  in `user_admin.py`). All fields default to blank/sensible defaults if no
  row has been saved yet.
- GET  C_mail_config/call_use_tls_select -> static Yes/No options.
- POST C_mail_config/submit (form: smtp_host, smtp_port, smtp_username,
  smtp_password, sender_name, sender_email, use_tls) -> {"message": "..."}.

Gated by `require_module_access("mail_config")`.
"""

from fastapi import APIRouter, Depends, Form

from models.user import UserModel
from repository.mail_config_repository import MailConfigRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_mail_config", tags=["mail-config"])
_mail_config_repository = MailConfigRepository()

_require_access = require_module_access("mail_config")

_YES_NO_OPTIONS = [
    {"value": "true", "label": "Yes"},
    {"value": "false", "label": "No"},
]


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


@router.get("/get")
def get(user: UserModel = Depends(_require_access)) -> dict:
    config = _mail_config_repository.get_config()
    if config is None:
        return {
            "smtp_host": "",
            "smtp_port": "587",
            "smtp_username": "",
            "smtp_password": "",
            "sender_name": "",
            "sender_email": "",
            "use_tls": "true",
        }
    return {
        "smtp_host": config.smtp_host,
        "smtp_port": str(config.smtp_port),
        "smtp_username": config.smtp_username,
        "smtp_password": config.smtp_password,
        "sender_name": config.sender_name,
        "sender_email": config.sender_email,
        "use_tls": "true" if config.use_tls else "false",
    }


@router.get("/call_use_tls_select")
def call_use_tls_select(user: UserModel = Depends(_require_access)) -> list:
    return _YES_NO_OPTIONS


@router.post("/submit")
def submit(
    smtp_host: str = Form(""),
    smtp_port: str = Form("587"),
    smtp_username: str = Form(""),
    smtp_password: str = Form(""),
    sender_name: str = Form(""),
    sender_email: str = Form(""),
    use_tls: str = Form("true"),
    user: UserModel = Depends(_require_access),
) -> dict:
    try:
        smtp_port_value = int(smtp_port) if smtp_port else 587
    except ValueError:
        return {"error": "SMTP port must be a number"}

    _mail_config_repository.upsert_config(
        smtp_host=smtp_host,
        smtp_port=smtp_port_value,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        sender_name=sender_name,
        sender_email=sender_email,
        use_tls=_parse_bool(use_tls),
        actor_id=user.id,
    )
    return {"message": "Mail config updated successfully"}
