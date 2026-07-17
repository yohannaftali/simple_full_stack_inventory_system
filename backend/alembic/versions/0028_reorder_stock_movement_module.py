"""move the stock_movement module tile to sit between stock_in and stock_out
on the Home screen (user-requested reorder, issue #31 follow-up) - a
data-only migration reassigning modules.sort by name, same pattern as
0013_assign_module_groups.py.

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (module name, new sort, old sort) - old values are what 0006/0020/0027
# originally seeded, restored on downgrade.
REORDER = [
    ("stock_movement", 21, 25),
    ("stock_out", 22, 21),
    ("stock_browse", 23, 22),
    ("usage_report", 24, 23),
    ("purchase_report", 25, 24),
]

_modules_table = sa.table(
    "modules",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("sort", sa.Integer),
)


def upgrade() -> None:
    bind = op.get_bind()
    for name, new_sort, _old_sort in REORDER:
        bind.execute(
            _modules_table.update()
            .where(_modules_table.c.name == name)
            .values(sort=new_sort)
        )


def downgrade() -> None:
    bind = op.get_bind()
    for name, _new_sort, old_sort in REORDER:
        bind.execute(
            _modules_table.update()
            .where(_modules_table.c.name == name)
            .values(sort=old_sort)
        )
