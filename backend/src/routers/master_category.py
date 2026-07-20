"""Category master-data CRUD admin screen (frontend module `master_category`).

Same list/get/submit/delete contract as `master_supplier.py` — see that
file's docstring for the shape. Gated by
`require_module_access("master_category")`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.category import CategoryModel
from models.user import UserModel
from repository.category_repository import CategoryRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_category", tags=["master-category"])
_category_repository = CategoryRepository()

_require_access = require_module_access("master_category")

_EXPORT_COLUMNS = [("code", "Code"), ("name", "Name"), ("description", "Description")]


def _serialize(category: CategoryModel) -> dict:
    return {
        "id": category.id,
        "code": category.code,
        "name": category.name,
        "description": category.description,
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
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _category_repository.list_categories(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize(category) for category in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _category_repository.list_categories(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize(category) for category in rows], _EXPORT_COLUMNS, format, "master_category"
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    category = _category_repository.get_category_by_id(id)
    if category is None:
        return {"error": "Category not found"}
    return _serialize(category)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _category_repository.update_category(
            int(id), code=code, name=name, description=description, updated_by=user.id
        )
        if not updated:
            return {"error": "Category not found"}
        return {"message": "Category updated successfully"}

    _category_repository.create_category(
        code=code, name=name, description=description, created_by=user.id
    )
    return {"message": "Category created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _category_repository.delete_category(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: this category is linked to one or more materials"}
    if not deleted:
        return {"error": "Category not found"}
    return {"message": "Category deleted successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["code", "name", "description"])

    def build(row, session):
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not code or not name:
            raise BulkRowError(row["_row"], "Code and Name are required")
        description = str(row.get("description", "")).strip()
        return CategoryModel(code=code, name=name, description=description, created_by=user.id)

    return bulk_create(rows, build)
