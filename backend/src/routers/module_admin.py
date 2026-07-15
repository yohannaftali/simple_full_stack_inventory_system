"""Module CRUD admin screen (frontend module `ap_module`).

Contract (see components/table/table.py and components/form/form.py):
- GET  C_ap_module/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> list of module dicts, each carrying `db_total_page`/`db_num_rows`
  pagination metadata (the list table).
- GET  C_ap_module/get?id=<id> -> single module dict (the edit form).
- POST C_ap_module/submit (form: id, name, label, sort, icon, description,
  module_group_id) -> upsert (blank/missing id = create), {"message": "..."}
  or {"error": "..."}. `module_group_id` is optional (blank = ungrouped).
- POST C_ap_module/delete (form: id) -> {"message": "..."} or {"error": "..."}.
- GET  C_ap_module/call_module_group_id_select -> options for the new/edit
  form's `module_group_id` select field, sourced from `master_module_group`.

All routes require `ap_module` access (or superuser) via `require_module_access`.

Known limitation: if there are zero rows, `get_detail` still returns a list
(possibly empty); the frontend's `Table.get_data()` indexes `response[0]` for
pagination metadata and will raise on a genuinely empty result set. That's an
existing frontend behavior, not something this router works around.
"""

from fastapi import APIRouter, Depends, Form, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination
from models.module import ModuleModel
from models.user import UserModel
from repository.module_group_repository import ModuleGroupRepository
from repository.module_repository import ModuleRepository
from repository.user_module_permission_repository import UserModulePermissionRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_ap_module", tags=["module-admin"])
_module_repository = ModuleRepository()
_permission_repository = UserModulePermissionRepository()
_module_group_repository = ModuleGroupRepository()

_require_access = require_module_access("ap_module")

_EXPORT_COLUMNS = [
    ("name", "Name"),
    ("label", "Label"),
    ("sort", "Sort"),
    ("icon", "Icon"),
    ("description", "Description"),
    ("module_group_name", "Group"),
]


def _serialize(module: ModuleModel) -> dict:
    group = (
        _module_group_repository.get_group_by_id(module.module_group_id)
        if module.module_group_id
        else None
    )
    return {
        "id": module.id,
        "name": module.name,
        "label": module.label,
        "sort": module.sort,
        "icon": module.icon,
        "description": module.description,
        "module_group_id": str(module.module_group_id) if module.module_group_id else "",
        "module_group_name": group.name if group else "",
    }


@router.get("/get_detail")
def get_detail(
    request: Request,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    """Paginated module list for the admin list screen."""
    rows, pagination = _module_repository.list_modules(
        keyword=keyword, query_params=request.query_params, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize(module) for module in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _module_repository.list_modules(
        keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
    return export_response([_serialize(module) for module in rows], _EXPORT_COLUMNS, format, "ap_module")


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
    module_group_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    """Create or update a module (blank/missing id = create)."""
    try:
        sort_value = int(sort) if sort else 0
    except ValueError:
        return {"error": "Sort must be a number"}

    module_group_id_value = int(module_group_id) if module_group_id else None

    if id:
        updated = _module_repository.update_module(
            module_id=int(id),
            name=name,
            label=label,
            sort=sort_value,
            icon=icon or "chevron_right",
            description=description,
            module_group_id=module_group_id_value,
        )
        if not updated:
            return {"error": "Module not found"}
        return {"message": "Module updated successfully"}

    _module_repository.create_module(
        name=name, label=label, sort=sort_value, icon=icon or "chevron_right",
        description=description, module_group_id=module_group_id_value,
    )
    return {"message": "Module created successfully"}


@router.get("/call_module_group_id_select")
def call_module_group_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(g.id), "label": g.name}
        for g in _module_group_repository.get_all_groups()
    ]


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    """Delete a module and every permission grant referencing it."""
    module_id = int(id)
    _permission_repository.delete_permissions_for_module(module_id)
    deleted = _module_repository.delete_module(module_id)
    if not deleted:
        return {"error": "Module not found"}
    return {"message": "Module deleted successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(
        form, ["name", "label", "sort", "icon", "description", "module_group_id"]
    )

    def build(row, session):
        name = str(row.get("name", "")).strip()
        label = str(row.get("label", "")).strip()
        if not name or not label:
            raise BulkRowError(row["_row"], "Name and Label are required")
        sort_raw = str(row.get("sort", "")).strip()
        try:
            sort_value = int(sort_raw) if sort_raw else 0
        except ValueError:
            raise BulkRowError(row["_row"], "Sort must be a number")
        group_raw = str(row.get("module_group_id", "")).strip()
        try:
            module_group_id = int(group_raw) if group_raw else None
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Group: {group_raw}")
        return ModuleModel(
            name=name,
            label=label,
            sort=sort_value,
            icon=str(row.get("icon", "")).strip() or "chevron_right",
            description=str(row.get("description", "")).strip(),
            module_group_id=module_group_id,
        )

    return bulk_create(rows, build)
