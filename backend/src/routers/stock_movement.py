"""Stock movement (transfer between locations) screens (frontend module
`stock_movement`, issue #31).

Same header/item-subscreen structure as `stock_out.py`, except:
- The header additionally stamps `created_by`/`updated_by` from the
  authenticated session user (a first for this codebase's header tables).
- Items carry BOTH an origin and a destination location - unlike
  `stock_in`/`stock_out`, which each have exactly one location select,
  `call_location_id_select` here feeds the item form's single destination
  dropdown; the origin locations come from `get_stock_by_material` instead
  (same as `stock_out`'s per-location table), not from a select.
- `submit_items` (single-material, multi-origin-location, one fixed
  destination for the whole request) is the only item-write endpoint -
  no `submit_bulk_items` multi-material bulk endpoint like `stock_out` has:
  the per-origin-location entry table on `item_new` is a plain
  `is_inside_form=True` Table with editable "Qty Movement"/"Remarks"
  columns, so it already gets a generic CSV/XLSX upload menu for free
  (`components/table/menu.py::TableMenu` - see AGENTS.md's "Table
  export/upload convention"), no bespoke bulk-upload backend needed.

- GET  C_stock_movement/get_detail -> paginated stock movement headers.
- GET  C_stock_movement/get?id=<id> -> single header {id, date, description}.
- POST C_stock_movement/submit (form: id, date, description) -> upsert
  header, stamping created_by (create) / updated_by (create and update)
  from the current session user.
- POST C_stock_movement/submit_bulk (form: repeated date/description +
  row_number) -> ALL OR NOTHING bulk header create via bulk_service.
- GET  C_stock_movement/get_items?header_id=<id>&table-keyword-filter=&limit=&page=&offset=
  -> paginated items for that header, joined with material_code/name and
  both locations' code/name for display, plus plan_qty/movement_qty
  (remaining computed by the router as plan_qty - movement_qty).
- GET  C_stock_movement/get_stock_by_material?material_id=<id> -> current
  qty per location for one material, qty > 0 only - same shape/endpoint
  contract as C_stock_out/get_stock_by_material (reuses stock_repository
  directly), feeds the item form's per-origin-location "Qty Movement" table.
- POST C_stock_movement/submit_items (form: stock_movement_header_id,
  material_id, destination_location_id, repeated origin_location_id/
  movement_qty/remarks - one triplet per origin-location row with a qty >
  0) -> validates every requested qty against that origin location's
  current stock up front, rejects any row whose origin equals the chosen
  destination, then calls inventory_service.create_stock_movement_item
  once per origin location.
- GET  C_stock_movement/call_material_id_select, call_location_id_select ->
  options for the item form's `select` fields.

Gated by `require_module_access("stock_movement")`.
"""

from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.stock_movement_header import StockMovementHeaderModel
from models.user import UserModel
from repository.location_repository import LocationRepository
from repository.material_repository import MaterialRepository
from repository.stock_movement_repository import StockMovementRepository
from repository.stock_repository import StockRepository
from repository.unit_of_material_repository import UnitOfMaterialRepository
from services import inventory_service
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows
from services.inventory_service import InsufficientStockError, SameLocationMovementError

router = APIRouter(prefix="/C_stock_movement", tags=["stock-movement"])
_stock_movement_repository = StockMovementRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()
_stock_repository = StockRepository()
_unit_repository = UnitOfMaterialRepository()

_require_access = require_module_access("stock_movement")

_EXPORT_DETAIL_COLUMNS = [
    ("date", "Date"),
    ("description", "Description"),
]
_EXPORT_ITEMS_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("origin_location_code", "Origin Location Code"),
    ("origin_location_name", "Origin Location"),
    ("destination_location_code", "Destination Location Code"),
    ("destination_location_name", "Destination Location"),
    ("plan_qty", "Qty Plan"),
    ("movement_qty", "Qty Movement"),
    ("remaining", "Remaining"),
    ("remarks", "Remarks"),
]


def _serialize_header(header) -> dict:
    return {
        "id": header.id,
        "date": header.date.isoformat(),
        "description": header.description,
    }


