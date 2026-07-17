"""Stock repository — read-only browse access (aggregated by material+location).

Lot-level writes (upsert on receive, FIFO deduction on issue) are owned by
`services.inventory_service`.
"""

from sqlalchemy import func

from core.table_query import Pagination, apply_keyword_filter, apply_sort, paginate
from models.base import SessionLocal
from models.inventory_value import InventoryValueModel
from models.location import LocationModel
from models.material import MaterialModel
from models.stock import StockModel
from models.unit_of_material import UnitOfMaterialModel


class StockRepository:
    """Repository class for browsing current stock (material x location totals)."""

    def list_stock_summary(
        self,
        keyword: str = "",
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[dict], Pagination]:
        """Current on-hand qty per (material, location), qty > 0 only."""
        with SessionLocal() as session:
            qty_expr = func.sum(StockModel.qty)
            # average_price/value used to be resolved in a *separate*
            # post-pagination lookup (one query per page of results, keyed
            # by material_id) - that made them display-only, with no SQL
            # expression to sort by. Outer-joining InventoryValueModel
            # directly (one row per material, so it's safe to add to
            # group_by alongside material's own id) turns both into real,
            # sortable/orderable expressions in the same query.
            average_price_expr = func.coalesce(InventoryValueModel.average_price, 0)
            value_expr = qty_expr * average_price_expr
            query = (
                session.query(
                    MaterialModel.id.label("material_id"),
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                    LocationModel.id.label("location_id"),
                    LocationModel.code.label("location_code"),
                    LocationModel.name.label("location_name"),
                    UnitOfMaterialModel.code.label("unit_code"),
                    UnitOfMaterialModel.name.label("unit_name"),
                    qty_expr.label("qty"),
                    average_price_expr.label("average_price"),
                    value_expr.label("value"),
                )
                .join(MaterialModel, MaterialModel.id == StockModel.material_id)
                .join(LocationModel, LocationModel.id == StockModel.location_id)
                .join(UnitOfMaterialModel, UnitOfMaterialModel.id == MaterialModel.unit_id)
                .outerjoin(
                    InventoryValueModel, InventoryValueModel.material_id == MaterialModel.id
                )
                .group_by(
                    MaterialModel.id, LocationModel.id, InventoryValueModel.average_price
                )
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
            column_map = {
                "material_code": MaterialModel.material_code,
                "material_name": MaterialModel.material_name,
                "location_code": LocationModel.code,
                "location_name": LocationModel.name,
                "unit_name": UnitOfMaterialModel.name,
                "qty": qty_expr,
                "average_price": average_price_expr,
                "value": value_expr,
            }
            if sort_fields:
                query = apply_sort(query, sort_fields, column_map)
            else:
                query = query.order_by(MaterialModel.material_code, LocationModel.code)
            rows, pagination = paginate(query, limit=limit, page=page, offset=offset)

            summary = [
                {
                    "material_id": row.material_id,
                    "material_code": row.material_code,
                    "material_name": row.material_name,
                    "location_id": row.location_id,
                    "location_code": row.location_code,
                    "location_name": row.location_name,
                    "unit_code": row.unit_code,
                    "unit_name": row.unit_name,
                    "qty": row.qty,
                    "average_price": row.average_price,
                    "value": row.value,
                }
                for row in rows
            ]
            return summary, pagination

    def list_stock_by_material(self, material_id: int) -> list[dict]:
        """Current on-hand qty per location for one material, qty > 0 only.

        Not paginated - feeds the stock-out item form's per-location qty
        table, which is naturally small (one row per location actually
        holding this material).
        """
        with SessionLocal() as session:
            rows = (
                session.query(
                    LocationModel.id.label("location_id"),
                    LocationModel.code.label("location_code"),
                    LocationModel.name.label("location_name"),
                    UnitOfMaterialModel.code.label("unit_code"),
                    UnitOfMaterialModel.name.label("unit_name"),
                    func.sum(StockModel.qty).label("qty"),
                )
                .join(LocationModel, LocationModel.id == StockModel.location_id)
                .join(MaterialModel, MaterialModel.id == StockModel.material_id)
                .join(UnitOfMaterialModel, UnitOfMaterialModel.id == MaterialModel.unit_id)
                .filter(StockModel.material_id == material_id)
                .group_by(LocationModel.id)
                .having(func.sum(StockModel.qty) > 0)
                .order_by(LocationModel.code)
                .all()
            )
            return [
                {
                    "location_id": row.location_id,
                    "location_code": row.location_code,
                    "location_name": row.location_name,
                    "unit_code": row.unit_code,
                    "unit_name": row.unit_name,
                    "qty": row.qty,
                }
                for row in rows
            ]
