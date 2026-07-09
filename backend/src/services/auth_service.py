"""Authentication: password + TOTP verification against the users table."""

from fastapi import Depends, HTTPException, Request

from core.security import verify_password
from core.totp import verify as verify_totp
from models.user import UserModel
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from repository.user_repository import UserRepository

_user_repository = UserRepository()
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()


def authenticate(username: str, password: str, totp: str) -> UserModel:
    """Verify credentials and TOTP; raise HTTP 401 on any mismatch."""
    user = _user_repository.get_user_by_username(username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_totp(user.totp_secret, totp):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user


def get_current_user(request: Request) -> UserModel:
    """FastAPI dependency: resolve the logged-in user from the session cookie."""
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = _user_repository.get_user_by_username(username)
    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


def require_module_access(module_name: str):
    """FastAPI dependency factory: 401 if not logged in, 403 if not granted
    access to `module_name`. Superusers bypass the grant check — someone has
    to be able to manage modules/permissions before any grants exist."""

    def dependency(user: UserModel = Depends(get_current_user)) -> UserModel:
        if user.is_superuser:
            return user

        module = _module_repository.get_module_by_name(module_name)
        if module is None or not _permission_repository.has_access(user.id, module.id):
            raise HTTPException(status_code=403, detail="Forbidden")

        return user

    return dependency
