"""add qty_plan to receiving_items and stock_out_items (issue #33),
extending the plan_qty precedent already shipped on stock_movement_items
(issue #31) - backfills existing rows so qty_plan matches the actual
qty_received/qty_out, since this rollout has no plan-vs-actual distinction
yet.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_receiving_items_table = sa.table(
    "receiving_items",
    sa.column("qty_plan", sa.Numeric(18, 4)),
    sa.column("qty_received", sa.Numeric(18, 4)),
)
_stock_out_items_table = sa.table(
    "stock_out_items",
    sa.column("qty_plan", sa.Numeric(18, 4)),
    sa.column("qty_out", sa.Numeric(18, 4)),
)


def upgrade() -> None:
    with op.batch_alter_table("receiving_items") as batch_op:
        batch_op.add_column(
            sa.Column("qty_plan", sa.Numeric(18, 4), nullable=True)
        )
    op.execute(
        _receiving_items_table.update().values(
            qty_plan=_receiving_items_table.c.qty_received
        )
    )
    with op.batch_alter_table("receiving_items") as batch_op:
        batch_op.alter_column("qty_plan", existing_type=sa.Numeric(18, 4), nullable=False)

    with op.batch_alter_table("stock_out_items") as batch_op:
        batch_op.add_column(
            sa.Column("qty_plan", sa.Numeric(18, 4), nullable=True)
        )
    op.execute(
        _stock_out_items_table.update().values(
            qty_plan=_stock_out_items_table.c.qty_out
        )
    )
    with op.batch_alter_table("stock_out_items") as batch_op:
        batch_op.alter_column("qty_plan", existing_type=sa.Numeric(18, 4), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("stock_out_items") as batch_op:
        batch_op.drop_column("qty_plan")

    with op.batch_alter_table("receiving_items") as batch_op:
        batch_op.drop_column("qty_plan")
