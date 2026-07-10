"""Stock repository — read-only browse access (aggregated by material+location).

Lot-level writes (upsert on receive, FIFO deduction on issue) are owned by
`services.inventory_service`.
"""

from sqlalchemy import func

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.inventory_value import InventoryValueModel
from models.location import LocationModel
from models.material import MaterialModel
from models.stock import StockModel


class StockRepository:
    """Repository class for browsing current stock (material x location totals)."""

    def list_stock_summary(
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[dict], Pagination]:
        """Current on-hand qty per (material, location), qty > 0 only."""
        with SessionLocal() as session:
            query = (
                session.query(
                    MaterialModel.id.label("material_id"),
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                    LocationModel.id.label("location_id"),
                    LocationModel.code.label("location_code"),
                    LocationModel.name.label("location_name"),
                    func.sum(StockModel.qty).label("qty"),
                )
                .join(MaterialModel, MaterialModel.id == StockModel.material_id)
                .join(LocationModel, LocationModel.id == StockModel.location_id)
                .group_by(MaterialModel.id, LocationModel.id)
                .having(func.sum(StockModel.qty) > 0)
            )
            query = apply_keyword_filter(
                query,
                [
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                    LocationModel.code,
                    LocationModel.name,
                ],
                keyword,
            )
            query = query.order_by(MaterialModel.material_code, LocationModel.code)
            rows, pagination = paginate(query, limit=limit, page=page, offset=offset)

            material_ids = {row.material_id for row in rows}
            prices: dict[int, tuple] = {}
            if material_ids:
                for inv in (
                    session.query(InventoryValueModel)
                    .filter(InventoryValueModel.material_id.in_(material_ids))
                    .all()
                ):
                    prices[inv.material_id] = inv.average_price

            summary = []
            for row in rows:
                average_price = prices.get(row.material_id, 0)
                summary.append(
                    {
                        "material_id": row.material_id,
                        "material_code": row.material_code,
                        "material_name": row.material_name,
                        "location_id": row.location_id,
                        "location_code": row.location_code,
                        "location_name": row.location_name,
                        "qty": row.qty,
                        "average_price": average_price,
                        "value": row.qty * average_price,
                    }
                )
            return summary, pagination
