"""Department master-data CRUD admin screen (frontend module `master_department`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_department")`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.department import DepartmentModel
from models.user import UserModel
from repository.department_repository import DepartmentRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_department", tags=["master-department"])
_department_repository = DepartmentRepository()

_require_access = require_module_access("master_department")

_EXPORT_COLUMNS = [("code", "Code"), ("name", "Name")]


def _serialize(department: DepartmentModel) -> dict:
    return {"id": department.id, "code": department.code, "name": department.name}


@router.get("/get_detail")
def get_detail(
    request: Request,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _department_repository.list_departments(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize(department) for department in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _department_repository.list_departments(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize(department) for department in rows], _EXPORT_COLUMNS, format, "master_department"
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    department = _department_repository.get_department_by_id(id)
    if department is None:
        return {"error": "Department not found"}
    return _serialize(department)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    code: str = Form(...),
    name: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _department_repository.update_department(int(id), code=code, name=name)
        if not updated:
            return {"error": "Department not found"}
        return {"message": "Department updated successfully"}

    _department_repository.create_department(code=code, name=name)
    return {"message": "Department created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _department_repository.delete_department(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: this department is linked to one or more users/transactions"}
    if not deleted:
        return {"error": "Department not found"}
    return {"message": "Department deleted successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["code", "name"])

    def build(row, session):
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not code or not name:
            raise BulkRowError(row["_row"], "Code and Name are required")
        return DepartmentModel(code=code, name=name)

    return bulk_create(rows, build)
