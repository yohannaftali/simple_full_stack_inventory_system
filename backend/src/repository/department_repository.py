"""Department repository for data access operations."""

from typing import Optional

from sqlalchemy import func, or_

from models.base import SessionLocal
from models.department import DepartmentModel


class DepartmentRepository:
    """Repository class for department data access operations."""

    def get_department_by_id(self, department_id: int) -> Optional[DepartmentModel]:
        with SessionLocal() as session:
            return (
                session.query(DepartmentModel)
                .filter(DepartmentModel.id == department_id)
                .first()
            )

    def get_department_by_code(self, code: str) -> Optional[DepartmentModel]:
        with SessionLocal() as session:
            return session.query(DepartmentModel).filter(DepartmentModel.code == code).first()

    def get_all_departments(self) -> list[DepartmentModel]:
        with SessionLocal() as session:
            return session.query(DepartmentModel).order_by(DepartmentModel.code).all()

    def list_departments(
        self, keyword: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[DepartmentModel], int]:
        with SessionLocal() as session:
            query = session.query(DepartmentModel)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    or_(DepartmentModel.code.like(like), DepartmentModel.name.like(like))
                )
            total = query.with_entities(func.count(DepartmentModel.id)).scalar() or 0
            rows = query.order_by(DepartmentModel.code).offset(offset).limit(limit).all()
            return rows, total

    def create_department(self, code: str, name: str) -> DepartmentModel:
        with SessionLocal() as session:
            department = DepartmentModel(code=code, name=name)
            session.add(department)
            session.commit()
            session.refresh(department)
            return department

    def update_department(self, department_id: int, code: str, name: str) -> bool:
        with SessionLocal() as session:
            department = (
                session.query(DepartmentModel)
                .filter(DepartmentModel.id == department_id)
                .first()
            )
            if department is None:
                return False

            department.code = code
            department.name = name
            session.commit()
            return True

    def delete_department(self, department_id: int) -> bool:
        with SessionLocal() as session:
            department = (
                session.query(DepartmentModel)
                .filter(DepartmentModel.id == department_id)
                .first()
            )
            if department is None:
                return False

            session.delete(department)
            session.commit()
            return True
