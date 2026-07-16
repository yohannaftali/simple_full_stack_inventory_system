"""Stock in (receiving) screens (frontend module `stock_in`).

Header list/get/submit follows the standard Table/Form contract (see
`module_admin.py`). Items are a separate sub-screen flow, not an embedded
Form table field (see AGENTS.md for why): the header's edit screen shows a
plain `Table` of its items (`GET C_stock_in/get_items?header_id=`), with a
"+" button navigating to an item_new screen that posts to
`POST C_stock_in/submit_item`; clicking a row navigates to an item_edit
screen (material/location are then read-only — see inventory_service).

- GET  C_stock_in/get_detail -> paginated receiving headers, including
  supplier_id/supplier_name (optional - a receiving header may predate the
  supplier link, or the shipment's supplier may be unknown). Keyword search
  also matches the linked supplier's code/name, not just description.
- GET  C_stock_in/get?id=<id> -> single header {id, date, description,
  supplier_id, supplier_name}.
- POST C_stock_in/submit (form: id, date, description, supplier_id) ->
  upsert header. supplier_id is optional (blank = no supplier recorded).
- GET  C_stock_in/get_items?header_id=<id>&table-keyword-filter=&limit=&page=&offset=
  -> paginated items for that header (keyword matches `remarks`), joined
  with material_code/name and location_code/name for display.
- GET  C_stock_in/get_item?id=<item_id> -> single item for the edit screen:
  {id, material_name, location_name, qty_received, price_buy, remarks}.
- POST C_stock_in/submit_item (form: id [blank=create], receiving_header_id
  [required on create], material_id, location_id [required on create],
  qty_received, price_buy, remarks) -> services.inventory_service create/update.
  The create path rejects an inactive material (`materials.is_active`, issue
  #17) with `{"error": "Cannot receive: material is inactive"}` - editing an
  existing item (id present) is unaffected, since that material was already
  receivable at the time it was first received.
- POST C_stock_in/submit_bulk_item (form: receiving_header_id, repeated
  material_id/location_id/qty_received/price_buy/remarks + row_number,
  same wire shape as submit_bulk) -> ALL OR NOTHING bulk item creation via
  `inventory_service.create_receiving_items_bulk` (issue #24) - unlike the
  header-level `submit_bulk` above, this doesn't go through
  `bulk_service.bulk_create` (whose single `session.add(build_instance(...))`
  shape doesn't fit a receiving item's three co-dependent writes), it's a
  bespoke bulk function living in `inventory_service.py` alongside
  `create_receiving_item`, following the same ALL-OR-NOTHING/one-session
  convention.
- GET  C_stock_in/call_material_id_select, call_location_id_select -> options
  for the item form's `select` fields.
- GET  C_stock_in/call_supplier_id_select -> options for the header form's
  `supplier_id` select field.

Gated by `require_module_access("stock_in")`.
"""

from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination
from models.receiving_header import ReceivingHeaderModel
from models.user import UserModel
from repository.location_repository import LocationRepository
from repository.material_repository import MaterialRepository
from repository.receiving_repository import ReceivingRepository
from repository.supplier_repository import SupplierRepository
from repository.unit_of_material_repository import UnitOfMaterialRepository
from services import inventory_service
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_stock_in", tags=["stock-in"])
_receiving_repository = ReceivingRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()
_supplier_repository = SupplierRepository()
_unit_repository = UnitOfMaterialRepository()

_require_access = require_module_access("stock_in")

_EXPORT_DETAIL_COLUMNS = [
    ("date", "Date"),
    ("description", "Description"),
    ("supplier_name", "Supplier"),
]
_EXPORT_ITEMS_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("location_code", "Location Code"),
    ("location_name", "Location"),
    ("qty_received", "Qty"),
    ("unit_name", "Unit"),
    ("price_buy", "Price"),
    ("remarks", "Remarks"),
]


