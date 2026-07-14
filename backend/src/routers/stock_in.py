"""Stock in (receiving) screens (frontend module `stock_in`).

Header list/get/submit follows the standard Table/Form contract (see
`module_admin.py`). Items are a separate sub-screen flow, not an embedded
Form table field (see AGENTS.md for why): the header's edit screen shows a
plain `Table` of its items (`GET C_stock_in/get_items?header_id=`), with a
"+" button navigating to an item_new screen that posts to
`POST C_stock_in/submit_item`; clicking a row navigates to an item_edit
screen (material/location are then read-only — see inventory_service).

- GET  C_stock_in/get_detail -> paginated receiving headers.
- GET  C_stock_in/get?id=<id> -> single header {id, date, description}.
- POST C_stock_in/submit (form: id, date, description) -> upsert header.
- GET  C_stock_in/get_items?header_id=<id>&table-keyword-filter=&limit=&page=&offset=
  -> paginated items for that header (keyword matches `remarks`), joined
  with material_code/name and location_code/name for display.
- GET  C_stock_in/get_item?id=<item_id> -> single item for the edit screen:
  {id, material_name, location_name, qty_received, price_buy, remarks}.
- POST C_stock_in/submit_item (form: id [blank=create], receiving_header_id
  [required on create], material_id, location_id [required on create],
  qty_received, price_buy, remarks) -> services.inventory_service create/update.
- GET  C_stock_in/call_material_id_select, call_location_id_select -> options
  for the item form's `select` fields.

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
from services import inventory_service
from services.auth_service import require_module_access
from services.bulk_service import BulkRowError, bulk_create, parse_bulk_rows

router = APIRouter(prefix="/C_stock_in", tags=["stock-in"])
_receiving_repository = ReceivingRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()

_require_access = require_module_access("stock_in")

_EXPORT_DETAIL_COLUMNS = [("date", "Date"), ("description", "Description")]
_EXPORT_ITEMS_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("location_code", "Location Code"),
    ("location_name", "Location"),
    ("qty_received", "Qty"),
    ("price_buy", "Price"),
    ("remarks", "Remarks"),
]


def _serialize_item(item) -> dict:
    material = _material_repository.get_material_by_id(item.material_id)
    location = _location_repository.get_location_by_id(item.location_id)
    return {
        "id": item.id,
        "material_code": material.material_code if material else "",
        "material_name": material.material_name if material else "",
        "location_code": location.code if location else "",
        "location_name": location.name if location else "",
        "qty_received": item.qty_received,
        "price_buy": item.price_buy,
        "remarks": item.remarks,
    }


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    rows, pagination = _receiving_repository.list_headers(
        keyword=keyword, limit=limit, page=page, offset=offset
    )
    result = [
        {"id": header.id, "date": header.date.isoformat(), "description": header.description}
        for header in rows
    ]
    return attach_pagination(result, pagination)


@router.get("/export_detail")
def export_detail(
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _receiving_repository.list_headers(keyword=keyword, limit=0, page=1, offset=0)
    result = [
        {"id": header.id, "date": header.date.isoformat(), "description": header.description}
        for header in rows
    ]
    return export_response(result, _EXPORT_DETAIL_COLUMNS, format, "stock_in")


@router.get("/export_items")
def export_items(
    header_id: int,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    items, _pagination = _receiving_repository.list_items_by_header(
        header_id, keyword=keyword, limit=0, page=1, offset=0
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
    return {"id": header.id, "date": header.date.isoformat(), "description": header.description}


@router.post("/submit")
def submit(
    id: str = Form(""),  # noqa: A002
    date: date_type = Form(...),
    description: str = Form(""),
    user: UserModel = Depends(_require_access),
) -> dict:
    if id:
        updated = _receiving_repository.update_header(int(id), date=date, description=description)
        if not updated:
            return {"error": "Receiving header not found"}
        return {"message": "Receiving header updated successfully"}

    _receiving_repository.create_header(date=date, description=description)
    return {"message": "Receiving header created successfully"}


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
        return ReceivingHeaderModel(
            date=date_value, description=str(row.get("description", "")).strip()
        )

    return bulk_create(rows, build)


@router.get("/get_items")
def get_items(
    header_id: int,
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    items, pagination = _receiving_repository.list_items_by_header(
        header_id, keyword=keyword, limit=limit, page=page, offset=offset
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

    inventory_service.create_receiving_item(
        receiving_header_id=int(receiving_header_id),
        material_id=int(material_id),
        location_id=int(location_id),
        price_buy=price_buy,
        qty_received=qty_received,
        remarks=remarks,
    )
    return {"message": "Receiving item added successfully"}


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
