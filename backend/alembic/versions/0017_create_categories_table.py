"""create categories table and link materials.category_id

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_categories_code", "categories", ["code"], unique=True)

    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_materials_category_id", ["category_id"])
        batch_op.create_foreign_key(
            "fk_materials_category_id_categories", "categories", ["category_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_constraint(
            "fk_materials_category_id_categories", type_="foreignkey"
        )
        batch_op.drop_index("ix_materials_category_id")
        batch_op.drop_column("category_id")
    op.drop_table("categories")
