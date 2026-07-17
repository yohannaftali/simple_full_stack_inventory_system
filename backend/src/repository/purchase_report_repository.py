"""Purchase report repository — read-only, aggregates receiving (stock in)
purchases by supplier and by material (total qty received, total purchase
value) for reporting.

Mirrors `usage_report_repository.py`'s shape: a cross-table read-only
aggregate query, kept in its own repository rather than bolted onto
`receiving_repository.py` (which owns header CRUD + item reads, not
aggregate reporting). "Total purchase" = SUM(qty_received * price_buy),
today's captured cost at time of receipt — same "reflects the transaction,
not any later price change" semantics as `usage_report`'s `total_cost`.

Both tables inner-join their grouping dimension (Supplier/Material), so a
receiving header with no `supplier_id` recorded is simply excluded from
the by-supplier breakdown (nothing to group it under) — same as
`stock_repository.py`'s `having(qty > 0)` silently dropping zero-stock
rows, not an error case.
"""

from datetime import date as date_type
from typing import Optional

from sqlalchemy import func

from core.table_query import Pagination, apply_field_filters, apply_sort, paginate
from models.base import SessionLocal
from models.material import MaterialModel
from models.receiving_header import ReceivingHeaderModel
from models.receiving_item import ReceivingItemModel
from models.supplier import SupplierModel
from models.unit_of_material import UnitOfMaterialModel


class PurchaseReportRepository:
    """Repository class for the by-supplier / by-material purchase report."""

    def list_by_supplier(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        supplier_id: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[dict], Pagination]:
        with SessionLocal() as session:
            total_qty_expr = func.sum(ReceivingItemModel.qty_received)
            total_purchase_expr = func.sum(
                ReceivingItemModel.qty_received * ReceivingItemModel.price_buy
            )
            query = (
                session.query(
                    SupplierModel.id.label("supplier_id"),
                    SupplierModel.code.label("supplier_code"),
                    SupplierModel.name.label("supplier_name"),
                    total_qty_expr.label("total_qty"),
                    total_purchase_expr.label("total_purchase"),
                )
                .join(
                    ReceivingHeaderModel,
                    ReceivingHeaderModel.id == ReceivingItemModel.receiving_header_id,
                )
                .join(SupplierModel, SupplierModel.id == ReceivingHeaderModel.supplier_id)
                .group_by(SupplierModel.id)
            )
            query = apply_field_filters(
                query,
                [
                    (ReceivingHeaderModel.date, ">=", start_date),
                    (ReceivingHeaderModel.date, "<=", end_date),
                    (SupplierModel.id, "==", supplier_id),
                ],
            )
            column_map = {
                "supplier_code": SupplierModel.code,
                "supplier_name": SupplierModel.name,
                "total_qty": total_qty_expr,
                "total_purchase": total_purchase_expr,
            }
            if sort_fields:
                query = apply_sort(query, sort_fields, column_map)
            else:
                query = query.order_by(SupplierModel.code)
            rows, pagination = paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

            return [
                {
                    "supplier_id": row.supplier_id,
                    "supplier_code": row.supplier_code,
                    "supplier_name": row.supplier_name,
                    "total_qty": row.total_qty,
                    "total_purchase": row.total_purchase,
                }
                for row in rows
            ], pagination

    def list_by_material(
        self,
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        material_id: Optional[int] = None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[dict], Pagination]:
        with SessionLocal() as session:
            total_qty_expr = func.sum(ReceivingItemModel.qty_received)
            total_purchase_expr = func.sum(
                ReceivingItemModel.qty_received * ReceivingItemModel.price_buy
            )
            query = (
                session.query(
                    MaterialModel.id.label("material_id"),
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                    UnitOfMaterialModel.code.label("unit_code"),
                    UnitOfMaterialModel.name.label("unit_name"),
                    total_qty_expr.label("total_qty"),
                    total_purchase_expr.label("total_purchase"),
                )
                .join(
                    ReceivingHeaderModel,
                    ReceivingHeaderModel.id == ReceivingItemModel.receiving_header_id,
                )
                .join(MaterialModel, MaterialModel.id == ReceivingItemModel.material_id)
                .join(UnitOfMaterialModel, UnitOfMaterialModel.id == MaterialModel.unit_id)
                .group_by(MaterialModel.id)
            )
            query = apply_field_filters(
                query,
                [
                    (ReceivingHeaderModel.date, ">=", start_date),
                    (ReceivingHeaderModel.date, "<=", end_date),
                    (MaterialModel.id, "==", material_id),
                ],
            )
            column_map = {
                "material_code": MaterialModel.material_code,
                "material_name": MaterialModel.material_name,
                "unit_name": UnitOfMaterialModel.name,
                "total_qty": total_qty_expr,
                "total_purchase": total_purchase_expr,
            }
            if sort_fields:
                query = apply_sort(query, sort_fields, column_map)
            else:
                query = query.order_by(MaterialModel.material_code)
            rows, pagination = paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

            return [
                {
                    "material_id": row.material_id,
                    "material_code": row.material_code,
                    "material_name": row.material_name,
                    "unit_code": row.unit_code,
                    "unit_name": row.unit_name,
                    "total_qty": row.total_qty,
                    "total_purchase": row.total_purchase,
                }
                for row in rows
            ], pagination
