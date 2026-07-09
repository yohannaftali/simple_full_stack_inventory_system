"""Material repository for data access operations."""

from typing import Optional

from sqlalchemy import func, or_

from models.base import SessionLocal
from models.material import MaterialModel


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
        self, keyword: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[MaterialModel], int]:
        with SessionLocal() as session:
            query = session.query(MaterialModel)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    or_(
                        MaterialModel.material_code.like(like),
                        MaterialModel.material_name.like(like),
                    )
                )
            total = query.with_entities(func.count(MaterialModel.id)).scalar() or 0
            rows = (
                query.order_by(MaterialModel.material_code).offset(offset).limit(limit).all()
            )
            return rows, total

    def create_material(self, material_code: str, material_name: str) -> MaterialModel:
        with SessionLocal() as session:
            material = MaterialModel(material_code=material_code, material_name=material_name)
            session.add(material)
            session.commit()
            session.refresh(material)
            return material

    def update_material(self, material_id: int, material_code: str, material_name: str) -> bool:
        with SessionLocal() as session:
            material = (
                session.query(MaterialModel).filter(MaterialModel.id == material_id).first()
            )
            if material is None:
                return False

            material.material_code = material_code
            material.material_name = material_name
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
