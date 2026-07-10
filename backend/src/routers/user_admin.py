"""User CRUD + module-permission admin screen (frontend module `ap_master_user`).

Contract (see components/table/table.py, components/form/form.py, components/form/select.py):
- GET  C_ap_master_user/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> list of user dicts (no password), paginated (the list table).
- GET  C_ap_master_user/get?id=<id> -> single user dict, `is_active`/
  `is_superuser` as the strings "true"/"false" (the edit form; selects need
  string option values).
- GET  C_ap_master_user/call_is_active_select,
  GET  C_ap_master_user/call_is_superuser_select -> static Yes/No options.
- POST C_ap_master_user/submit (form: id, username, email, password, is_active,
  is_superuser, department_id) -> upsert. `password` is required to create,
  optional on update (blank = keep existing); always bcrypt-hashed before
  storing. `department_id` is optional (nullable — not every user belongs to
  a department, e.g. admin/IT accounts).
- GET  C_ap_master_user/call_department_id_select -> options for the
  `department_id` select field.
- POST C_ap_master_user/delete (form: id) -> also deletes the user's
  module-permission grants first.
- GET  C_ap_master_user/get_all_modules -> every module (for the permission
  checklist), `{"id","name","label"}` each.
- GET  C_ap_master_user/get_permissions?id=<user_id> -> {"module_ids": [...]}.
- POST C_ap_master_user/save_permissions (form: user_id, module_ids [comma-
  separated ids]) -> replaces the user's grants with exactly that set.

All routes require `ap_master_user` access (or superuser) via `require_module_access`.
"""

from fastapi import APIRouter, Depends, Form, Query

from core.security import hash_password
from core.table_query import attach_pagination
from models.user import UserModel
from repository.department_repository import DepartmentRepository
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from repository.user_repository import UserRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_ap_master_user", tags=["user-admin"])
_user_repository = UserRepository()
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()
_department_repository = DepartmentRepository()

_require_access = require_module_access("ap_master_user")

_YES_NO_OPTIONS = [
    {"value": "true", "label": "Yes"},
    {"value": "false", "label": "No"},
]


def _serialize_user(user: UserModel) -> dict:
    department = (
        _department_repository.get_department_by_id(user.department_id)
        if user.department_id
        else None
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": "true" if user.is_active else "false",
        "is_superuser": "true" if user.is_superuser else "false",
        "department_id": str(user.department_id) if user.department_id else "",
        "department_name": department.name if department else "",
    }


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated user list for the admin list screen."""
    rows, pagination = _user_repository.list_users(
        keyword=keyword, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize_user(row_user) for row_user in rows], pagination)


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """Single user record for the edit form (never includes the password)."""
    target = _user_repository.get_user_by_id(id)
    if target is None:
        return {"error": "User not found"}
    return _serialize_user(target)


@router.get("/call_is_active_select")
def call_is_active_select(user: UserModel = Depends(_require_access)) -> list:
    return _YES_NO_OPTIONS


@router.get("/call_is_superuser_select")
def call_is_superuser_select(user: UserModel = Depends(_require_access)) -> list:
    return _YES_NO_OPTIONS


@router.get("/call_department_id_select")
def call_department_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(d.id), "label": f"{d.code} - {d.name}"}
        for d in _department_repository.get_all_departments()
    ]


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    is_active: str = Form("true"),
    is_superuser: str = Form("false"),
    department_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    """Create or update a user (blank/missing id = create)."""
    active = _parse_bool(is_active)
    superuser = _parse_bool(is_superuser)
    department_id_value = int(department_id) if department_id else None

    if id:
        target_id = int(id)
        if _user_repository.check_user_exists(username, email, exclude_id=target_id):
            return {"error": "Username or email already in use"}

        updated = _user_repository.update_user_by_id(
            user_id=target_id,
            username=username,
            email=email,
            is_active=active,
            is_superuser=superuser,
            password=hash_password(password) if password else None,
            department_id=department_id_value,
        )
        if not updated:
            return {"error": "User not found"}
        return {"message": "User updated successfully"}

    if not password:
        return {"error": "Password is required to create a user"}
    if _user_repository.check_user_exists(username, email):
        return {"error": "Username or email already in use"}

    _user_repository.create_user(
        username=username,
        password=hash_password(password),
        email=email,
        is_active=active,
        is_superuser=superuser,
        department_id=department_id_value,
    )
    return {"message": "User created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """Delete a user and every permission grant referencing them."""
    user_id = int(id)
    _permission_repository.delete_permissions_for_user(user_id)
    deleted = _user_repository.delete_user_by_id(user_id)
    if not deleted:
        return {"error": "User not found"}
    return {"message": "User deleted successfully"}


@router.get("/get_all_modules")
def get_all_modules(user: UserModel = Depends(_require_access)) -> list:
    """Every registered module, for the permission checklist."""
    return [
        {"id": module.id, "name": module.name, "label": module.label}
        for module in _module_repository.get_all_modules()
    ]


@router.get("/get_permissions")
def get_permissions(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """The module ids a user has been granted access to."""
    return {"module_ids": _permission_repository.get_module_ids_for_user(id)}


@router.post("/save_permissions")
def save_permissions(
    user_id: str = Form(...),
    module_ids: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    """Replace a user's module grants with exactly the given comma-separated ids."""
    ids = [int(part) for part in module_ids.split(",") if part.strip()]
    _permission_repository.set_modules_for_user(int(user_id), ids)
    return {"message": "Permissions saved successfully"}
