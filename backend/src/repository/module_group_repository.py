"""Module group repository for data access operations."""

from typing import Optional

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.module_group import ModuleGroupModel


class ModuleGroupRepository:
    """Repository class for module group data access operations."""

    def get_group_by_id(self, group_id: int) -> Optional[ModuleGroupModel]:
        with SessionLocal() as session:
            return (
                session.query(ModuleGroupModel).filter(ModuleGroupModel.id == group_id).first()
            )

    def get_group_by_name(self, name: str) -> Optional[ModuleGroupModel]:
        with SessionLocal() as session:
            return (
                session.query(ModuleGroupModel).filter(ModuleGroupModel.name == name).first()
            )

    def get_all_groups(self) -> list[ModuleGroupModel]:
        """Get all module groups, ordered by sort."""
        with SessionLocal() as session:
            return session.query(ModuleGroupModel).order_by(ModuleGroupModel.sort).all()

    def list_groups(
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[ModuleGroupModel], Pagination]:
        """List module groups matching an optional keyword, paginated."""
        with SessionLocal() as session:
            query = session.query(ModuleGroupModel)
            query = apply_keyword_filter(query, [ModuleGroupModel.name], keyword)
            query = query.order_by(ModuleGroupModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_group(self, name: str, sort: int = 0) -> ModuleGroupModel:
        with SessionLocal() as session:
            group = ModuleGroupModel(name=name, sort=sort)
            session.add(group)
            session.commit()
            session.refresh(group)
            return group

    def update_group(self, group_id: int, name: str, sort: int = 0) -> bool:
        with SessionLocal() as session:
            group = (
                session.query(ModuleGroupModel).filter(ModuleGroupModel.id == group_id).first()
            )
            if group is None:
                return False

            group.name = name
            group.sort = sort
            session.commit()
            return True

    def delete_group(self, group_id: int) -> bool:
        with SessionLocal() as session:
            group = (
                session.query(ModuleGroupModel).filter(ModuleGroupModel.id == group_id).first()
            )
            if group is None:
                return False

            session.delete(group)
            session.commit()
            return True
