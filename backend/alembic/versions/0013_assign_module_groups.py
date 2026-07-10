"""assign existing modules to their module groups (Inventory / Master /
Application Configuration)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (module name, group name)
MODULE_GROUP_ASSIGNMENTS = [
    ("stock_in", "Inventory"),
    ("stock_out", "Inventory"),
    ("stock_browse", "Inventory"),
    ("usage_report", "Inventory"),
    ("master_location", "Master"),
    ("master_material", "Master"),
    ("master_department", "Master"),
    ("master_supplier", "Master"),
    ("ap_master_user", "Application Configuration"),
    ("ap_module", "Application Configuration"),
]

_module_groups_table = sa.table(
    "module_groups",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)

_modules_table = sa.table(
    "modules",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("module_group_id", sa.Integer),
)


def _group_ids_by_name(bind) -> dict:
    rows = bind.execute(sa.select(_module_groups_table.c.id, _module_groups_table.c.name)).all()
    return {name: group_id for group_id, name in rows}


def upgrade() -> None:
    bind = op.get_bind()
    group_ids = _group_ids_by_name(bind)

    for module_name, group_name in MODULE_GROUP_ASSIGNMENTS:
        group_id = group_ids.get(group_name)
        if group_id is None:
            continue
        bind.execute(
            _modules_table.update()
            .where(_modules_table.c.name == module_name)
            .values(module_group_id=group_id)
        )


def downgrade() -> None:
    bind = op.get_bind()
    module_names = [name for name, _ in MODULE_GROUP_ASSIGNMENTS]
    bind.execute(
        _modules_table.update()
        .where(_modules_table.c.name.in_(module_names))
        .values(module_group_id=None)
    )
