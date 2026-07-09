"""User-to-module grant ORM model — adopted from the legacy PHP `ap_auth` table."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class UserModulePermissionModel(Base):
    """Grants a user access to a module (one row = one user/module pair)."""

    __tablename__ = "user_module_permissions"
    __table_args__ = (
        UniqueConstraint("module_id", "user_id", name="uq_module_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
