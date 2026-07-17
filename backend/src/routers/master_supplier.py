"""Supplier master-data CRUD admin screen (frontend module `master_supplier`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_supplier")`.
"""

from fastapi import APIRouter, Depends, Form, Query, Request
from sqlalchemy.exc import IntegrityError

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.supplier import SupplierModel
from models.user import UserModel
from repository.supplier_repository import SupplierRepository
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_master_supplier", tags=["master-supplier"])
_supplier_repository = SupplierRepository()

_require_access = require_module_access("master_supplier")

_EXPORT_COLUMNS = [("code", "Code"), ("name", "Name")]


def _serialize(supplier: SupplierModel) -> dict:
    return {"id": supplier.id, "code": supplier.code, "name": supplier.name}


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
    rows, pagination = _supplier_repository.list_suppliers(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize(supplier) for supplier in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _supplier_repository.list_suppliers(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize(supplier) for supplier in rows], _EXPORT_COLUMNS, format, "master_supplier"
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    supplier = _supplier_repository.get_supplier_by_id(id)
    if supplier is None:
        return {"error": "Supplier not found"}
    return _serialize(supplier)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    code: str = Form(...),
    name: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _supplier_repository.update_supplier(int(id), code=code, name=name)
        if not updated:
            return {"error": "Supplier not found"}
        return {"message": "Supplier updated successfully"}

    _supplier_repository.create_supplier(code=code, name=name)
    return {"message": "Supplier created successfully"}


@router.post("/delete")
def delete(id: str = Form(...), user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    try:
        deleted = _supplier_repository.delete_supplier(int(id))
    except IntegrityError:
        return {"error": "Cannot delete: this supplier is linked to one or more materials"}
    if not deleted:
        return {"error": "Supplier not found"}
    return {"message": "Supplier deleted successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["code", "name"])

    def build(row, session):
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not code or not name:
            raise BulkRowError(row["_row"], "Code and Name are required")
        return SupplierModel(code=code, name=name)

    return bulk_create(rows, build)
