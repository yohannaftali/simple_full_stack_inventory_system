"""remove materials.supplier_id (a material may have many suppliers;
tracked per receiving header instead, see 0019)

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_constraint(
            "fk_materials_supplier_id_suppliers", type_="foreignkey"
        )
        batch_op.drop_index("ix_materials_supplier_id")
        batch_op.drop_column("supplier_id")


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_materials_supplier_id", ["supplier_id"])
        batch_op.create_foreign_key(
            "fk_materials_supplier_id_suppliers", "suppliers", ["supplier_id"], ["id"]
        )
