"""Unit of material repository for data access operations.

No `delete_unit` method by design — a unit of material can never be removed
once created (every material links to exactly one, and deleting the unit out
from under them would break that link), matching `master_material`'s own
delete-guard reasoning. Same CRUD shape as `location_repository.py` otherwise.
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
from models.unit_of_material import UnitOfMaterialModel

_FILTER_COLUMN_MAP = {
    "code": UnitOfMaterialModel.code,
    "name": UnitOfMaterialModel.name,
}


class UnitOfMaterialRepository:
    """Repository class for unit of material data access operations."""

    def get_unit_by_id(self, unit_id: int) -> Optional[UnitOfMaterialModel]:
        with SessionLocal() as session:
            return (
                session.query(UnitOfMaterialModel)
                .filter(UnitOfMaterialModel.id == unit_id)
                .first()
            )

    def get_unit_by_code(self, code: str) -> Optional[UnitOfMaterialModel]:
        with SessionLocal() as session:
            return (
                session.query(UnitOfMaterialModel)
                .filter(UnitOfMaterialModel.code == code)
                .first()
            )

    def get_all_units(self) -> list[UnitOfMaterialModel]:
        with SessionLocal() as session:
            return session.query(UnitOfMaterialModel).order_by(UnitOfMaterialModel.code).all()

    def list_units(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[UnitOfMaterialModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(UnitOfMaterialModel)
            query = apply_keyword_filter(
                query, [UnitOfMaterialModel.code, UnitOfMaterialModel.name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(UnitOfMaterialModel.code)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_unit(self, code: str, name: str) -> UnitOfMaterialModel:
        with SessionLocal() as session:
            unit = UnitOfMaterialModel(code=code, name=name)
            session.add(unit)
            session.commit()
            session.refresh(unit)
            return unit

    def update_unit(self, unit_id: int, code: str, name: str) -> bool:
        with SessionLocal() as session:
            unit = (
                session.query(UnitOfMaterialModel)
                .filter(UnitOfMaterialModel.id == unit_id)
                .first()
            )
            if unit is None:
                return False

            unit.code = code
            unit.name = name
            session.commit()
            return True
