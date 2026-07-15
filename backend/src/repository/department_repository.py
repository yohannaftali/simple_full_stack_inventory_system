"""Department repository for data access operations."""

from typing import Optional

from core.table_query import Pagination, apply_column_filters, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.department import DepartmentModel

_FILTER_COLUMN_MAP = {"code": DepartmentModel.code, "name": DepartmentModel.name}


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
        self, keyword: str = "", query_params=None, limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[DepartmentModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(DepartmentModel)
            query = apply_keyword_filter(
                query, [DepartmentModel.code, DepartmentModel.name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            query = query.order_by(DepartmentModel.code)
            return paginate(query, limit=limit, page=page, offset=offset)

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
