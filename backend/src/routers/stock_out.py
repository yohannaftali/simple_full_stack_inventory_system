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
- GET  C_stock_out/get_items?header_id=<id>&table-keyword-filter=&limit=&page=&offset=
  -> paginated items for that header (keyword matches `remarks`), joined
  with material_code/name and location_code/name, plus the captured price
  and total_value.
- GET  C_stock_out/get_stock_by_material?material_id=<id> -> current qty per
  location for one material, qty > 0 only ({"location_id",
  "location_code", "location_name", "qty"}) - feeds the item form's
  per-location "Qty Issue" table so the user can see what's available
  before typing a quantity.
- POST C_stock_out/submit_items (form: stock_out_header_id, material_id,
  repeated location_id/qty_out/remarks - one triplet per location row with
  a qty > 0) -> validates every requested qty against that location's
  current stock up front (so a shortfall anywhere rejects the whole
  submission instead of partially issuing), then calls
  services.inventory_service.create_stock_out_item once per location.
  Replaces the older single-location `submit_item` shape - issuing is
  now "pick a material, then a qty per location" instead of "pick a
  material and one location", matching FIFO-by-location semantics but
  letting one screen issue from several locations at once.
- GET  C_stock_out/call_material_id_select, call_location_id_select,
  call_department_id_select -> options for the header form's `select`
  fields (`call_location_id_select` is unused by the item form now, kept
  for parity/possible future use).

Gated by `require_module_access("stock_out")`.
"""

from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination
from models.user import UserModel
from repository.department_repository import DepartmentRepository
from repository.location_repository import LocationRepository
from repository.material_repository import MaterialRepository
from repository.stock_out_repository import StockOutRepository
from models.stock_out_header import StockOutHeaderModel
from repository.stock_repository import StockRepository
from repository.unit_of_material_repository import UnitOfMaterialRepository
from services import inventory_service
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows
from services.inventory_service import InsufficientStockError

router = APIRouter(prefix="/C_stock_out", tags=["stock-out"])
_stock_out_repository = StockOutRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()
_department_repository = DepartmentRepository()
_stock_repository = StockRepository()
_unit_repository = UnitOfMaterialRepository()

_require_access = require_module_access("stock_out")

_EXPORT_DETAIL_COLUMNS = [
    ("date", "Date"),
    ("description", "Description"),
    ("department_name", "Department"),
]
_EXPORT_ITEMS_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("location_code", "Location Code"),
    ("location_name", "Location"),
    ("qty_out", "Qty Out"),
    ("unit_name", "Unit"),
    ("price", "Price"),
    ("total_value", "Total Value"),
    ("remarks", "Remarks"),
]


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


def _serialize_item(item) -> dict:
    material = _material_repository.get_material_by_id(item.material_id)
    location = _location_repository.get_location_by_id(item.location_id)
    unit = _unit_repository.get_unit_by_id(material.unit_id) if material else None
    return {
        "id": item.id,
        "material_code": material.material_code if material else "",
        "material_name": material.material_name if material else "",
        "location_code": location.code if location else "",
        "location_name": location.name if location else "",
        "qty_out": item.qty_out,
        "unit_code": unit.code if unit else "",
        "unit_name": unit.name if unit else "",
        "price": item.price,
        "total_value": item.total_value,
        "remarks": item.remarks,
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
    rows, pagination = _stock_out_repository.list_headers(
        keyword=keyword, query_params=request.query_params, limit=limit, page=page, offset=offset
    )
    return attach_pagination([_serialize_header(header) for header in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _stock_out_repository.list_headers(
        keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
    return export_response(
        [_serialize_header(header) for header in rows], _EXPORT_DETAIL_COLUMNS, format, "stock_out"
    )


@router.get("/export_items")
def export_items(
    request: Request,
    header_id: int,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    items, _pagination = _stock_out_repository.list_items_by_header(
        header_id, keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
    return export_response(
        [_serialize_item(item) for item in items],
        _EXPORT_ITEMS_COLUMNS,
        format,
        f"stock_out_{header_id}_items",
    )


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


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["date", "description", "department_id"])

    def build(row, session):
        date_raw = str(row.get("date", "")).strip()
        if not date_raw:
            raise BulkRowError(row["_row"], "Date is required")
        try:
            date_value = date_type.fromisoformat(date_raw)
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid date: {date_raw} (expected YYYY-MM-DD)")
        department_raw = str(row.get("department_id", "")).strip()
        if not department_raw:
            raise BulkRowError(row["_row"], "Department is required")
        try:
            department_id = int(department_raw)
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Department: {department_raw}")
        return StockOutHeaderModel(
            date=date_value,
            description=str(row.get("description", "")).strip(),
            department_id=department_id,
        )

    return bulk_create(rows, build)


@router.get("/get_items")
def get_items(
    request: Request,
    header_id: int,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    items, pagination = _stock_out_repository.list_items_by_header(
        header_id,
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
    )
    return attach_pagination([_serialize_item(item) for item in items], pagination)


@router.get("/get_stock_by_material")
def get_stock_by_material(material_id: int, user: UserModel = Depends(_require_access)) -> list:
    return _stock_repository.list_stock_by_material(material_id)


@router.post("/submit_items")
async def submit_items(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    stock_out_header_id = form.get("stock_out_header_id")
    material_id = form.get("material_id")
    location_ids = form.getlist("location_id")
    qty_outs = form.getlist("qty_out")
    remarks_list = form.getlist("remarks")

    if not stock_out_header_id or not material_id:
        return {"error": "Material is required"}

    # Parse and drop blank/zero rows first, so "enter a qty for some of the
    # locations, leave the rest blank" (the whole point of this table) never
    # reaches inventory_service.
    requested: dict[int, Decimal] = {}
    remarks_by_location: dict[int, str] = {}
    for location_id, qty_out_raw, remarks in zip(location_ids, qty_outs, remarks_list):
        if not str(qty_out_raw).strip():
            continue
        try:
            qty_out = Decimal(str(qty_out_raw))
        except InvalidOperation:
            return {"error": f"Invalid quantity: {qty_out_raw}"}
        if qty_out <= 0:
            continue
        requested[int(location_id)] = qty_out
        remarks_by_location[int(location_id)] = remarks

    if not requested:
        return {"error": "Enter a quantity to issue for at least one location"}

    # Validate every requested qty against current stock up front, so a
    # shortfall at any one location rejects the whole submission instead of
    # issuing some locations and silently failing on others.
    available = {
        row["location_id"]: row["qty"]
        for row in _stock_repository.list_stock_by_material(int(material_id))
    }
    for location_id, qty_out in requested.items():
        on_hand = available.get(location_id, Decimal("0"))
        if qty_out > on_hand:
            location = _location_repository.get_location_by_id(location_id)
            location_label = location.name if location else f"location {location_id}"
            return {
                "error": f"Insufficient stock: only {on_hand} available at {location_label}"
            }

    try:
        for location_id, qty_out in requested.items():
            inventory_service.create_stock_out_item(
                stock_out_header_id=int(stock_out_header_id),
                material_id=int(material_id),
                location_id=location_id,
                qty_out=qty_out,
                remarks=remarks_by_location[location_id],
            )
    except InsufficientStockError as exc:
        # Only reachable if stock changed concurrently after the up-front
        # check above - the common case is already caught there.
        return {"error": f"Insufficient stock: only {exc.available} available"}

    return {"message": f"Stock issued from {len(requested)} location(s) successfully"}


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
