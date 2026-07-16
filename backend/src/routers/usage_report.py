"""Read-only department usage/cost report (frontend module `usage_report`).

- GET C_usage_report/get_detail?table-keyword-filter=&start_date-filter=
  &end_date-filter=&limit=&page=&offset= -> paginated list of
  {"department_code", "department_name", "material_code", "material_name",
  "total_qty_out", "total_cost"}, one row per (department, material) pair
  that has ever been issued via Stock Out (within the date range, if given)
  — answers "which department consumes how much of which material, and at
  what total cost". Relies on every `stock_out_headers` row declaring a
  `department_id` (enforced by `routers/stock_out.py::submit`).
  `start_date-filter`/`end_date-filter` are the same independently-optional,
  inclusive `{field}-filter` convention issue #8 introduced for
  `purchase_report` (see `core/table_query.py::apply_field_filters`) —
  blank/absent on either bound means no filtering on that side.

Gated by `require_module_access("usage_report")`.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query

from core.table_export import export_response
from core.table_query import attach_pagination
from models.user import UserModel
from repository.usage_report_repository import UsageReportRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_usage_report", tags=["usage-report"])
_usage_report_repository = UsageReportRepository()

_require_access = require_module_access("usage_report")

_EXPORT_COLUMNS = [
    ("department_code", "Dept Code"),
    ("department_name", "Department"),
    ("material_code", "Material Code"),
    ("material_name", "Material"),
    ("unit_name", "Unit"),
    ("total_qty_out", "Total Qty"),
    ("total_cost", "Total Cost"),
]


def _parse_date(value: str):
    """Blank or unparseable = no bound on that side - same leniency as
    `purchase_report.py`'s `_parse_date`."""
    if not value:
        return None
    try:
        return date_type.fromisoformat(value)
    except ValueError:
        return None


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    rows, pagination = _usage_report_repository.list_usage_by_department(
        keyword=keyword,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        limit=limit,
        page=page,
        offset=offset,
    )
    return attach_pagination([dict(row) for row in rows], pagination)


@router.get("/export_detail")
def export_detail(
    format: str = Query(...),  # noqa: A002
    keyword: str = Query("", alias="table-keyword-filter"),
    start_date: str = Query("", alias="start_date-filter"),
    end_date: str = Query("", alias="end_date-filter"),
    user: UserModel = Depends(_require_access),
):
    rows, _pagination = _usage_report_repository.list_usage_by_department(
        keyword=keyword,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        limit=0,
        page=1,
        offset=0,
    )
    return export_response([dict(row) for row in rows], _EXPORT_COLUMNS, format, "usage_report")
