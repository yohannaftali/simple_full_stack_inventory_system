"""add receiving_headers.supplier_id (nullable FK to suppliers)

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("receiving_headers") as batch_op:
        batch_op.add_column(sa.Column("supplier_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_receiving_headers_supplier_id", ["supplier_id"])
        batch_op.create_foreign_key(
            "fk_receiving_headers_supplier_id_suppliers",
            "suppliers",
            ["supplier_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("receiving_headers") as batch_op:
        batch_op.drop_constraint(
            "fk_receiving_headers_supplier_id_suppliers", type_="foreignkey"
        )
        batch_op.drop_index("ix_receiving_headers_supplier_id")
        batch_op.drop_column("supplier_id")
