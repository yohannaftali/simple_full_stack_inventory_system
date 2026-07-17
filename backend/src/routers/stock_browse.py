"""Read-only current-stock listing (frontend module `stock_browse`).

- GET C_stock_browse/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> paginated list of {"material_code", "material_name", "location_code",
  "location_name", "qty", "average_price", "value"}, one row per
  (material, location) with qty > 0. `average_price`/`value` come from
  `inventory_values` (the material's MAP), not a per-location price.
- GET C_stock_browse/get_stock_by_material?material_id=<id> -> not
  paginated list of {"location_id", "location_code", "location_name",
  "unit_code", "unit_name", "qty", "average_price", "value"}, one row per
  location currently holding that material, qty > 0 only (issue #29's
  drill-down screen; row-click target from get_detail).
- GET C_stock_browse/get_material?material_id=<id> -> {"material_code",
  "material_name"} for the drill-down screen's heading - a material has no
  edit screen of its own to fetch this from (materials are read-only from
  this module's perspective; see master_material for actual CRUD).

Gated by `require_module_access("stock_browse")`.
"""

from fastapi import APIRouter, Depends, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.user import UserModel
from repository.material_repository import MaterialRepository
from repository.stock_repository import StockRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_stock_browse", tags=["stock-browse"])
_stock_repository = StockRepository()
_material_repository = MaterialRepository()

_require_access = require_module_access("stock_browse")

_EXPORT_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("location_code", "Location Code"),
    ("location_name", "Location"),
    ("qty", "Qty"),
    ("unit_name", "Unit"),
    ("average_price", "Avg Price"),
    ("value", "Value"),
]
_EXPORT_BY_MATERIAL_COLUMNS = [
    ("location_code", "Location Code"),
    ("location_name", "Location"),
    ("qty", "Qty"),
    ("unit_name", "Unit"),
    ("average_price", "Avg Price"),
    ("value", "Value"),
]


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
    rows, pagination = _stock_repository.list_stock_summary(
        keyword=keyword, limit=limit, page=page, offset=offset, sort_fields=sort_fields
    )
    return attach_pagination([dict(row) for row in rows], pagination)


@router.get("/export_detail")
def export_detail(
    request: Request,
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _stock_repository.list_stock_summary(
        keyword=keyword, limit=0, page=1, offset=0, sort_fields=sort_fields
    )
    return export_response([dict(row) for row in rows], _EXPORT_COLUMNS, format, "stock_browse")


@router.get("/get_stock_by_material")
def get_stock_by_material(
    request: Request, material_id: int, user: UserModel = Depends(_require_access)
) -> list:
    sort_fields = parse_sort_fields(request.query_params)
    return _stock_repository.list_stock_by_material(material_id, sort_fields=sort_fields)


@router.get("/export_stock_by_material")
def export_stock_by_material(
    material_id: int,
    format: str = Query(...),  # noqa: A002
    user: UserModel = Depends(_require_access),
):
    rows = _stock_repository.list_stock_by_material(material_id)
    return export_response(
        rows, _EXPORT_BY_MATERIAL_COLUMNS, format, f"stock_browse_material_{material_id}"
    )


@router.get("/get_material")
def get_material(material_id: int, user: UserModel = Depends(_require_access)) -> dict:
    material = _material_repository.get_material_by_id(material_id)
    if material is None:
        return {"error": "Material not found"}
    return {"material_code": material.material_code, "material_name": material.material_name}
