"""standardize created_at/created_by/updated_at/updated_by across every
table (issue #34), generalizing the nullable created_by/updated_by FK shape
stock_movement_headers/stock_movement_items already shipped with (issue
#31) to every other table, and fixing every table's updated_at column to
the newly-confirmed semantics: NULL until the row's first real UPDATE
(onupdate=func.now() only, no server_default), instead of also being
stamped at INSERT time. created_at is unaffected (already NOT NULL +
server_default=func.now() everywhere) except on inventory_values/
user_module_permissions, which had no created_at/created_by/updated_by at
all before this migration - added fresh here, backfilled by their own
server_default like every other table's created_at.

Existing rows: created_by/updated_by are NULL for every pre-existing row
(no way to retroactively know who created/updated them) - not backfilled
with a placeholder, per the issue's own confirmed design decision.

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that already have created_at (NOT NULL, server_default=func.now())
# and the old-shape updated_at (NOT NULL, server_default=func.now(),
# onupdate=func.now()), but no created_by/updated_by yet.
_STANDARD_TABLES = [
    "app_configs",
    "categories",
    "departments",
    "locations",
    "mail_configs",
    "materials",
    "modules",
    "module_groups",
    "receiving_headers",
    "receiving_items",
    "stocks",
    "stock_out_headers",
    "stock_out_items",
    "suppliers",
    "units_of_material",
    "users",
]

# Tables that already have created_by/updated_by (issue #31) and just need
# their updated_at column's semantics fixed.
_ALREADY_HAS_AUDIT_BY_TABLES = [
    "stock_movement_headers",
    "stock_movement_items",
]


def _add_audit_by_columns(table: str) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.create_index(f"ix_{table}_created_by", ["created_by"])
        batch_op.create_foreign_key(
            f"fk_{table}_created_by_users", "users", ["created_by"], ["id"]
        )
        batch_op.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
        batch_op.create_index(f"ix_{table}_updated_by", ["updated_by"])
        batch_op.create_foreign_key(
            f"fk_{table}_updated_by_users", "users", ["updated_by"], ["id"]
        )


def _drop_audit_by_columns(table: str) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.drop_constraint(f"fk_{table}_updated_by_users", type_="foreignkey")
        batch_op.drop_index(f"ix_{table}_updated_by")
        batch_op.drop_column("updated_by")
        batch_op.drop_constraint(f"fk_{table}_created_by_users", type_="foreignkey")
        batch_op.drop_index(f"ix_{table}_created_by")
        batch_op.drop_column("created_by")


def _loosen_updated_at(table: str) -> None:
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=True,
            server_default=None,
            existing_nullable=False,
            existing_server_default=sa.func.now(),
        )


def _restore_updated_at(table: str) -> None:
    # A downgrade must backfill any NULL updated_at (the normal case for a
    # row never updated since this migration) before the column can go
    # back to NOT NULL - otherwise the ALTER itself fails with a data
    # truncation/constraint error.
    _table = sa.table(
        table, sa.column("created_at", sa.DateTime()), sa.column("updated_at", sa.DateTime())
    )
    op.execute(
        _table.update()
        .where(_table.c.updated_at.is_(None))
        .values(updated_at=_table.c.created_at)
    )
    with op.batch_alter_table(table) as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            existing_nullable=True,
        )


def upgrade() -> None:
    for table in _STANDARD_TABLES:
        _add_audit_by_columns(table)
        _loosen_updated_at(table)

    for table in _ALREADY_HAS_AUDIT_BY_TABLES:
        _loosen_updated_at(table)

    # inventory_values had no created_at/created_by/updated_by at all.
    with op.batch_alter_table("inventory_values") as batch_op:
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_inventory_values_created_by", ["created_by"])
        batch_op.create_foreign_key(
            "fk_inventory_values_created_by_users", "users", ["created_by"], ["id"]
        )
        batch_op.add_column(
            sa.Column(
                "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            )
        )
        batch_op.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_inventory_values_updated_by", ["updated_by"])
        batch_op.create_foreign_key(
            "fk_inventory_values_updated_by_users", "users", ["updated_by"], ["id"]
        )
    _loosen_updated_at("inventory_values")

    # user_module_permissions had no created_at/updated_at/created_by/updated_by at all.
    with op.batch_alter_table("user_module_permissions") as batch_op:
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_user_module_permissions_created_by", ["created_by"])
        batch_op.create_foreign_key(
            "fk_user_module_permissions_created_by_users", "users", ["created_by"], ["id"]
        )
        batch_op.add_column(
            sa.Column(
                "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
            )
        )
        batch_op.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
        batch_op.create_index("ix_user_module_permissions_updated_by", ["updated_by"])
        batch_op.create_foreign_key(
            "fk_user_module_permissions_updated_by_users", "users", ["updated_by"], ["id"]
        )
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_module_permissions") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_constraint(
            "fk_user_module_permissions_updated_by_users", type_="foreignkey"
        )
        batch_op.drop_index("ix_user_module_permissions_updated_by")
        batch_op.drop_column("updated_by")
        batch_op.drop_column("created_at")
        batch_op.drop_constraint(
            "fk_user_module_permissions_created_by_users", type_="foreignkey"
        )
        batch_op.drop_index("ix_user_module_permissions_created_by")
        batch_op.drop_column("created_by")

    _restore_updated_at("inventory_values")
    with op.batch_alter_table("inventory_values") as batch_op:
        batch_op.drop_constraint(
            "fk_inventory_values_updated_by_users", type_="foreignkey"
        )
        batch_op.drop_index("ix_inventory_values_updated_by")
        batch_op.drop_column("updated_by")
        batch_op.drop_column("created_at")
        batch_op.drop_constraint(
            "fk_inventory_values_created_by_users", type_="foreignkey"
        )
        batch_op.drop_index("ix_inventory_values_created_by")
        batch_op.drop_column("created_by")

    for table in _ALREADY_HAS_AUDIT_BY_TABLES:
        _restore_updated_at(table)

    for table in _STANDARD_TABLES:
        _restore_updated_at(table)
        _drop_audit_by_columns(table)
