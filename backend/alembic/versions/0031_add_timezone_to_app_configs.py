"""add app_configs.timezone (issue #47) - the live, admin-editable IANA
timezone name backing core/timezone.py::get_app_timezone(). Backfilled to
config.APP_TIMEZONE_STR (env APP_TIMEZONE, default "Asia/Jakarta") for the
existing singleton row so an upgrade never leaves it blank.

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core import config

revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("app_configs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "timezone",
                sa.String(length=64),
                nullable=False,
                server_default=config.APP_TIMEZONE_STR,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("app_configs") as batch_op:
        batch_op.drop_column("timezone")
