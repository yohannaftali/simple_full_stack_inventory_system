"""seed a full default unit-of-material catalog

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# `PCS` is deliberately absent - it's already seeded by 0022 (as the
# backfill default for pre-existing materials), and this migration's
# idempotency guard would skip it anyway, but leaving it out here keeps
# ownership of that one row unambiguous (0022's, not this migration's - see
# downgrade()).
DEFAULT_UNITS = [
    ("L", "Litres"),
    ("G", "Grams"),
    ("KG", "Kilograms"),
    ("LB", "Pounds"),
    ("OZ", "Ounces"),
    ("GAL", "Gallons"),
    ("ML", "Millilitres"),
    ("CTN", "Carton"),
    ("PACK", "Pack"),
    ("PLT", "Pallet"),
    ("ROLL", "Roll"),
    ("BOX", "Boxes"),
    ("DZ", "Dozens"),
    ("BTL", "Bottles"),
    ("CASE", "Cases"),
    ("M", "Meters"),
    ("CM", "Centimeters"),
    ("FT", "Feet"),
    ("IN", "Inches"),
    ("UNIT", "Units"),
    ("SET", "Sets"),
    ("PAIR", "Pairs"),
]

_units_table = sa.table(
    "units_of_material",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
)


def upgrade() -> None:
    bind = op.get_bind()

    for code, name in DEFAULT_UNITS:
        existing_id = bind.execute(
            sa.select(_units_table.c.id).where(_units_table.c.code == code)
        ).scalar()
        if existing_id is None:
            bind.execute(_units_table.insert().values(code=code, name=name))


def downgrade() -> None:
    bind = op.get_bind()

    for code, _name in DEFAULT_UNITS:
        unit_id = bind.execute(
            sa.select(_units_table.c.id).where(_units_table.c.code == code)
        ).scalar()
        if unit_id is None:
            continue
        # A material may have since been created against this seeded unit -
        # `materials.unit_id` has no ON DELETE CASCADE, so the FK would
        # reject the delete. Skip and leave it in place rather than raising,
        # same friendly-skip precedent as the rest of this codebase's
        # delete-guards (see master_unit_of_material.py's docstring for why
        # a unit is otherwise undeletable through the app itself). A
        # SAVEPOINT (not a full rollback) contains the failed delete to
        # itself - the whole migration still runs inside one outer
        # transaction, and a plain `bind.rollback()` here would abort that
        # entirely rather than just this one row.
        try:
            with bind.begin_nested():
                bind.execute(_units_table.delete().where(_units_table.c.id == unit_id))
        except IntegrityError:
            pass
