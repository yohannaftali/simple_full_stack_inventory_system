"""Module group CRUD admin screen (frontend module `master_module_group`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_module_group")`.
Groups categorize modules (e.g. Inventory, Master, Application Configuration)
for display/organization; `module_admin.py`'s `call_module_group_id_select`
sources its options from `get_all_groups` here.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination
from models.module_group import ModuleGroupModel
from models.user import UserModel
from repository.module_group_repository import ModuleGroupRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_module_group", tags=["master-module-group"])
_module_group_repository = ModuleGroupRepository()

_require_access = require_module_access("master_module_group")

_EXPORT_COLUMNS = [("name", "Name"), ("sort", "Sort")]


def _serialize(group: ModuleGroupModel) -> dict:
    return {"id": group.id, "name": group.name, "sort": group.sort}


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    rows, pagination = _module_group_repository.list_groups(
        keyword=keyword, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize(group) for group in rows], pagination)


@router.get("/export_detail")
def export_detail(
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _module_group_repository.list_groups(keyword=keyword, limit=0, page=1, offset=0)
    return export_response(
        [_serialize(group) for group in rows], _EXPORT_COLUMNS, format, "master_module_group"
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    group = _module_group_repository.get_group_by_id(id)
    if group is None:
        return {"error": "Module group not found"}
    return _serialize(group)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    name: str = Form(...),
    sort: str = Form("0"),
    user: UserModel = Depends(_require_access),
) -> dict:
    try:
        sort_value = int(sort) if sort else 0
    except ValueError:
        return {"error": "Sort must be a number"}

    if id:
        updated = _module_group_repository.update_group(int(id), name=name, sort=sort_value)
        if not updated:
            return {"error": "Module group not found"}
        return {"message": "Module group updated successfully"}

    _module_group_repository.create_group(name=name, sort=sort_value)
    return {"message": "Module group created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _module_group_repository.delete_group(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: one or more modules still belong to this group"}
    if not deleted:
        return {"error": "Module group not found"}
    return {"message": "Module group deleted successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["name", "sort"])

    def build(row, session):
        name = str(row.get("name", "")).strip()
        if not name:
            raise BulkRowError(row["_row"], "Name is required")
        sort_raw = str(row.get("sort", "")).strip()
        try:
            sort_value = int(sort_raw) if sort_raw else 0
        except ValueError:
            raise BulkRowError(row["_row"], "Sort must be a number")
        return ModuleGroupModel(name=name, sort=sort_value)

    return bulk_create(rows, build)
