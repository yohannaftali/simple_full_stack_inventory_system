"""create units_of_material table and link materials.unit_id (required)

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seeded so every pre-existing material has something to backfill onto -
# "1 material only will have 1 type of unit of material" means unit_id can't
# stay nullable, but a fresh column has nothing to point existing rows at
# without one.
_DEFAULT_UNIT_CODE = "PCS"
_DEFAULT_UNIT_NAME = "Pieces"

_units_table = sa.table(
    "units_of_material",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
)

_materials_table = sa.table(
    "materials",
    sa.column("id", sa.Integer),
    sa.column("unit_id", sa.Integer),
)


def upgrade() -> None:
    op.create_table(
        "units_of_material",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_units_of_material_code", "units_of_material", ["code"], unique=True)

    bind = op.get_bind()
    bind.execute(
        _units_table.insert().values(code=_DEFAULT_UNIT_CODE, name=_DEFAULT_UNIT_NAME)
    )
    default_unit_id = bind.execute(
        sa.select(_units_table.c.id).where(_units_table.c.code == _DEFAULT_UNIT_CODE)
    ).scalar()

    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(sa.Column("unit_id", sa.Integer(), nullable=True))

    bind.execute(_materials_table.update().values(unit_id=default_unit_id))

    with op.batch_alter_table("materials") as batch_op:
        batch_op.alter_column("unit_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_materials_unit_id", ["unit_id"])
        batch_op.create_foreign_key(
            "fk_materials_unit_id_units_of_material", "units_of_material", ["unit_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_constraint(
            "fk_materials_unit_id_units_of_material", type_="foreignkey"
        )
        batch_op.drop_index("ix_materials_unit_id")
        batch_op.drop_column("unit_id")
    op.drop_table("units_of_material")
