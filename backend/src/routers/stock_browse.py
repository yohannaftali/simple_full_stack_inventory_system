"""Read-only current-stock listing (frontend module `stock_browse`).

- GET C_stock_browse/get_detail?table-keyword-filter=&limit=&page=&offset=
  -> paginated list of {"material_code", "material_name", "location_code",
  "location_name", "qty", "average_price", "value"}, one row per
  (material, location) with qty > 0. `average_price`/`value` come from
  `inventory_values` (the material's MAP), not a per-location price.

Gated by `require_module_access("stock_browse")`.
"""

import math

from fastapi import APIRouter, Depends, Query

from models.user import UserModel
from repository.stock_repository import StockRepository
from services.auth_service import require_module_access

router = APIRouter(prefix="/C_stock_browse", tags=["stock-browse"])
_stock_repository = StockRepository()

_require_access = require_module_access("stock_browse")


@router.get("/get_detail")
def get_detail(
    keyword: str = Query("", alias="table-keyword-filter"),
    limit: int = Query(20),
    page: int = Query(1),
    offset: int = Query(0),
    user: UserModel = Depends(_require_access),
) -> list:
    effective_offset = offset if offset else max(page - 1, 0) * limit
    rows, total = _stock_repository.list_stock_summary(
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
