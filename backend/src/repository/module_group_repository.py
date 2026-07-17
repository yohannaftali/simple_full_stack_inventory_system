"""Module group repository for data access operations."""

from typing import Optional

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.module_group import ModuleGroupModel

# Reference implementation for issue #10's generic per-column filter
# mechanism — `name` (text, LIKE) and `sort` (numeric, operator-syntax:
# `>=5and<=10` etc.) exercise both `apply_column_filters` code paths on one
# simple, non-aggregate list. See AGENTS.md's "Per-column field filters"
# section before extending this to another screen.
_FILTER_COLUMN_MAP = {"name": ModuleGroupModel.name, "sort": ModuleGroupModel.sort}
_FILTER_NUMERIC_FIELDS = {"sort"}


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
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ModuleGroupModel], Pagination]:
        """List module groups matching an optional keyword, paginated.

        `query_params` (raw `Request.query_params`, optional) additionally
        applies any `{field}-filter` present for `name`/`sort` via
        `apply_column_filters` — skipped entirely if `keyword` is set,
        matching that helper's own keyword-vs-per-column precedence.
        """
        with SessionLocal() as session:
            query = session.query(ModuleGroupModel)
            query = apply_keyword_filter(query, [ModuleGroupModel.name], keyword)
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _FILTER_COLUMN_MAP, _FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(ModuleGroupModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

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
