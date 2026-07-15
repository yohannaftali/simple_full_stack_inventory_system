"""Material repository for data access operations."""

from typing import Optional

from core.table_query import Pagination, apply_column_filters, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.material import MaterialModel

_FILTER_COLUMN_MAP = {
    "material_code": MaterialModel.material_code,
    "material_name": MaterialModel.material_name,
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
        self, keyword: str = "", query_params=None, limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[MaterialModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(MaterialModel)
            query = apply_keyword_filter(
                query, [MaterialModel.material_code, MaterialModel.material_name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            query = query.order_by(MaterialModel.material_code)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_material(
        self,
        material_code: str,
        material_name: str,
        supplier_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> MaterialModel:
        with SessionLocal() as session:
            material = MaterialModel(
                material_code=material_code,
                material_name=material_name,
                supplier_id=supplier_id,
                category_id=category_id,
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
        supplier_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> bool:
        with SessionLocal() as session:
            material = (
                session.query(MaterialModel).filter(MaterialModel.id == material_id).first()
            )
            if material is None:
                return False

            material.material_code = material_code
            material.material_name = material_name
            material.supplier_id = supplier_id
            material.category_id = category_id
            session.commit()
            return True

    def delete_material(self, material_id: int) -> bool:
        with SessionLocal() as session:
            material = (
                session.query(MaterialModel).filter(MaterialModel.id == material_id).first()
            )
            if material is None:
                return False

            session.delete(material)
            session.commit()
            return True
