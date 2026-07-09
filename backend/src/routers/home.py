"""Post-login endpoints consumed by the home page and the TOTP-setup modal.

Contract:
- GET  C_home/home -> {"username", "modules": [...], "title", "footer"} once
  authenticated; 401 if the session cookie is missing/invalid/expired.
  Each module dict: {"name", "label", "module_icon", "module_description"}
  (see components/home/module_card.py) — only modules the user has been
  granted access to (user_module_permissions), ordered by ModuleModel.sort.
- GET  C_home/call_generate_totp -> {"secret": "<base32>"}, a candidate secret
  for the user to scan and confirm — not persisted until call_change_totp
  verifies it.
- POST C_home/call_change_totp (form data: secret, totp) -> {"success": "..."}
  and persists `secret` as the user's totp_secret, or {"error": "..."} if the
  code doesn't match (still HTTP 200 either way — the frontend branches on
  the JSON body, not the status code, for this endpoint).
"""

from fastapi import APIRouter, Depends, Form

from core.totp import generate_secret, verify as verify_totp
from models.user import UserModel
from repository.user_module_permission_repository import UserModulePermissionRepository
from repository.user_repository import UserRepository
from services.auth_service import get_current_user

router = APIRouter(prefix="/C_home", tags=["home"])
_user_repository = UserRepository()
_permission_repository = UserModulePermissionRepository()


@router.get("/home")
def home(user: UserModel = Depends(get_current_user)) -> dict:
    """Post-login bootstrap data: username, available modules, page chrome."""
    modules = [
        {
            "name": module.name,
            "label": module.label,
            "module_icon": module.icon,
            "module_description": module.description,
        }
        for module in _permission_repository.get_modules_for_user(user.id)
    ]
    return {"username": user.username, "modules": modules, "title": "SFSIS", "footer": ""}


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

    _user_repository.update_user_totp_secret(user.username, secret)
    return {"success": "TOTP enabled successfully"}
