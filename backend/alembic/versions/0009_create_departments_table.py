"""create departments table and link users.department_id,
stock_out_headers.department_id

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_departments_code", "departments", ["code"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_users_department_id", ["department_id"])
        batch_op.create_foreign_key(
            "fk_users_department_id_departments", "departments", ["department_id"], ["id"]
        )

    with op.batch_alter_table("stock_out_headers") as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_stock_out_headers_department_id", ["department_id"])
        batch_op.create_foreign_key(
            "fk_stock_out_headers_department_id_departments",
            "departments",
            ["department_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("stock_out_headers") as batch_op:
        batch_op.drop_constraint(
            "fk_stock_out_headers_department_id_departments", type_="foreignkey"
        )
        batch_op.drop_index("ix_stock_out_headers_department_id")
        batch_op.drop_column("department_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_department_id_departments", type_="foreignkey")
        batch_op.drop_index("ix_users_department_id")
        batch_op.drop_column("department_id")

    op.drop_table("departments")
