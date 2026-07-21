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
- GET  C_ap_master_user/get_granted_modules?id=<user_id>&table-keyword-filter=&
  limit=&page=&offset= -> paginated list of modules the user already has
  access to (the read-only module-access table on `edit.py`, issue #41).
- GET  C_ap_master_user/get_ungranted_modules?id=<user_id>&table-keyword-filter=&
  limit=&page=&offset= -> paginated list of modules the user does NOT yet
  have access to (the checkbox-select table on `permission_new.py`, issue #41).
- POST C_ap_master_user/submit_permission_new (form: user_id, repeated
  module_ids) -> grants access to exactly those module ids, additive only -
  does not touch any of the user's existing grants (issue #41).
- POST C_ap_master_user/revoke_permission (form: user_id, repeated
  module_ids) -> revokes access to exactly those module ids (single or
  bulk), leaving every other grant untouched - backs the granted-modules
  table's remove button on `edit.py` (issue #42).

All routes require `ap_master_user` access (or superuser) via `require_module_access`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request

from core.security import hash_password
from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.module import ModuleModel
from models.user import UserModel
from repository.department_repository import DepartmentRepository
from repository.module_group_repository import ModuleGroupRepository
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from repository.user_repository import UserRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_ap_master_user", tags=["user-admin"])
_user_repository = UserRepository()
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()
_department_repository = DepartmentRepository()
_module_group_repository = ModuleGroupRepository()

_require_access = require_module_access("ap_master_user")

_EXPORT_COLUMNS = [
    ("username", "Username"),
    ("email", "Email"),
    ("is_active", "Active"),
    ("is_superuser", "Superuser"),
    ("department_name", "Department"),
]

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
    request: Request,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated user list for the admin list screen."""
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _user_repository.list_users(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize_user(row_user) for row_user in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _user_repository.list_users(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize_user(row_user) for row_user in rows], _EXPORT_COLUMNS, format, "ap_master_user"
    )


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
            updated_by=user.id,
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
        created_by=user.id,
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


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(
        form,
        ["username", "email", "password", "is_active", "is_superuser", "department_id"],
    )

    def build(row, session):
        username = str(row.get("username", "")).strip()
        email = str(row.get("email", "")).strip()
        password = str(row.get("password", ""))
        if not username or not email:
            raise BulkRowError(row["_row"], "Username and Email are required")
        if not password:
            raise BulkRowError(row["_row"], "Password is required to create a user")

        # Queried inside the batch's own session, so rows flushed earlier in
        # this same file are visible too - one check covers both "already in
        # the database" and "duplicated within the uploaded file", with the
        # same message the single-record submit produces.
        exists = (
            session.query(UserModel)
            .filter((UserModel.username == username) | (UserModel.email == email))
            .first()
        )
        if exists:
            raise BulkRowError(row["_row"], "Username or email already in use")

        department_raw = str(row.get("department_id", "")).strip()
        try:
            department_id = int(department_raw) if department_raw else None
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Department: {department_raw}")

        return UserModel(
            username=username,
            email=email,
            password=hash_password(password),
            is_active=_parse_bool(row.get("is_active", "true") or "true"),
            is_superuser=_parse_bool(row.get("is_superuser", "false") or "false"),
            department_id=department_id,
            totp_secret="",
            created_by=user.id,
        )

    return bulk_create(rows, build)


def _serialize_module_for_permission(module: ModuleModel) -> dict:
    group = (
        _module_group_repository.get_group_by_id(module.module_group_id)
        if module.module_group_id
        else None
    )
    return {
        "id": module.id,
        "name": module.name,
        "label": module.label,
        "description": module.description,
        "module_group_name": group.name if group else "",
    }


@router.get("/get_granted_modules")
def get_granted_modules(
    request: Request,
    id: int,  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated list of modules the user already has access to."""
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _module_repository.list_granted_modules_for_user(
        user_id=id,
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination(
        [_serialize_module_for_permission(module) for module in rows], pagination
    )


@router.get("/get_ungranted_modules")
def get_ungranted_modules(
    request: Request,
    id: int,  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated list of modules the user does NOT yet have access to."""
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _module_repository.list_ungranted_modules_for_user(
        user_id=id,
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination(
        [_serialize_module_for_permission(module) for module in rows], pagination
    )


@router.post("/submit_permission_new")
async def submit_permission_new(
    request: Request, user: UserModel = Depends(_require_access)
) -> dict:
    """Grant a user access to every module id submitted - additive only,
    existing grants are left untouched (unlike the old save_permissions,
    which replaced the whole grant set)."""
    form = await request.form()
    user_id_raw = form.get("user_id", "")
    if not user_id_raw:
        return {"error": "user_id is required"}
    module_ids = [part for part in form.getlist("module_ids") if part]
    if not module_ids:
        return {"error": "Select at least one module"}

    target_user_id = int(user_id_raw)
    for module_id in module_ids:
        _permission_repository.grant_access(
            target_user_id, int(module_id), granted_by=user.id
        )
    return {"message": "Permission added successfully"}


@router.post("/revoke_permission")
async def revoke_permission(
    request: Request, user: UserModel = Depends(_require_access)
) -> dict:
    """Revoke a user's access to every module id submitted (single or
    bulk) - backs the granted-modules table's remove button on edit.py
    (issue #42). Uses the already-existing
    UserModulePermissionRepository.revoke_access, no new repository logic."""
    form = await request.form()
    user_id_raw = form.get("user_id", "")
    if not user_id_raw:
        return {"error": "user_id is required"}
    module_ids = [part for part in form.getlist("module_ids") if part]
    if not module_ids:
        return {"error": "Select at least one module"}

    target_user_id = int(user_id_raw)
    for module_id in module_ids:
        _permission_repository.revoke_access(target_user_id, int(module_id))
    return {"message": "Permission removed successfully"}
