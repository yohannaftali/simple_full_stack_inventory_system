"""Supplier master-data CRUD admin screen (frontend module `master_supplier`).

Same list/get/submit/delete contract as `module_admin.py` — see that file's
docstring for the shape. Gated by `require_module_access("master_supplier")`.
"""

import math

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.exc import IntegrityError

from models.supplier import SupplierModel
from models.user import UserModel
from repository.supplier_repository import SupplierRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_master_supplier", tags=["master-supplier"])
_supplier_repository = SupplierRepository()

_require_access = require_module_access("master_supplier")


def _serialize(supplier: SupplierModel) -> dict:
    return {"id": supplier.id, "code": supplier.code, "name": supplier.name}


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _supplier_repository.list_suppliers(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for supplier in rows:
        row = _serialize(supplier)
        row["db_total_page"] = total_pages
        row["db_num_rows"] = total
        result.append(row)
    return result


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
