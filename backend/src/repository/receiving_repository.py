"""Receiving repository — header CRUD and read-only item access.

Item *writes* (create/update) go through `services.inventory_service`, since
each one must also upsert a `StockModel` lot and recompute `InventoryValueModel`
atomically — not something a plain single-table repository method should do.
"""

from typing import Optional

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.receiving_header import ReceivingHeaderModel
from models.receiving_item import ReceivingItemModel


class ReceivingRepository:
    """Repository class for receiving header data access, plus item reads."""

    def get_header_by_id(self, header_id: int) -> Optional[ReceivingHeaderModel]:
        with SessionLocal() as session:
            return (
                session.query(ReceivingHeaderModel)
                .filter(ReceivingHeaderModel.id == header_id)
                .first()
            )

    def list_headers(
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[ReceivingHeaderModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(ReceivingHeaderModel)
            query = apply_keyword_filter(query, [ReceivingHeaderModel.description], keyword)
            query = query.order_by(
                ReceivingHeaderModel.date.desc(), ReceivingHeaderModel.id.desc()
            )
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_header(self, date, description: str) -> ReceivingHeaderModel:
        with SessionLocal() as session:
            header = ReceivingHeaderModel(date=date, description=description)
            session.add(header)
            session.commit()
            session.refresh(header)
            return header

    def update_header(self, header_id: int, date, description: str) -> bool:
        with SessionLocal() as session:
            header = (
                session.query(ReceivingHeaderModel)
                .filter(ReceivingHeaderModel.id == header_id)
                .first()
            )
            if header is None:
                return False

            header.date = date
            header.description = description
            session.commit()
            return True

    def get_item_by_id(self, item_id: int) -> Optional[ReceivingItemModel]:
        with SessionLocal() as session:
            return (
                session.query(ReceivingItemModel)
                .filter(ReceivingItemModel.id == item_id)
                .first()
            )

    def list_items_by_header(
        self,
        header_id: int,
        keyword: str = "",
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
    ) -> tuple[list[ReceivingItemModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(ReceivingItemModel).filter(
                ReceivingItemModel.receiving_header_id == header_id
            )
            query = apply_keyword_filter(query, [ReceivingItemModel.remarks], keyword)
            query = query.order_by(ReceivingItemModel.id)
            return paginate(query, limit=limit, page=page, offset=offset)
