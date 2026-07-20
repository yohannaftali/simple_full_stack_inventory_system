"""Post-login endpoints consumed by the home page and the TOTP-setup modal.

Contract:
- GET  C_home/home -> {"username", "modules": [...], "title", "footer"} once
  authenticated; 401 if the session cookie is missing/invalid/expired.
  Each module dict: {"name", "label", "module_icon", "module_description",
  "group"} (field names match `components/home/module_card.py` and
  `components/home/module_container.py`, the latter reading `"group"` to
  bucket modules under a group header — falls back to "Dashboard" on the
  frontend if `"group"` is blank/missing) — only modules the user has been
  granted access to (user_module_permissions), ordered by group sort first
  then `ModuleModel.sort` within that group (see
  `UserModulePermissionRepository.get_modules_for_user`), so groups render
  in their configured order. `title`/`footer` come from the singleton
  `app_configs` row (see `routers/app_config.py`, frontend module
  `master_config`), falling back to "SFSIS"/"" if that row somehow doesn't
  exist yet.
- GET  C_home/call_generate_totp -> {"secret": "<base32>"}, a candidate secret
  for the user to scan and confirm — not persisted until call_change_totp
  verifies it.
- POST C_home/call_change_totp (form data: secret, totp) -> {"success": "..."}
  and persists `secret` as the user's totp_secret, or {"error": "..."} if the
  code doesn't match (still HTTP 200 either way — the frontend branches on
  the JSON body, not the status code, for this endpoint).
- POST C_home/call_change_password (form data: c=current, n=new, f=new
  confirmation) -> {"success": "..."} and persists the new (bcrypt-hashed)
  password, or {"error": "..."} if the confirmation doesn't match, the new
  password equals the current one, or the current password is wrong. Always
  HTTP 200 — same body-not-status-code contract as call_change_totp.
"""

from fastapi import APIRouter, Depends, Form

from core.security import hash_password, verify_password
from core.totp import generate_secret, verify as verify_totp
from models.user import UserModel
from repository.app_config_repository import AppConfigRepository
from repository.module_group_repository import ModuleGroupRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from repository.user_repository import UserRepository
from services.auth_service import get_current_user

router = APIRouter(prefix="/C_home", tags=["home"])
_user_repository = UserRepository()
_permission_repository = UserModulePermissionRepository()
_app_config_repository = AppConfigRepository()
_module_group_repository = ModuleGroupRepository()


@router.get("/home")
def home(user: UserModel = Depends(get_current_user)) -> dict:
    """Post-login bootstrap data: username, available modules, page chrome."""
    modules = []
    for module in _permission_repository.get_modules_for_user(user.id):
        group = (
            _module_group_repository.get_group_by_id(module.module_group_id)
            if module.module_group_id
            else None
        )
        modules.append(
            {
                "name": module.name,
                "label": module.label,
                "module_icon": module.icon,
                "module_description": module.description,
                "group": group.name if group else "",
            }
        )
    config = _app_config_repository.get_config()
    title = config.app_title if config else "SFSIS"
    footer = config.footer if config else ""
    return {"username": user.username, "modules": modules, "title": title, "footer": footer}


@router.get("/call_generate_totp")
def call_generate_totp(user: UserModel = Depends(get_current_user)) -> dict:
    """Generate a candidate TOTP secret for the user to scan and confirm."""
    return {"secret": generate_secret()}


@router.post("/call_change_totp")
def call_change_totp(
    secret: str = Form(...),
    totp: str = Form(...),
    user: UserModel = Depends(get_current_user),
) -> dict:
    """Confirm and persist a new TOTP secret after verifying the code against it."""
    if not verify_totp(secret, totp):
        return {"error": "Invalid code, please try again"}

    _user_repository.update_user_totp_secret(user.username, secret, updated_by=user.id)
    return {"success": "TOTP enabled successfully"}


@router.post("/call_change_password")
def call_change_password(
    c: str = Form(...),
    n: str = Form(...),
    f: str = Form(...),
    user: UserModel = Depends(get_current_user),
) -> dict:
    """Verify the current password, then persist the new one (bcrypt-hashed)."""
    if n != f:
        return {"error": "New password confirmation does not match"}

    if c == n:
        return {"error": "New password must be different from the current password"}

    if not verify_password(c, user.password):
        return {"error": "Current password is incorrect"}

    _user_repository.update_user_password(user.username, hash_password(n), updated_by=user.id)
    return {"success": "Password changed successfully"}
