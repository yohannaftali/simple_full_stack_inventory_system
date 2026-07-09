"""Usage report repository — read-only, aggregates stock-out consumption by
department + material (total qty issued, total cost) for reporting.

Mirrors `stock_repository.py`'s shape: a cross-table read-only aggregate
query, kept in its own repository rather than bolted onto
`stock_out_repository.py` (which owns header CRUD + item reads, not
aggregate reporting).
"""

from sqlalchemy import func, or_

from models.base import SessionLocal
from models.department import DepartmentModel
from models.material import MaterialModel
from models.stock_out_header import StockOutHeaderModel
from models.stock_out_item import StockOutItemModel


class UsageReportRepository:
    """Repository class for the department x material usage/cost report."""

    def list_usage_by_department(
        self, keyword: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[dict], int]:
        """Total qty issued + total cost per (department, material), summed
        across every stock-out item ever issued under that department."""
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
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    or_(
                        DepartmentModel.code.like(like),
                        DepartmentModel.name.like(like),
                        MaterialModel.material_code.like(like),
                        MaterialModel.material_name.like(like),
                    )
                )

            total = query.count()
            rows = (
                query.order_by(DepartmentModel.code, MaterialModel.material_code)
                .offset(offset)
                .limit(limit)
                .all()
            )

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
            ], total
