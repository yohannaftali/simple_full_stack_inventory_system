"""create suppliers table and link materials.supplier_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"], unique=True)

    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_materials_supplier_id", ["supplier_id"])
        batch_op.create_foreign_key(
            "fk_materials_supplier_id_suppliers", "suppliers", ["supplier_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_constraint(
            "fk_materials_supplier_id_suppliers", type_="foreignkey"
        )
        batch_op.drop_index("ix_materials_supplier_id")
        batch_op.drop_column("supplier_id")
    op.drop_table("suppliers")
