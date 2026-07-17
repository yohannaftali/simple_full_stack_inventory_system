"""Read-only purchase report (frontend module `purchase_report`).

Two independent aggregate tables over `receiving_items` joined to
`receiving_headers` (for `date`/`supplier_id`) and materials/suppliers —
"total purchase" = SUM(qty_received * price_buy):

- GET C_purchase_report/get_by_supplier?start_date-filter=&end_date-filter=
  &supplier_id-filter=&limit=&page=&offset= -> paginated
  {"supplier_code", "supplier_name", "total_qty", "total_purchase"}, one row
  per supplier that has ever been received from.
- GET C_purchase_report/get_by_material?start_date-filter=&end_date-filter=
  &material_id-filter=&limit=&page=&offset= -> paginated
  {"material_code", "material_name", "total_qty", "total_purchase"}, one row
  per material that has ever been received.

Each `{field}-filter` is independently optional (blank/absent = no bound on
that dimension); the date range is inclusive on both ends. Uses
`core/table_query.py::apply_field_filters` rather than hand-rolled
`if value: query.filter(...)` chains, per AGENTS.md's filter convention.

Gated by `require_module_access("purchase_report")`.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, Request

from core.table_export import export_response
from core.table_query import attach_pagination, parse_sort_fields
from models.user import UserModel
from repository.material_repository import MaterialRepository
from repository.purchase_report_repository import PurchaseReportRepository
from repository.supplier_repository import SupplierRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_purchase_report", tags=["purchase-report"])
_purchase_report_repository = PurchaseReportRepository()
_supplier_repository = SupplierRepository()
_material_repository = MaterialRepository()

_require_access = require_module_access("purchase_report")

_EXPORT_BY_SUPPLIER_COLUMNS = [
    ("supplier_code", "Supplier Code"),
    ("supplier_name", "Supplier"),
    ("total_qty", "Total Qty"),
    ("total_purchase", "Total Purchase"),
]
_EXPORT_BY_MATERIAL_COLUMNS = [
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("unit_name", "Unit"),
    ("total_qty", "Total Qty"),
    ("total_purchase", "Total Purchase"),
]


def _parse_date(value: str):
    """Blank or unparseable = no bound on that side, matching the leniency
    `apply_sort()`/`apply_field_filters()` already show elsewhere - an
    invalid date param just doesn't filter, it doesn't 422."""
    if not value:
        return None
    try:
        return date_type.fromisoformat(value)
    except ValueError:
        return None


@router.get("/get_by_supplier")
def get_by_supplier(
    request: Request,
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    supplier_id: str = Query("", alias="supplier_id-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _purchase_report_repository.list_by_supplier(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        supplier_id=int(supplier_id) if supplier_id else None,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination(rows, pagination)


@router.get("/export_by_supplier")
def export_by_supplier(
    request: Request,
    format: str = Query(...),  # noqa: A002
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    supplier_id: str = Query("", alias="supplier_id-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _purchase_report_repository.list_by_supplier(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        supplier_id=int(supplier_id) if supplier_id else None,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        rows, _EXPORT_BY_SUPPLIER_COLUMNS, format, "purchase_report_by_supplier"
    )


@router.get("/get_by_material")
def get_by_material(
    request: Request,
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    material_id: str = Query("", alias="material_id-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    sort_fields = parse_sort_fields(request.query_params)
    rows, pagination = _purchase_report_repository.list_by_material(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        material_id=int(material_id) if material_id else None,
        limit=limit,
        page=page,
        offset=offset,
        sort_fields=sort_fields,
    )
    return attach_pagination(rows, pagination)


@router.get("/export_by_material")
def export_by_material(
    request: Request,
    format: str = Query(...),  # noqa: A002
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    material_id: str = Query("", alias="material_id-filter"),
    user: UserModel = Depends(_require_access),
):
    sort_fields = parse_sort_fields(request.query_params)
    rows, _pagination = _purchase_report_repository.list_by_material(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        material_id=int(material_id) if material_id else None,
        limit=0,
        page=1,
        offset=0,
        sort_fields=sort_fields,
    )
    return export_response(
        rows, _EXPORT_BY_MATERIAL_COLUMNS, format, "purchase_report_by_material"
    )


@router.get("/call_supplier_id_select")
def call_supplier_id_select(user: UserModel = Depends(_require_access)) -> list:
    options = [{"value": "", "label": "All Suppliers"}]
    options += [
        {"value": str(s.id), "label": f"{s.code} - {s.name}"}
        for s in _supplier_repository.get_all_suppliers()
    ]
    return options


@router.get("/call_material_id_select")
def call_material_id_select(user: UserModel = Depends(_require_access)) -> list:
    options = [{"value": "", "label": "All Materials"}]
    options += [
        {"value": str(m.id), "label": f"{m.material_code} - {m.material_name}"}
        for m in _material_repository.get_all_materials()
    ]
    return options
