"""seed default superuser

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core import config
from core.security import hash_password

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bootstrap-only credentials, sourced from ADMIN_USERNAME/ADMIN_PASSWORD/
# ADMIN_TOTP_SECRET in .env (see core/config.py) — falls back to the
# original hardcoded dev defaults if unset. Change the password after
# first login.
DEFAULT_ADMIN_USERNAME = config.ADMIN_USERNAME
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = config.ADMIN_PASSWORD
DEFAULT_ADMIN_TOTP_SECRET = config.ADMIN_TOTP_SECRET

_users_table = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("username", sa.String),
    sa.column("password", sa.String),
    sa.column("email", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("is_superuser", sa.Boolean),
    sa.column("totp_secret", sa.String),
)


def upgrade() -> None:
    bind = op.get_bind()

    existing = bind.execute(
        sa.select(_users_table.c.id).where(
            _users_table.c.username == DEFAULT_ADMIN_USERNAME
        )
    ).first()
    if existing is not None:
        return

    bind.execute(
        _users_table.insert().values(
            username=DEFAULT_ADMIN_USERNAME,
            password=hash_password(DEFAULT_ADMIN_PASSWORD),
            email=DEFAULT_ADMIN_EMAIL,
            is_active=True,
            is_superuser=True,
            totp_secret=DEFAULT_ADMIN_TOTP_SECRET,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        _users_table.delete().where(_users_table.c.username == DEFAULT_ADMIN_USERNAME)
    )
