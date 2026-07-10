"""create module_groups table, seed default groups, and turn
modules.module_group_id into a real (nullable) FK

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (name, sort)
DEFAULT_GROUPS = [
    ("Inventory", 1),
    ("Master", 9),
    ("Application Configuration", 10),
]

_module_groups_table = sa.table(
    "module_groups",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("sort", sa.Integer),
)

_modules_table = sa.table(
    "modules",
    sa.column("id", sa.Integer),
    sa.column("module_group_id", sa.Integer),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Idempotent like every other seed migration in this repo: MySQL/MariaDB
    # DDL auto-commits per-statement (unlike DML), so a migration that fails
    # partway through - e.g. the FK step below - can leave the table already
    # created on the next retry. Guard table/index creation accordingly.
    if not inspector.has_table("module_groups"):
        op.create_table(
            "module_groups",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_module_groups_name", "module_groups", ["name"], unique=True)
        op.create_index("ix_module_groups_sort", "module_groups", ["sort"])

    for name, sort in DEFAULT_GROUPS:
        exists = bind.execute(
            sa.select(_module_groups_table.c.id).where(_module_groups_table.c.name == name)
        ).scalar()
        if exists is None:
            bind.execute(_module_groups_table.insert().values(name=name, sort=sort))

    # module_group_id previously had no FK and defaulted to 0 (legacy PHP
    # parity placeholder) - 0 is not a valid module_groups.id, so the column
    # must be made nullable *before* any row can be cleared to NULL, and the
    # FK constraint can only be added once no row still holds a dangling 0.
    modules_columns = {c["name"]: c for c in inspector.get_columns("modules")}
    if not modules_columns["module_group_id"]["nullable"]:
        with op.batch_alter_table("modules") as batch_op:
            batch_op.alter_column(
                "module_group_id", existing_type=sa.Integer(), nullable=True, server_default=None
            )

    bind.execute(_modules_table.update().where(_modules_table.c.module_group_id == 0).values(
        module_group_id=None
    ))

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("modules")}
    if "fk_modules_module_group_id_module_groups" not in existing_fks:
        with op.batch_alter_table("modules") as batch_op:
            batch_op.create_foreign_key(
                "fk_modules_module_group_id_module_groups",
                "module_groups",
                ["module_group_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(_modules_table.update().where(_modules_table.c.module_group_id.is_(None)).values(
        module_group_id=0
    ))

    with op.batch_alter_table("modules") as batch_op:
        batch_op.drop_constraint(
            "fk_modules_module_group_id_module_groups", type_="foreignkey"
        )
        batch_op.alter_column(
            "module_group_id", existing_type=sa.Integer(), nullable=False, server_default="0"
        )

    op.drop_index("ix_module_groups_sort", table_name="module_groups")
    op.drop_index("ix_module_groups_name", table_name="module_groups")
    op.drop_table("module_groups")