def _serialize_header(header) -> dict:
    supplier = (
        _supplier_repository.get_supplier_by_id(header.supplier_id)
        if header.supplier_id
        else None
    )
    return {
        "id": header.id,
        "date": header.date.isoformat(),
        "description": header.description,
        "supplier_id": str(header.supplier_id) if header.supplier_id else "",
        "supplier_name": supplier.name if supplier else "",
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
        "qty_received": item.qty_received,
        "unit_code": unit.code if unit else "",
        "unit_name": unit.name if unit else "",
        "price_buy": item.price_buy,
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
    rows, pagination = _receiving_repository.list_headers(
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
    rows, _pagination = _receiving_repository.list_headers(
        keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
    return export_response(
        [_serialize_header(header) for header in rows], _EXPORT_DETAIL_COLUMNS, format, "stock_in"
    )


@router.get("/export_items")
def export_items(
    request: Request,
    header_id: int,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    items, _pagination = _receiving_repository.list_items_by_header(
        header_id, keyword=keyword, query_params=request.query_params, limit=0, page=1, offset=0
    )
    return export_response(
        [_serialize_item(item) for item in items],
        _EXPORT_ITEMS_COLUMNS,
        format,
        f"stock_in_{header_id}_items",
    )


@router.get("/get")
def get(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    header = _receiving_repository.get_header_by_id(id)
    if header is None:
        return {"error": "Receiving header not found"}
    return _serialize_header(header)


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    date: date_type = Form(...),
    description: str = Form(""),
    supplier_id: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    supplier_id_value = int(supplier_id) if supplier_id else None

    if id:
        updated = _receiving_repository.update_header(
            int(id), date=date, description=description, supplier_id=supplier_id_value
        )
        if not updated:
            return {"error": "Receiving header not found"}
        return {"message": "Receiving header updated successfully"}

    _receiving_repository.create_header(
        date=date, description=description, supplier_id=supplier_id_value
    )
    return {"message": "Receiving header created successfully"}


@router.post("/submit_bulk")
async def submit_bulk(request: Request, user: UserModel = Depends(_require_access)) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(form, ["date", "description", "supplier_id"])

    def build(row, session):
        date_raw = str(row.get("date", "")).strip()
        if not date_raw:
            raise BulkRowError(row["_row"], "Date is required")
        try:
            date_value = date_type.fromisoformat(date_raw)
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid date: {date_raw} (expected YYYY-MM-DD)")
        supplier_raw = str(row.get("supplier_id", "")).strip()
        try:
            supplier_id = int(supplier_raw) if supplier_raw else None
        except ValueError:
            raise BulkRowError(row["_row"], f"Invalid Supplier: {supplier_raw}")
        return ReceivingHeaderModel(
            date=date_value,
            description=str(row.get("description", "")).strip(),
            supplier_id=supplier_id,
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
    items, pagination = _receiving_repository.list_items_by_header(
        header_id,
        keyword=keyword,
        query_params=request.query_params,
        limit=limit,
        page=page,
        offset=offset,
    )
    return attach_pagination([_serialize_item(item) for item in items], pagination)


@router.get("/get_item")
def get_item(id: int, user: UserModel = Depends(_require_access)) -> dict:  # noqa: A002
    item = _receiving_repository.get_item_by_id(id)
    if item is None:
        return {"error": "Receiving item not found"}

    material = _material_repository.get_material_by_id(item.material_id)
    location = _location_repository.get_location_by_id(item.location_id)
    return {
        "id": item.id,
        "material_name": (
            f"{material.material_code} - {material.material_name}" if material else ""
        ),
        "location_name": f"{location.code} - {location.name}" if location else "",
        "qty_received": item.qty_received,
        "price_buy": item.price_buy,
        "remarks": item.remarks,
    }


@router.post("/submit_item")
def submit_item(
    id: str = Form(""),  # noqa: A002
    receiving_header_id: str = Form(""),
    material_id: str = Form(""),
    location_id: str = Form(""),
    qty_received: Decimal = Form(...),
    price_buy: Decimal = Form(...),
    remarks: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if qty_received <= 0:
        return {"error": "Quantity received must be greater than zero"}
    if price_buy < 0:
        return {"error": "Price cannot be negative"}

    if id:
        item = inventory_service.update_receiving_item(
            item_id=int(id),
            price_buy=price_buy,
            qty_received=qty_received,
            remarks=remarks,
        )
        if item is None:
            return {"error": "Receiving item not found"}
        return {"message": "Receiving item updated successfully"}

    if not receiving_header_id or not material_id or not location_id:
        return {"error": "receiving_header_id, material_id and location_id are required"}

    material = _material_repository.get_material_by_id(int(material_id))
    if material is not None and not material.is_active:
        return {"error": "Cannot receive: material is inactive"}

    inventory_service.create_receiving_item(
        receiving_header_id=int(receiving_header_id),
        material_id=int(material_id),
        location_id=int(location_id),
        price_buy=price_buy,
        qty_received=qty_received,
        remarks=remarks,
    )
    return {"message": "Receiving item added successfully"}


@router.post("/submit_bulk_item")
async def submit_bulk_item(
    request: Request,
    receiving_header_id: str = Form(...),
    user: UserModel = Depends(_require_access),
) -> dict:
    form = await request.form()
    rows = parse_bulk_rows(
        form, ["material_id", "location_id", "qty_received", "price_buy", "remarks"]
    )
    return inventory_service.create_receiving_items_bulk(int(receiving_header_id), rows)


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


@router.get("/call_supplier_id_select")
def call_supplier_id_select(user: UserModel = Depends(_require_access)) -> list:
    return [
        {"value": str(s.id), "label": f"{s.code} - {s.name}"}
        for s in _supplier_repository.get_all_suppliers()
    ]
