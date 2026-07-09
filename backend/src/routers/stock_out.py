"""Stock out (issue) screens (frontend module `stock_out`).

Same header/item-subscreen structure as `stock_in.py`, except items are
create-only (no `submit_item` update path, no `get_item`) — see
`services.inventory_service` for why editing an issue isn't supported.

- GET  C_stock_out/get_detail -> paginated stock out headers, including
  department_id/department_name (each transaction is issued to exactly one
  department, for usage reporting).
- GET  C_stock_out/get?id=<id> -> single header {id, date, description,
  department_id, department_name}.
- POST C_stock_out/submit (form: id, date, description, department_id) ->
  upsert header. `department_id` is required — every stock-out transaction
  must be attributed to a department.
- GET  C_stock_out/get_items?header_id=<id> -> that header's items, joined
  with material_code/name and location_code/name, plus the captured price
  and total_value.
- POST C_stock_out/submit_item (form: stock_out_header_id, material_id,
  location_id, qty_out, remarks) -> services.inventory_service.
  create_stock_out_item; {"error": "..."} (still HTTP 200) if there isn't
  enough stock at that location.
- GET  C_stock_out/call_material_id_select, call_location_id_select,
  call_department_id_select -> options for the header/item forms' `select`
  fields.

Gated by `require_module_access("stock_out")`.
"""

import math
from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query

from models.user import UserModel
from repository.department_repository import DepartmentRepository
from repository.location_repository import LocationRepository
from repository.material_repository import MaterialRepository
from repository.stock_out_repository import StockOutRepository
from services import inventory_service
from services.auth_service import require_module_access
from services.inventory_service import InsufficientStockError

router = APIRouter(prefix="/C_stock_out", tags=["stock-out"])
_stock_out_repository = StockOutRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()
_department_repository = DepartmentRepository()

_require_access = require_module_access("stock_out")


def _serialize_header(header) -> dict:
    department = (
        _department_repository.get_department_by_id(header.department_id)
        if header.department_id
        else None
    )
    return {
        "id": header.id,
        "date": header.date.isoformat(),
        "description": header.description,
        "department_id": str(header.department_id) if header.department_id else "",
        "department_name": department.name if department else "",
    }


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _stock_out_repository.list_headers(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for header in rows:
        row = _serialize_header(header)
        row["db_total_page"] = total_pages
        row["db_num_rows"] = total
        result.append(row)
    return result


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    header = _stock_out_repository.get_header_by_id(id)
    if header is None:
        return {"error": "Stock out header not found"}
    return _serialize_header(header)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    date: date_type = Form(...),
    description: str = Form(""),
    department_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if not department_id:
        return {"error": "Department is required"}
    department_id_value = int(department_id)

    if id:
        updated = _stock_out_repository.update_header(
            int(id), date=date, description=description, department_id=department_id_value
        )
        if not updated:
            return {"error": "Stock out header not found"}
        return {"message": "Stock out header updated successfully"}

    _stock_out_repository.create_header(
        date=date, description=description, department_id=department_id_value
    )
    return {"message": "Stock out header created successfully"}


@router.get("/get_items")
def get_items(header_id: int, user: UserModel = Depends(_require_access)) -> list:
    items = _stock_out_repository.list_items_by_header(header_id)
    result = []
    for item in items:
        material = _material_repository.get_material_by_id(item.material_id)
        location = _location_repository.get_location_by_id(item.location_id)
        result.append(
            {
                "id": item.id,
                "material_code": material.material_code if material else "",
                "material_name": material.material_name if material else "",
                "location_code": location.code if location else "",
                "location_name": location.name if location else "",
                "qty_out": item.qty_out,
                "price": item.price,
                "total_value": item.total_value,
                "remarks": item.remarks,
                "db_total_page": 1,
                "db_num_rows": len(items),
            }
        )
    return result


@router.post("/submit_item")
def submit_item(
    stock_out_header_id: str = Form(...),
    material_id: str = Form(...),
    location_id: str = Form(...),
    qty_out: Decimal = Form(...),
    remarks: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if qty_out <= 0:
        return {"error": "Quantity out must be greater than zero"}

    try:
        inventory_service.create_stock_out_item(
            stock_out_header_id=int(stock_out_header_id),
            material_id=int(material_id),
            location_id=int(location_id),
            qty_out=qty_out,
            remarks=remarks,
        )
    except InsufficientStockError as exc:
        return {"error": f"Insufficient stock: only {exc.available} available at this location"}

    return {"message": "Stock out item added successfully"}


@router.get("/call_material_id_select")
def call_material_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(m.id), "label": f"{m.material_code} - {m.material_name}"}
        for m in _material_repository.get_all_materials()
    ]


@router.get("/call_location_id_select")
def call_location_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(loc.id), "label": f"{loc.code} - {loc.name}"}
        for loc in _location_repository.get_all_locations()
    ]


@router.get("/call_department_id_select")
def call_department_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(d.id), "label": f"{d.code} - {d.name}"}
        for d in _department_repository.get_all_departments()
    ]
