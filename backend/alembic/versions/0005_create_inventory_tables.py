"""create inventory tables (locations, materials, inventory_values,
receiving_headers, receiving_items, stocks, stock_out_headers, stock_out_items)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_locations_code", "locations", ["code"], unique=True)

    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_code", sa.String(length=50), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_materials_material_code", "materials", ["material_code"], unique=True)

    op.create_table(
        "inventory_values",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("average_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_inventory_values_material_id", "inventory_values", ["material_id"], unique=True
    )

    op.create_table(
        "receiving_headers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "receiving_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "receiving_header_id",
            sa.Integer(),
            sa.ForeignKey("receiving_headers.id"),
            nullable=False,
        ),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("price_buy", sa.Numeric(18, 4), nullable=False),
        sa.Column("qty_received", sa.Numeric(18, 4), nullable=False),
        sa.Column("remarks", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_receiving_items_receiving_header_id", "receiving_items", ["receiving_header_id"]
    )
    op.create_index("ix_receiving_items_material_id", "receiving_items", ["material_id"])
    op.create_index("ix_receiving_items_location_id", "receiving_items", ["location_id"])

    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "receiving_item_id",
            sa.Integer(),
            sa.ForeignKey("receiving_items.id"),
            nullable=False,
        ),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "receiving_item_id", "material_id", "location_id", name="uq_stock_lot"
        ),
    )
    op.create_index("ix_stocks_receiving_item_id", "stocks", ["receiving_item_id"])
    op.create_index("ix_stocks_material_id", "stocks", ["material_id"])
    op.create_index("ix_stocks_location_id", "stocks", ["location_id"])

    op.create_table(
        "stock_out_headers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "stock_out_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "stock_out_header_id",
            sa.Integer(),
            sa.ForeignKey("stock_out_headers.id"),
            nullable=False,
        ),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("qty_out", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("remarks", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_stock_out_items_stock_out_header_id", "stock_out_items", ["stock_out_header_id"]
    )
    op.create_index("ix_stock_out_items_material_id", "stock_out_items", ["material_id"])
    op.create_index("ix_stock_out_items_location_id", "stock_out_items", ["location_id"])


def downgrade() -> None:
    op.drop_table("stock_out_items")
    op.drop_table("stock_out_headers")
    op.drop_table("stocks")
    op.drop_table("receiving_items")
    op.drop_table("receiving_headers")
    op.drop_table("inventory_values")
    op.drop_table("materials")
    op.drop_table("locations")
