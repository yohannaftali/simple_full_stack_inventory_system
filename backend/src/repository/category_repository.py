"""Category repository for data access operations."""

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

_FILTER_COLUMN_MAP = {
    "code": CategoryModel.code,
    "name": CategoryModel.name,
    "description": CategoryModel.description,
}


class CategoryRepository:
    """Repository class for category data access operations."""

    def get_category_by_id(self, category_id: int) -> Optional[CategoryModel]:
        with SessionLocal() as session:
            return session.query(CategoryModel).filter(CategoryModel.id == category_id).first()

    def get_category_by_code(self, code: str) -> Optional[CategoryModel]:
        with SessionLocal() as session:
            return session.query(CategoryModel).filter(CategoryModel.code == code).first()

    def get_all_categories(self) -> list[CategoryModel]:
        with SessionLocal() as session:
            return session.query(CategoryModel).order_by(CategoryModel.code).all()

    def list_categories(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[CategoryModel], Pagination]:
        with SessionLocal() as session:
            query = session.query(CategoryModel)
            query = apply_keyword_filter(
                query, [CategoryModel.code, CategoryModel.name], keyword
            )
            if query_params is not None:
                query = apply_column_filters(query, query_params, _FILTER_COLUMN_MAP)
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(CategoryModel.code)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_category(self, code: str, name: str, description: str = "") -> CategoryModel:
        with SessionLocal() as session:
            category = CategoryModel(code=code, name=name, description=description)
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    def update_category(
        self, category_id: int, code: str, name: str, description: str = ""
    ) -> bool:
        with SessionLocal() as session:
            category = (
                session.query(CategoryModel).filter(CategoryModel.id == category_id).first()
            )
            if category is None:
                return False

            category.code = code
            category.name = name
            category.description = description
            session.commit()
            return True

    def delete_category(self, category_id: int) -> bool:
        with SessionLocal() as session:
            category = (
                session.query(CategoryModel).filter(CategoryModel.id == category_id).first()
            )
            if category is None:
                return False

            session.delete(category)
            session.commit()
            return True
