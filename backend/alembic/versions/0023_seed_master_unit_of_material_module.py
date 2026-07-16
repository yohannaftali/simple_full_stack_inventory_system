"""seed the master_unit_of_material module and grant it to the default superuser

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core import config

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ADMIN_USERNAME = config.ADMIN_USERNAME
GROUP_NAME = "Master"

# (name, label, icon, description, sort)
DEFAULT_MODULES = [
    (
        "master_unit_of_material",
        "Units of Material",
        "straighten",
        "Manage units of material",
        14,
    ),
]

_users_table = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("username", sa.String),
)

_module_groups_table = sa.table(
    "module_groups",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
)

_modules_table = sa.table(
    "modules",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("label", sa.String),
    sa.column("icon", sa.String),
    sa.column("mdi", sa.String),
    sa.column("description", sa.String),
    sa.column("sort", sa.Integer),
    sa.column("module_type", sa.SmallInteger),
    sa.column("module_group_id", sa.Integer),
)

_permissions_table = sa.table(
    "user_module_permissions",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("module_id", sa.Integer),
)


def upgrade() -> None:
    bind = op.get_bind()

    admin_id = bind.execute(
        sa.select(_users_table.c.id).where(
            _users_table.c.username == DEFAULT_ADMIN_USERNAME
        )
    ).scalar()

    group_id = bind.execute(
        sa.select(_module_groups_table.c.id).where(
            _module_groups_table.c.name == GROUP_NAME
        )
    ).scalar()

    for name, label, icon, description, sort in DEFAULT_MODULES:
        module_id = bind.execute(
            sa.select(_modules_table.c.id).where(_modules_table.c.name == name)
        ).scalar()

        if module_id is None:
            bind.execute(
                _modules_table.insert().values(
                    name=name,
                    label=label,
                    icon=icon,
                    mdi="chevron_right",
                    description=description,
                    sort=sort,
                    module_type=0,
                    module_group_id=group_id,
                )
            )
            module_id = bind.execute(
                sa.select(_modules_table.c.id).where(_modules_table.c.name == name)
            ).scalar()

        if admin_id is None:
            continue

        already_granted = bind.execute(
            sa.select(_permissions_table.c.id).where(
                _permissions_table.c.user_id == admin_id,
                _permissions_table.c.module_id == module_id,
            )
        ).first()
        if already_granted is None:
            bind.execute(
                _permissions_table.insert().values(
                    user_id=admin_id, module_id=module_id
                )
            )


def downgrade() -> None:
    bind = op.get_bind()

    module_names = [name for name, *_ in DEFAULT_MODULES]
    module_ids = bind.execute(
        sa.select(_modules_table.c.id).where(_modules_table.c.name.in_(module_names))
    ).scalars().all()

    if module_ids:
        bind.execute(
            _permissions_table.delete().where(
                _permissions_table.c.module_id.in_(module_ids)
            )
        )
        bind.execute(_modules_table.delete().where(_modules_table.c.id.in_(module_ids)))
