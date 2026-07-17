"""Receiving repository — header CRUD and read-only item access.

Item *writes* (create/update) go through `services.inventory_service`, since
each one must also upsert a `StockModel` lot and recompute `InventoryValueModel`
atomically — not something a plain single-table repository method should do.
"""

from typing import Optional

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.receiving_header import ReceivingHeaderModel
from models.receiving_item import ReceivingItemModel
from models.supplier import SupplierModel

_HEADER_FILTER_COLUMN_MAP = {
    "description": ReceivingHeaderModel.description,
    "supplier_name": SupplierModel.name,
}
# date isn't a per-column *filter* (no {field}-filter UI for it - the
# purchase/usage reports already own date-range filtering), but it's a real
# column worth sorting a transaction list by, so it's sort-only, kept out of
# _HEADER_FILTER_COLUMN_MAP.
_HEADER_SORT_COLUMN_MAP = {**_HEADER_FILTER_COLUMN_MAP, "date": ReceivingHeaderModel.date}
_ITEM_FILTER_COLUMN_MAP = {
    "remarks": ReceivingItemModel.remarks,
    "qty_received": ReceivingItemModel.qty_received,
    "price_buy": ReceivingItemModel.price_buy,
}
_ITEM_FILTER_NUMERIC_FIELDS = {"qty_received", "price_buy"}


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
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ReceivingHeaderModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(ReceivingHeaderModel).outerjoin(
                SupplierModel, SupplierModel.id == ReceivingHeaderModel.supplier_id
            )
            query = apply_keyword_filter(
                query,
                [ReceivingHeaderModel.description, SupplierModel.code, SupplierModel.name],
                keyword,
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _HEADER_FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _HEADER_SORT_COLUMN_MAP)
            else:
                query = query.order_by(
                    ReceivingHeaderModel.date.desc(), ReceivingHeaderModel.id.desc()
                )
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_header(
        self, date, description: str, supplier_id: Optional[int] = None
    ) -> ReceivingHeaderModel:
        with SessionLocal() as session:
            header = ReceivingHeaderModel(
                date=date, description=description, supplier_id=supplier_id
            )
            session.add(header)
            session.commit()
            session.refresh(header)
            return header

    def update_header(
        self, header_id: int, date, description: str, supplier_id: Optional[int] = None
    ) -> bool:
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
            header.supplier_id = supplier_id
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
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ReceivingItemModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(ReceivingItemModel).filter(
                ReceivingItemModel.receiving_header_id == header_id
            )
            query = apply_keyword_filter(query, [ReceivingItemModel.remarks], keyword)
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _ITEM_FILTER_COLUMN_MAP, _ITEM_FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _ITEM_FILTER_COLUMN_MAP)
            else:
                query = query.order_by(ReceivingItemModel.id)
            return paginate(query, limit=limit, page=page, offset=offset)
