"""create stock_movement_headers/stock_movement_items tables (issue #31);
make stocks.receiving_item_id nullable and add stocks.stock_movement_item_id,
so a movement's destination lot can exist without a receiving_item - a lot
row is now sourced from EITHER a receiving_item OR a stock_movement_item
(never both), same as how a receiving item already owns exactly one lot row.

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_movement_headers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_stock_movement_headers_created_by", "stock_movement_headers", ["created_by"]
    )
    op.create_index(
        "ix_stock_movement_headers_updated_by", "stock_movement_headers", ["updated_by"]
    )

    op.create_table(
        "stock_movement_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "stock_movement_header_id",
            sa.Integer(),
            sa.ForeignKey("stock_movement_headers.id"),
            nullable=False,
        ),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column(
            "origin_location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False
        ),
        sa.Column(
            "destination_location_id",
            sa.Integer(),
            sa.ForeignKey("locations.id"),
            nullable=False,
        ),
        sa.Column("plan_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("movement_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("remarks", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_stock_movement_items_stock_movement_header_id",
        "stock_movement_items",
        ["stock_movement_header_id"],
    )
    op.create_index(
        "ix_stock_movement_items_material_id", "stock_movement_items", ["material_id"]
    )
    op.create_index(
        "ix_stock_movement_items_origin_location_id",
        "stock_movement_items",
        ["origin_location_id"],
    )
    op.create_index(
        "ix_stock_movement_items_destination_location_id",
        "stock_movement_items",
        ["destination_location_id"],
    )
    op.create_index(
        "ix_stock_movement_items_created_by", "stock_movement_items", ["created_by"]
    )
    op.create_index(
        "ix_stock_movement_items_updated_by", "stock_movement_items", ["updated_by"]
    )

    with op.batch_alter_table("stocks") as batch_op:
        batch_op.alter_column("receiving_item_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(
            sa.Column(
                "stock_movement_item_id",
                sa.Integer(),
                sa.ForeignKey("stock_movement_items.id"),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_stocks_stock_movement_item_id", ["stock_movement_item_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("stocks") as batch_op:
        batch_op.drop_index("ix_stocks_stock_movement_item_id")
        batch_op.drop_column("stock_movement_item_id")
        batch_op.alter_column("receiving_item_id", existing_type=sa.Integer(), nullable=False)

    op.drop_table("stock_movement_items")
    op.drop_table("stock_movement_headers")
