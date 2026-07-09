"""Department master-data CRUD admin screen (frontend module `master_department`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_department")`.
"""

import math

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.exc import IntegrityError

from models.department import DepartmentModel
from models.user import UserModel
from repository.department_repository import DepartmentRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_department", tags=["master-department"])
_department_repository = DepartmentRepository()

_require_access = require_module_access("master_department")


def _serialize(department: DepartmentModel) -> dict:
    return {"id": department.id, "code": department.code, "name": department.name}


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _department_repository.list_departments(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for department in rows:
        row = _serialize(department)
        row["db_total_page"] = total_pages
        row["db_num_rows"] = total
        result.append(row)
    return result


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
