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
- GET  C_stock_in/get_items?header_id=<id> -> that header's items, joined
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

import math
from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query

from models.user import UserModel
from repository.location_repository import LocationRepository
from repository.material_repository import MaterialRepository
from repository.receiving_repository import ReceivingRepository
from services import inventory_service
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_stock_in", tags=["stock-in"])
_receiving_repository = ReceivingRepository()
_material_repository = MaterialRepository()
_location_repository = LocationRepository()

_require_access = require_module_access("stock_in")


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _receiving_repository.list_headers(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for header in rows:
        result.append(
            {
                "id": header.id,
                "date": header.date.isoformat(),
                "description": header.description,
                "db_total_page": total_pages,
                "db_num_rows": total,
            }
        )
    return result


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


@router.get("/get_items")
def get_items(header_id: int, user: UserModel = Depends(_require_access)) -> list:
    items = _receiving_repository.list_items_by_header(header_id)
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
                "qty_received": item.qty_received,
                "price_buy": item.price_buy,
                "remarks": item.remarks,
                "db_total_page": 1,
                "db_num_rows": len(items),
            }
        )
    return result


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
