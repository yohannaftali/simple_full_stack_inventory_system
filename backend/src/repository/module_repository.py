"""Module repository for data access operations."""

from typing import Optional

from core.table_query import Pagination, apply_keyword_filter, paginate
from models.base import SessionLocal
from models.module import ModuleModel


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
        self, keyword: str = "", limit: int = 20, page: int = 1, offset: int = 0
    ) -> tuple[list[ModuleModel], Pagination]:
        """List modules matching an optional keyword, paginated."""
        with SessionLocal() as session:
            query = session.query(ModuleModel)
            query = apply_keyword_filter(
                query, [ModuleModel.name, ModuleModel.label], keyword
            )
            query = query.order_by(ModuleModel.sort)
            return paginate(query, limit=limit, page=page, offset=offset)

    def create_module(
        self,
        name: str,
        label: str,
        sort: int = 0,
        icon: str = "chevron_right",
        description: str = "",
        module_group_id: Optional[int] = None,
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
