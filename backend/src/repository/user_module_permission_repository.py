"""User-module permission repository for data access operations."""

from typing import Optional

from models.base import SessionLocal
from models.module import ModuleModel
from models.module_group import ModuleGroupModel
from models.user_module_permission import UserModulePermissionModel


class UserModulePermissionRepository:
    """Repository class for user/module permission grants."""

    def has_access(self, user_id: int, module_id: int) -> bool:
        """Check whether a user has been granted access to a module."""
        with SessionLocal() as session:
            row = (
                session.query(UserModulePermissionModel.id)
                .filter(
                    UserModulePermissionModel.user_id == user_id,
                    UserModulePermissionModel.module_id == module_id,
                )
                .first()
            )
            return row is not None

    def get_modules_for_user(self, user_id: int) -> list[ModuleModel]:
        """Get every module a user has been granted access to, sorted by
        group sort first (so home screen groups appear in their configured
        order) then by the module's own `sort` within that group. Ungrouped
        modules (`module_group_id` is NULL) sort before any group, since
        that's this codebase's convention (see `module_group_id`'s FK)."""
        with SessionLocal() as session:
            return (
                session.query(ModuleModel)
                .join(
                    UserModulePermissionModel,
                    UserModulePermissionModel.module_id == ModuleModel.id,
                )
                .outerjoin(
                    ModuleGroupModel, ModuleGroupModel.id == ModuleModel.module_group_id
                )
                .filter(UserModulePermissionModel.user_id == user_id)
                .order_by(ModuleGroupModel.sort, ModuleModel.sort)
                .all()
            )

    def grant_access(
        self, user_id: int, module_id: int, granted_by: Optional[int] = None
    ) -> bool:
        """Grant a user access to a module. No-op if already granted."""
        if self.has_access(user_id, module_id):
            return True
        with SessionLocal() as session:
            session.add(
                UserModulePermissionModel(
                    user_id=user_id, module_id=module_id, created_by=granted_by
                )
            )
            session.commit()
            return True

    def revoke_access(self, user_id: int, module_id: int) -> bool:
        """Revoke a user's access to a module."""
        with SessionLocal() as session:
            grant = (
                session.query(UserModulePermissionModel)
                .filter(
                    UserModulePermissionModel.user_id == user_id,
                    UserModulePermissionModel.module_id == module_id,
                )
                .first()
            )
            if grant is None:
                return False

            session.delete(grant)
            session.commit()
            return True

    def get_module_ids_for_user(self, user_id: int) -> list[int]:
        """Get the ids of every module a user has been granted access to."""
        with SessionLocal() as session:
            rows = (
                session.query(UserModulePermissionModel.module_id)
                .filter(UserModulePermissionModel.user_id == user_id)
                .all()
            )
            return [row[0] for row in rows]

    def set_modules_for_user(
        self, user_id: int, module_ids: list[int], granted_by: Optional[int] = None
    ) -> None:
        """Replace a user's module grants with exactly `module_ids`."""
        target = set(module_ids)
        with SessionLocal() as session:
            existing = (
                session.query(UserModulePermissionModel)
                .filter(UserModulePermissionModel.user_id == user_id)
                .all()
            )
            existing_ids = {grant.module_id for grant in existing}

            for grant in existing:
                if grant.module_id not in target:
                    session.delete(grant)

            for module_id in target - existing_ids:
                session.add(
                    UserModulePermissionModel(
                        user_id=user_id, module_id=module_id, created_by=granted_by
                    )
                )

            session.commit()

    def delete_permissions_for_module(self, module_id: int) -> None:
        """Delete every grant referencing a module (call before deleting the module)."""
        with SessionLocal() as session:
            session.query(UserModulePermissionModel).filter(
                UserModulePermissionModel.module_id == module_id
            ).delete()
            session.commit()

    def delete_permissions_for_user(self, user_id: int) -> None:
        """Delete every grant referencing a user (call before deleting the user)."""
        with SessionLocal() as session:
            session.query(UserModulePermissionModel).filter(
                UserModulePermissionModel.user_id == user_id
            ).delete()
            session.commit()
