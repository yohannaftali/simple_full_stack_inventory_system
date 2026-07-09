"""Read-only department usage/cost report (frontend module `usage_report`).

- GET C_usage_report/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> paginated list of {"department_code", "department_name",
  "material_code", "material_name", "total_qty_out", "total_cost"}, one row
  per (department, material) pair that has ever been issued via Stock Out —
  answers "which department consumes how much of which material, and at
  what total cost". Relies on every `stock_out_headers` row declaring a
  `department_id` (enforced by `routers/stock_out.py::submit`).

Gated by `require_module_access("usage_report")`.
"""

import math

from fastapi import APIRouter, Depends, Query

from models.user import UserModel
from repository.usage_report_repository import UsageReportRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_usage_report", tags=["usage-report"])
_usage_report_repository = UsageReportRepository()

_require_access = require_module_access("usage_report")


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _usage_report_repository.list_usage_by_department(
        keyword=keyword, limit=limit, offset=effective_offset
    )
    total_pages = max(math.ceil(total / limit), 1) if limit else 1

    result = []
    for row in rows:
        entry = dict(row)
        entry["db_total_page"] = total_pages
        entry["db_num_rows"] = total
        result.append(entry)
    return result
