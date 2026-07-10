"""Stock out repository — header CRUD and read-only item access.

Item *writes* (create only — stock out items are immutable once created, see
`services.inventory_service`) go through the service layer, since each one
must also deduct FIFO from `StockModel` lots and decrement `InventoryValueModel`
atomically.
"""

from typing import Optional

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.stock_out_header import StockOutHeaderModel
from models.stock_out_item import StockOutItemModel


class StockOutRepository:
    """Repository class for stock out header data access, plus item reads."""

    def get_header_by_id(self, header_id: int) -> Optional[StockOutHeaderModel]:
        with SessionLocal() as session:
            return (
                session.query(StockOutHeaderModel)
                .filter(StockOutHeaderModel.id == header_id)
                .first()
            )

    def list_headers(
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[StockOutHeaderModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(StockOutHeaderModel)
            query = apply_keyword_filter(query, [StockOutHeaderModel.description], keyword)
            query = query.order_by(
                StockOutHeaderModel.date.desc(), StockOutHeaderModel.id.desc()
            )
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_header(
        self, date, description: str, department_id: Optional[int] = None
    ) -> StockOutHeaderModel:
        with SessionLocal() as session:
            header = StockOutHeaderModel(
                date=date, description=description, department_id=department_id
            )
            session.add(header)
            session.commit()
            session.refresh(header)
            return header

    def update_header(
        self, header_id: int, date, description: str, department_id: Optional[int] = None
    ) -> bool:
        with SessionLocal() as session:
            header = (
                session.query(StockOutHeaderModel)
                .filter(StockOutHeaderModel.id == header_id)
                .first()
            )
            if header is None:
                return False

            header.date = date
            header.description = description
            header.department_id = department_id
            session.commit()
            return True

    def list_items_by_header(self, header_id: int) -> list[StockOutItemModel]:
        with SessionLocal() as session:
            return (
                session.query(StockOutItemModel)
                .filter(StockOutItemModel.stock_out_header_id == header_id)
                .order_by(StockOutItemModel.id)
                .all()
            )
