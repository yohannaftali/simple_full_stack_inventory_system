"""Material repository for data access operations."""

from typing import Optional

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.category import CategoryModel
from models.material import MaterialModel
from models.unit_of_material import UnitOfMaterialModel

_FILTER_COLUMN_MAP = {
    "material_code": MaterialModel.material_code,
    "material_name": MaterialModel.material_name,
    "is_active": MaterialModel.is_active,
    # Join-derived display columns (category/unit are looked up per-row by
    # the router's own _serialize(), not returned by this query) -
    # outer/inner-joined below purely so these can be filtered/sorted.
    "category_name": CategoryModel.name,
    "unit_name": UnitOfMaterialModel.name,
}


class MaterialRepository:
    """Repository class for material data access operations."""

    def get_material_by_id(self, material_id: int) -> Optional[MaterialModel]:
        with SessionLocal() as session:
            return (
                session.query(MaterialModel).filter(MaterialModel.id == material_id).first()
            )

    def get_material_by_code(self, material_code: str) -> Optional[MaterialModel]:
        with SessionLocal() as session:
            return (
                session.query(MaterialModel)
                .filter(MaterialModel.material_code == material_code)
                .first()
            )

    def get_all_materials(self) -> list[MaterialModel]:
        with SessionLocal() as session:
            return session.query(MaterialModel).order_by(MaterialModel.material_code).all()

    def list_materials(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[MaterialModel], Pagination]:
        with SessionLocal() as session:
            query = (
                session.query(MaterialModel)
                .outerjoin(CategoryModel, CategoryModel.id == MaterialModel.category_id)
                .join(UnitOfMaterialModel, UnitOfMaterialModel.id == MaterialModel.unit_id)
            )
            query = apply_keyword_filter(
                query, [MaterialModel.material_code, MaterialModel.material_name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(MaterialModel.material_code)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def create_material(
        self,
        material_code: str,
        material_name: str,
        unit_id: int,
        category_id: Optional[int] = None,
        is_active: bool = True,
    ) -> MaterialModel:
        with SessionLocal() as session:
            material = MaterialModel(
                material_code=material_code,
                material_name=material_name,
                unit_id=unit_id,
                category_id=category_id,
                is_active=is_active,
            )
            session.add(material)
            session.commit()
            session.refresh(material)
            return material

    def update_material(
        self,
        material_id: int,
        material_code: str,
        material_name: str,
        unit_id: int,
        category_id: Optional[int] = None,
        is_active: bool = True,
    ) -> bool:
        with SessionLocal() as session:
            material = (
                session.query(MaterialModel).filter(MaterialModel.id == material_id).first()
            )
            if material is None:
                return False

            material.material_code = material_code
            material.material_name = material_name
            material.unit_id = unit_id
            material.category_id = category_id
            material.is_active = is_active
            session.commit()
            return True
