"""Generic per-module permission check, consumed by the frontend's
`ClientData.has_permission()` (frontend/src/repository/client_data.py).

Contract:
- GET C_{module_name} -> {"secure": {"access": bool}}; 401 if not logged in.
  `access` is False (not a 404) if the module name doesn't exist, so the
  frontend never has to special-case an unknown module.
"""

from fastapi import APIRouter, Depends

from models.user import UserModel
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from services.auth_service import get_current_user

router = APIRouter(tags=["module"])
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()


@router.get("/C_{module_name}")
def check_module_permission(
    module_name: str, user: UserModel = Depends(get_current_user)
) -> dict:
    """Report whether the current user may access the given module."""
    module = _module_repository.get_module_by_name(module_name)
    if module is None:
        return {"secure": {"access": False}}

    access = _permission_repository.has_access(user.id, module.id)
    return {"secure": {"access": access}}
