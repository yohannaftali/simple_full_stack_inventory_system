"""Module CRUD admin screen (frontend module `ap_module`).

Contract (see components/table/table.py and components/form/form.py):
- GET  C_ap_module/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> list of module dicts, each carrying `db_total_page`/`db_num_rows`
  pagination metadata (the list table).
- GET  C_ap_module/get?id=<id> -> single module dict (the edit form).
- POST C_ap_module/submit (form: id, name, label, sort, icon, description)
  -> upsert (blank/missing id = create), {"message": "..."} or {"error": "..."}.
- POST C_ap_module/delete (form: id) -> {"message": "..."} or {"error": "..."}.

All routes require `ap_module` access (or superuser) via `require_module_access`.

Known limitation: if there are zero rows, `get_detail` still returns a list
(possibly empty); the frontend's `Table.get_data()` indexes `response[0]` for
pagination metadata and will raise on a genuinely empty result set. That's an
existing frontend behavior, not something this router works around.
"""

from fastapi import APIRouter, Depends, Form, Query

from core.table_query import attach_pagination
from models.module import ModuleModel
from models.user import UserModel
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_ap_module", tags=["module-admin"])
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()

_require_access = require_module_access("ap_module")


def _serialize(module: ModuleModel) -> dict:
    return {
        "id": module.id,
        "name": module.name,
        "label": module.label,
        "sort": module.sort,
        "icon": module.icon,
        "description": module.description,
    }


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated module list for the admin list screen."""
    rows, pagination = _module_repository.list_modules(
        keyword=keyword, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize(module) for module in rows], pagination)


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """Single module record for the edit form."""
    module = _module_repository.get_module_by_id(id)
    if module is None:
        return {"error": "Module not found"}
    return _serialize(module)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    name: str = Form(...),
    label: str = Form(...),
    sort: str = Form("0"),
    icon: str = Form("chevron_right"),
    description: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    """Create or update a module (blank/missing id = create)."""
    try:
        sort_value = int(sort) if sort else 0
    except ValueError:
        return {"error": "Sort must be a number"}

    if id:
        updated = _module_repository.update_module(
            module_id=int(id),
            name=name,
            label=label,
            sort=sort_value,
            icon=icon or "chevron_right",
            description=description,
        )
        if not updated:
            return {"error": "Module not found"}
        return {"message": "Module updated successfully"}

    _module_repository.create_module(
        name=name, label=label, sort=sort_value, icon=icon or "chevron_right",
        description=description,
    )
    return {"message": "Module created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """Delete a module and every permission grant referencing it."""
    module_id = int(id)
    _permission_repository.delete_permissions_for_module(module_id)
    deleted = _module_repository.delete_module(module_id)
    if not deleted:
        return {"error": "Module not found"}
    return {"message": "Module deleted successfully"}
