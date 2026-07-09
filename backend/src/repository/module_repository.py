"""Module repository for data access operations."""

from typing import Optional

from sqlalchemy import func, or_

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
        self, keyword: str = "", limit: int = 20, offset: int = 0
    ) -> tuple[list[ModuleModel], int]:
        """List modules matching an optional keyword, paginated. Returns (rows, total_count)."""
        with SessionLocal() as session:
            query = session.query(ModuleModel)
            if keyword:
                like = f"%{keyword}%"
                query = query.filter(
                    or_(ModuleModel.name.like(like), ModuleModel.label.like(like))
                )
            total = query.with_entities(func.count(ModuleModel.id)).scalar() or 0
            rows = query.order_by(ModuleModel.sort).offset(offset).limit(limit).all()
            return rows, total

    def create_module(
        self,
        name: str,
        label: str,
        sort: int = 0,
        icon: str = "chevron_right",
        description: str = "",
    ) -> ModuleModel:
        """Create a new module."""
        with SessionLocal() as session:
            module = ModuleModel(
                name=name, label=label, sort=sort, icon=icon, description=description
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
