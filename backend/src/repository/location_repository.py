"""Location repository for data access operations."""

from typing import Optional

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.location import LocationModel

# Maps a frontend field name (Table field dict "name") to the real column it
# sorts by - see core/table_query.py::apply_sort(). Reused as-is for
# apply_column_filters()'s column_map (issue #10 rollout) - same field
# names, same columns.
_SORT_COLUMNS = {"code": LocationModel.code, "name": LocationModel.name}


class LocationRepository:
    """Repository class for location data access operations."""

    def get_location_by_id(self, location_id: int) -> Optional[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).filter(LocationModel.id == location_id).first()

    def get_location_by_code(self, code: str) -> Optional[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).filter(LocationModel.code == code).first()

    def get_all_locations(self) -> list[LocationModel]:
        with SessionLocal() as session:
            return session.query(LocationModel).order_by(LocationModel.code).all()

    def list_locations(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[LocationModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(LocationModel)
            query = apply_keyword_filter(
                query, [LocationModel.code, LocationModel.name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _SORT_COLUMNS)
            if sort_fields:
                query = apply_sort(query, sort_fields, _SORT_COLUMNS)
            else:
                query = query.order_by(LocationModel.code)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def create_location(
        self, code: str, name: str, created_by: Optional[int] = None
    ) -> LocationModel:
        with SessionLocal() as session:
            location = LocationModel(code=code, name=name, created_by=created_by)
            session.add(location)
            session.commit()
            session.refresh(location)
            return location

    def update_location(
        self, location_id: int, code: str, name: str, updated_by: Optional[int] = None
    ) -> bool:
        with SessionLocal() as session:
            location = (
                session.query(LocationModel).filter(LocationModel.id == location_id).first()
            )
            if location is None:
                return False

            location.code = code
            location.name = name
            location.updated_by = updated_by
            session.commit()
            return True

    def delete_location(self, location_id: int) -> bool:
        with SessionLocal() as session:
            location = (
                session.query(LocationModel).filter(LocationModel.id == location_id).first()
            )
            if location is None:
                return False

            session.delete(location)
            session.commit()
            return True
