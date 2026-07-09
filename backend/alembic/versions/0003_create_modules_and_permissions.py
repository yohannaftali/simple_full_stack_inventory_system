"""create modules and user_module_permissions tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("sort_mobile", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("module_type", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("module_group_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "icon", sa.String(length=255), nullable=False, server_default="chevron_right"
        ),
        sa.Column(
            "mdi", sa.String(length=255), nullable=False, server_default="chevron_right"
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_modules_name", "modules", ["name"], unique=True)
    op.create_index("ix_modules_sort", "modules", ["sort"])
    op.create_index("ix_modules_sort_mobile", "modules", ["sort_mobile"])
    op.create_index("ix_modules_module_type", "modules", ["module_type"])
    op.create_index("ix_modules_module_group_id", "modules", ["module_group_id"])

    op.create_table(
        "user_module_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "module_id", sa.Integer(), sa.ForeignKey("modules.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("module_id", "user_id", name="uq_module_user"),
    )
    op.create_index(
        "ix_user_module_permissions_module_id", "user_module_permissions", ["module_id"]
    )
    op.create_index(
        "ix_user_module_permissions_user_id", "user_module_permissions", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_module_permissions_user_id", table_name="user_module_permissions")
    op.drop_index("ix_user_module_permissions_module_id", table_name="user_module_permissions")
    op.drop_table("user_module_permissions")

    op.drop_index("ix_modules_module_group_id", table_name="modules")
    op.drop_index("ix_modules_module_type", table_name="modules")
    op.drop_index("ix_modules_sort_mobile", table_name="modules")
    op.drop_index("ix_modules_sort", table_name="modules")
    op.drop_index("ix_modules_name", table_name="modules")
    op.drop_table("modules")
