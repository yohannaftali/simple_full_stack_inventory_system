"""Module repository for data access operations."""

from typing import Optional

from core.table_query import (
    Pagination,
    apply_column_filters,
    apply_keyword_filter,
    apply_sort,
    paginate,
)
from models.base import SessionLocal
from models.module import ModuleModel
from models.module_group import ModuleGroupModel
from models.user_module_permission import UserModulePermissionModel

_FILTER_COLUMN_MAP = {
    "name": ModuleModel.name,
    "label": ModuleModel.label,
    "sort": ModuleModel.sort,
    "icon": ModuleModel.icon,
    "description": ModuleModel.description,
    # Join-derived display column (looked up per-row by the router's own
    # _serialize(), not returned by this query) - outer-joined below purely
    # so it can be filtered/sorted.
    "module_group_name": ModuleGroupModel.name,
}
_FILTER_NUMERIC_FIELDS = {"sort"}


class ModuleRepository:
    """Repository class for module data access operations."""

    def get_module_by_name(self, name: str) -> Optional[ModuleModel]:
        """Get a module by its unique name."""
        with SessionLocal() as session:
            return session.query(ModuleModel).filter(ModuleModel.name == name).first()

    def get_module_by_id(self, module_id: int) -> Optional[ModuleModel]:
        """Get a module by id."""
        with SessionLocal() as session:
            return session.query(ModuleModel).filter(ModuleModel.id == module_id).first()

    def get_all_modules(self) -> list[ModuleModel]:
        """Get all registered modules, ordered by sort."""
        with SessionLocal() as session:
            return (
                session.query(ModuleModel).order_by(ModuleModel.sort).all()
            )

    def list_modules(
        self,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ModuleModel], Pagination]:
        """List modules matching an optional keyword, paginated."""
        with SessionLocal() as session:
            query = session.query(ModuleModel).outerjoin(
                ModuleGroupModel, ModuleGroupModel.id == ModuleModel.module_group_id
            )
            query = apply_keyword_filter(
                query, [ModuleModel.name, ModuleModel.label], keyword
            )
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _FILTER_COLUMN_MAP, _FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(ModuleModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def list_granted_modules_for_user(
        self,
        user_id: int,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ModuleModel], Pagination]:
        """List modules a user has already been granted access to, paginated
        - backs the read-only module-access table on `ap_master_user/edit.py`."""
        with SessionLocal() as session:
            query = (
                session.query(ModuleModel)
                .join(
                    UserModulePermissionModel,
                    UserModulePermissionModel.module_id == ModuleModel.id,
                )
                .outerjoin(
                    ModuleGroupModel, ModuleGroupModel.id == ModuleModel.module_group_id
                )
                .filter(UserModulePermissionModel.user_id == user_id)
            )
            query = apply_keyword_filter(
                query, [ModuleModel.name, ModuleModel.label], keyword
            )
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _FILTER_COLUMN_MAP, _FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(ModuleModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def list_ungranted_modules_for_user(
        self,
        user_id: int,
        keyword: str = "",
        query_params=None,
        limit: int = 20,
        page: int = 1,
        offset: int = 0,
        sort_fields: list[tuple[str, str]] | None = None,
    ) -> tuple[list[ModuleModel], Pagination]:
        """List modules a user has NOT yet been granted access to, paginated
        - backs the checkbox-select table on `ap_master_user/permission_new.py`."""
        with SessionLocal() as session:
            granted_subquery = session.query(UserModulePermissionModel.module_id).filter(
                UserModulePermissionModel.user_id == user_id
            )
            query = (
                session.query(ModuleModel)
                .outerjoin(
                    ModuleGroupModel, ModuleGroupModel.id == ModuleModel.module_group_id
                )
                .filter(~ModuleModel.id.in_(granted_subquery))
            )
            query = apply_keyword_filter(
                query, [ModuleModel.name, ModuleModel.label], keyword
            )
            if query_params is not None:
                query = apply_column_filters(
                    query, query_params, _FILTER_COLUMN_MAP, _FILTER_NUMERIC_FIELDS
                )
            if sort_fields:
                query = apply_sort(query, sort_fields, _FILTER_COLUMN_MAP)
            else:
                query = query.order_by(ModuleModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset, sort_fields=sort_fields)

    def create_module(
        self,
        name: str,
        label: str,
        sort: int = 0,
        icon: str = "chevron_right",
        description: str = "",
        module_group_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> ModuleModel:
        """Create a new module."""
        with SessionLocal() as session:
            module = ModuleModel(
                name=name,
                label=label,
                sort=sort,
                icon=icon,
                description=description,
                module_group_id=module_group_id,
                created_by=created_by,
            )
            session.add(module)
            session.commit()
            session.refresh(module)
            return module

    def update_module(
        self,
        module_id: int,
        name: str,
        label: str,
        sort: int = 0,
        icon: str = "chevron_right",
        description: str = "",
        module_group_id: Optional[int] = None,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Update an existing module."""
        with SessionLocal() as session:
            module = session.query(ModuleModel).filter(ModuleModel.id == module_id).first()
            if module is None:
                return False

            module.name = name
            module.label = label
            module.sort = sort
            module.icon = icon
            module.description = description
            module.module_group_id = module_group_id
            module.updated_by = updated_by
            session.commit()
            return True

    def delete_module(self, module_id: int) -> bool:
        """Delete a module by id."""
        with SessionLocal() as session:
            module = session.query(ModuleModel).filter(ModuleModel.id == module_id).first()
            if module is None:
                return False

            session.delete(module)
            session.commit()
            return True