def _serialize_item(item) -> dict:
    material = _material_repository.get_material_by_id(item.material_id)
    origin = _location_repository.get_location_by_id(item.origin_location_id)
    destination = _location_repository.get_location_by_id(item.destination_location_id)
    unit = _unit_repository.get_unit_by_id(material.unit_id) if material else None
    return {
        "id": item.id,
        "material_code": material.material_code if material else "",
        "material_name": material.material_name if material else "",
        "origin_location_code": origin.code if origin else "",
        "origin_location_name": origin.name if origin else "",
        "destination_location_code": destination.code if destination else "",
        "destination_location_name": destination.name if destination else "",
        "plan_qty": item.plan_qty,
        "movement_qty": item.movement_qty,
        "remaining": item.plan_qty - item.movement_qty,
        "unit_code": unit.code if unit else "",
        "unit_name": unit.name if unit else "",
        "remarks": item.remarks,
        "created_at": item.created_at.isoformat(),
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
    rows, pagination = _stock_movement_repository.list_headers(
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize_header(header) for header in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _stock_movement_repository.list_headers(
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize_header(header) for header in rows],
        _EXPORT_DETAIL_COLUMNS,
        format,
        "stock_movement",
    )


@router.get("/export_items")
def export_items(
    request: Request,
    header_id: int,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    items, _pagination = _stock_movement_repository.list_items_by_header(
        header_id,
        keyword=keyword,
        query_params=request.query_params,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        [_serialize_item(item) for item in items],
        _EXPORT_ITEMS_COLUMNS,
        format,
        f"stock_movement_{header_id}_items",
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    header = _stock_movement_repository.get_header_by_id(id)
    if header is None:
        return {"error": "Stock movement header not found"}
    return _serialize_header(header)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    date: date_type = Form(...),
    description: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _stock_movement_repository.update_header(
            int(id), date=date, description=description, updated_by=user.id
        )
        if not updated:
            return {"error": "Stock movement header not found"}
        return {"message": "Stock movement header updated successfully"}

    _stock_movement_repository.create_header(
        date=date, description=description, created_by=user.id
    )
    return {"message": "Stock movement header created successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["date", "description"])

    def build(row, session):
        date_raw = str(row.get("date", "")).strip()
        if not date_raw:
            raise BulkRowError(row["_row"], "Date is required")
        try:
            date_value = date_type.fromisoformat(date_raw)
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid date: {date_raw} (expected YYYY-MM-DD)")
        return StockMovementHeaderModel(
            date=date_value,
            description=str(row.get("description", "")).strip(),
            created_by=user.id,
            updated_by=user.id,
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
    sort_fields = parse_sort_fields(request.query_params)
    items, pagination = _stock_movement_repository.list_items_by_header(
        header_id,
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination([_serialize_item(item) for item in items], pagination)


@router.get("/get_stock_by_material")
def get_stock_by_material(material_id: int, user: UserModel = Depends(_require_access)) -> list:
    return _stock_repository.list_stock_by_material(material_id)


@router.post("/submit_items")
async def submit_items(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    stock_movement_header_id = form.get("stock_movement_header_id")
    material_id = form.get("material_id")
    destination_location_id = form.get("destination_location_id")
    origin_location_ids = form.getlist("origin_location_id")
    movement_qtys = form.getlist("movement_qty")
    remarks_list = form.getlist("remarks")

    if not stock_movement_header_id or not material_id:
        return {"error": "Material is required"}
    if not destination_location_id:
        return {"error": "Destination location is required"}

    # Parse and drop blank/zero rows first, same convention as
    # stock_out.py::submit_items - "enter a qty for some of the origin
    # locations, leave the rest blank" is the whole point of this table.
    requested: dict[int, Decimal] = {}
    remarks_by_location: dict[int, str] = {}
    for origin_location_id, qty_raw, remarks in zip(
        origin_location_ids, movement_qtys, remarks_list
    ):
        if not str(qty_raw).strip():
            continue
        try:
            movement_qty = Decimal(str(qty_raw))
        except InvalidOperation:
            return {"error": f"Invalid quantity: {qty_raw}"}
        if movement_qty <= 0:
            continue
        requested[int(origin_location_id)] = movement_qty
        remarks_by_location[int(origin_location_id)] = remarks

    if not requested:
        return {"error": "Enter a quantity to move for at least one location"}

    if int(destination_location_id) in requested:
        return {"error": "Origin and destination location cannot be the same"}

    # Validate every requested qty against current stock up front, so a
    # shortfall at any one origin location rejects the whole submission
    # instead of moving some locations and silently failing on others.
    available = {
        row["location_id"]: row["qty"]
        for row in _stock_repository.list_stock_by_material(int(material_id))
    }
    for origin_location_id, movement_qty in requested.items():
        on_hand = available.get(origin_location_id, Decimal("0"))
        if movement_qty > on_hand:
            location = _location_repository.get_location_by_id(origin_location_id)
            location_label = location.name if location else f"location {origin_location_id}"
            return {
                "error": f"Insufficient stock: only {on_hand} available at {location_label}"
            }

    try:
        for origin_location_id, movement_qty in requested.items():
            inventory_service.create_stock_movement_item(
                stock_movement_header_id=int(stock_movement_header_id),
                material_id=int(material_id),
                origin_location_id=origin_location_id,
                destination_location_id=int(destination_location_id),
                movement_qty=movement_qty,
                remarks=remarks_by_location[origin_location_id],
                created_by=user.id,
            )
    except SameLocationMovementError:
        return {"error": "Origin and destination location cannot be the same"}
    except InsufficientStockError as exc:
        # Only reachable if stock changed concurrently after the up-front
        # check above - the common case is already caught there.
        return {"error": f"Insufficient stock: only {exc.available} available"}

    return {"message": f"Stock moved from {len(requested)} location(s) successfully"}


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
