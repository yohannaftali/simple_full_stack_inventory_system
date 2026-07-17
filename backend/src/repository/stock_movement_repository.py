"""Stock movement repository - header CRUD and read-only item access.

Item *writes* (create only - stock movement items are immutable once
created, same rationale as stock out items, see `services.inventory_service`)
go through the service layer, since each one must also deduct FIFO from the
origin location's `StockModel` lots and create a new lot at the destination
atomically.
"""

from typing import Optional

from sqlalchemy.orm import aliased

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.location import LocationModel
from models.material import MaterialModel
from models.stock_movement_header import StockMovementHeaderModel
from models.stock_movement_item import StockMovementItemModel

_HEADER_FILTER_COLUMN_MAP = {
    "description": StockMovementHeaderModel.description,
}
# date isn't a per-column *filter* (no {field}-filter UI for it, same
# convention as receiving_repository/stock_out_repository), but it's a real
# column worth sorting a transaction list by.
_HEADER_SORT_COLUMN_MAP = {
    **_HEADER_FILTER_COLUMN_MAP,
    "date": StockMovementHeaderModel.date,
}

_OriginLocation = aliased(LocationModel, name="origin_location")
_DestinationLocation = aliased(LocationModel, name="destination_location")

_ITEM_FILTER_COLUMN_MAP = {
    "remarks": StockMovementItemModel.remarks,
    "plan_qty": StockMovementItemModel.plan_qty,
    "movement_qty": StockMovementItemModel.movement_qty,
    # Join-derived display columns (material/location labels are looked up
    # per-row by the router's own _serialize_item(), not returned by this
    # query) - outer-joined below purely so these can be filtered/sorted,
    # same pattern as stock_out_repository.py's own item filter map.
    "material_code": MaterialModel.material_code,
    "material_name": MaterialModel.material_name,
    "origin_location_code": _OriginLocation.code,
    "origin_location_name": _OriginLocation.name,
    "destination_location_code": _DestinationLocation.code,
    "destination_location_name": _DestinationLocation.name,
}
_ITEM_FILTER_NUMERIC_FIELDS = {"plan_qty", "movement_qty"}
# created_at isn't a per-column *filter* (no {field}-filter UI for it), but
# it's a real column worth sorting the item table by ("Datetime Actual"),
# same sort-only convention as receiving_repository/stock_out_repository's
# header "date" entry.
_ITEM_SORT_COLUMN_MAP = {
    **_ITEM_FILTER_COLUMN_MAP,
    "created_at": StockMovementItemModel.created_at,
}


class StockMovementRepository:
    """Repository class for stock movement header data access, plus item reads."""

    def get_header_by_id(self, header_id: int) -> Optional[StockMovementHeaderModel]:
        with SessionLocal() as session:
            return (
                session.query(StockMovementHeaderModel)
                .filter(StockMovementHeaderModel.id == header_id)
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
    ) -> tuple[list[StockMovementHeaderModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(StockMovementHeaderModel)
            query = apply_keyword_filter(
                query, [StockMovementHeaderModel.description], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _HEADER_FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _HEADER_SORT_COLUMN_MAP)
            else:
                query = query.order_by(
                    StockMovementHeaderModel.date.desc(), StockMovementHeaderModel.id.desc()
                )
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def create_header(
        self, date, description: str, created_by: Optional[int] = None
    ) -> StockMovementHeaderModel:
        with SessionLocal() as session:
            header = StockMovementHeaderModel(
                date=date,
                description=description,
                created_by=created_by,
                updated_by=created_by,
            )
            session.add(header)
            session.commit()
            session.refresh(header)
            return header

    def update_header(
        self, header_id: int, date, description: str, updated_by: Optional[int] = None
    ) -> bool:
        with SessionLocal() as session:
            header = (
                session.query(StockMovementHeaderModel)
                .filter(StockMovementHeaderModel.id == header_id)
                .first()
            )
            if header is None:
                return False

            header.date = date
            header.description = description
            header.updated_by = updated_by
            session.commit()
            return True

    def list_items_by_header(
        self,
        header_id: int,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[StockMovementItemModel], Pagination]:
        with SessionLocal() as session:
            query = (
                session.query(StockMovementItemModel)
                .outerjoin(
                    MaterialModel, MaterialModel.id == StockMovementItemModel.material_id
                )
                .outerjoin(
                    _OriginLocation,
                    _OriginLocation.id == StockMovementItemModel.origin_location_id,
                )
                .outerjoin(
                    _DestinationLocation,
                    _DestinationLocation.id == StockMovementItemModel.destination_location_id,
                )
                .filter(StockMovementItemModel.stock_movement_header_id == header_id)
            )
            query = apply_keyword_filter(query, [StockMovementItemModel.remarks], keyword)
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _ITEM_FILTER_COLUMN_MAP, _ITEM_FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _ITEM_SORT_COLUMN_MAP)
            else:
                query = query.order_by(StockMovementItemModel.id)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)
