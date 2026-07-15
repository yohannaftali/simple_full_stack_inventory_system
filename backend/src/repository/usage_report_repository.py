"""Usage report repository — read-only, aggregates stock-out consumption by
department + material (total qty issued, total cost) for reporting.

Mirrors `stock_repository.py`'s shape: a cross-table read-only aggregate
query, kept in its own repository rather than bolted onto
`stock_out_repository.py` (which owns header CRUD + item reads, not
aggregate reporting).
"""

from datetime import date as date_type
from typing import Optional

from sqlalchemy import func

from core.table_query import Pagination, apply_field_filters, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.department import DepartmentModel
from models.material import MaterialModel
from models.stock_out_header import StockOutHeaderModel
from models.stock_out_item import StockOutItemModel


class UsageReportRepository:
    """Repository class for the department x material usage/cost report."""

    def list_usage_by_department(
        self,
        keyword: str = "",
        start_date: Optional[date_type] = None,
        end_date: Optional[date_type] = None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
    ) -> tuple[list[dict], Pagination]:
        """Total qty issued + total cost per (department, material), summed
        across every stock-out item ever issued under that department,
        optionally narrowed to an inclusive `stock_out_headers.date` range
        (each bound independently optional - see issue #9)."""
        with SessionLocal() as session:
            query = (
                session.query(
                    DepartmentModel.id.label("department_id"),
                    DepartmentModel.code.label("department_code"),
                    DepartmentModel.name.label("department_name"),
                    MaterialModel.id.label("material_id"),
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                    func.sum(StockOutItemModel.qty_out).label("total_qty_out"),
                    func.sum(StockOutItemModel.total_value).label("total_cost"),
                )
                .join(
                    StockOutHeaderModel,
                    StockOutHeaderModel.id == StockOutItemModel.stock_out_header_id,
                )
                .join(DepartmentModel, DepartmentModel.id == StockOutHeaderModel.department_id)
                .join(MaterialModel, MaterialModel.id == StockOutItemModel.material_id)
                .group_by(DepartmentModel.id, MaterialModel.id)
            )
            query = apply_keyword_filter(
                query,
                [
                    DepartmentModel.code,
                    DepartmentModel.name,
                    MaterialModel.material_code,
                    MaterialModel.material_name,
                ],
                keyword,
            )
            query = apply_field_filters(
                query,
                [
                    (StockOutHeaderModel.date, ">=", start_date),
                    (StockOutHeaderModel.date, "<=", end_date),
                ],
            )
            query = query.order_by(DepartmentModel.code, MaterialModel.material_code)
            rows, pagination = paginate(query, limit=limit, page=page, offset=offset)

            return [
                {
                    "department_id": row.department_id,
                    "department_code": row.department_code,
                    "department_name": row.department_name,
                    "material_id": row.material_id,
                    "material_code": row.material_code,
                    "material_name": row.material_name,
                    "total_qty_out": row.total_qty_out,
                    "total_cost": row.total_cost,
                }
                for row in rows
            ], pagination
