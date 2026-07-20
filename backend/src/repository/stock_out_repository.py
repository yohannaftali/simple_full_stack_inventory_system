"""Stock out repository — header CRUD and read-only item access.

Item *writes* (create only — stock out items are immutable once created, see
`services.inventory_service`) go through the service layer, since each one
must also deduct FIFO from `StockModel` lots and decrement `InventoryValueModel`
atomically.
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
from models.department import DepartmentModel
from models.location import LocationModel
from models.material import MaterialModel
from models.stock_out_header import StockOutHeaderModel
from models.stock_out_item import StockOutItemModel
from models.unit_of_material import UnitOfMaterialModel

_HEADER_FILTER_COLUMN_MAP = {
    "description": StockOutHeaderModel.description,
    "department_name": DepartmentModel.name,
}
# date isn't a per-column *filter* (no {field}-filter UI for it - the usage
# report already owns date-range filtering), but it's a real column worth
# sorting a transaction list by, so it's sort-only, kept out of
# _HEADER_FILTER_COLUMN_MAP.
_HEADER_SORT_COLUMN_MAP = {**_HEADER_FILTER_COLUMN_MAP, "date": StockOutHeaderModel.date}
_ITEM_FILTER_COLUMN_MAP = {
    "remarks": StockOutItemModel.remarks,
    "qty_plan": StockOutItemModel.qty_plan,
    "qty_out": StockOutItemModel.qty_out,
    "price": StockOutItemModel.price,
    "total_value": StockOutItemModel.total_value,
    # Join-derived display columns (material/location/unit are looked up
    # per-row by the router's own _serialize_item(), not returned by this
    # query) - outer-joined below purely so these can be filtered/sorted.
    "material_code": MaterialModel.material_code,
    "material_name": MaterialModel.material_name,
    "location_code": LocationModel.code,
    "unit_name": UnitOfMaterialModel.name,
}
_ITEM_FILTER_NUMERIC_FIELDS = {"qty_plan", "qty_out", "price", "total_value"}


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
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[StockOutHeaderModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(StockOutHeaderModel).outerjoin(
                DepartmentModel, DepartmentModel.id == StockOutHeaderModel.department_id
            )
            query = apply_keyword_filter(query, [StockOutHeaderModel.description], keyword)
            if query_params is not None:
                query = apply_column_filters(query, query_params, _HEADER_FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _HEADER_SORT_COLUMN_MAP)
            else:
                query = query.order_by(
                    StockOutHeaderModel.date.desc(), StockOutHeaderModel.id.desc()
                )
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def create_header(
        self,
        date,
        description: str,
        department_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> StockOutHeaderModel:
        with SessionLocal() as session:
            header = StockOutHeaderModel(
                date=date, description=description, department_id=department_id,
                created_by=created_by,
            )
            session.add(header)
            session.commit()
            session.refresh(header)
            return header

    def update_header(
        self,
        header_id: int,
        date,
        description: str,
        department_id: Optional[int] = None,
        updated_by: Optional[int] = None,
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
    ) -> tuple[list[StockOutItemModel], Pagination]:
        with SessionLocal() as session:
            query = (
                session.query(StockOutItemModel)
                .outerjoin(MaterialModel, MaterialModel.id == StockOutItemModel.material_id)
                .outerjoin(LocationModel, LocationModel.id == StockOutItemModel.location_id)
                .outerjoin(UnitOfMaterialModel, UnitOfMaterialModel.id == MaterialModel.unit_id)
                .filter(StockOutItemModel.stock_out_header_id == header_id)
            )
            query = apply_keyword_filter(query, [StockOutItemModel.remarks], keyword)
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _ITEM_FILTER_COLUMN_MAP, _ITEM_FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _ITEM_FILTER_COLUMN_MAP)
            else:
                query = query.order_by(StockOutItemModel.id)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)
