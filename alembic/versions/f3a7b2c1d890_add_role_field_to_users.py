"""add role field to users

Revision ID: f3a7b2c1d890
Revises: e1f4c2b9a017
Create Date: 2026-08-07 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a7b2c1d890"
down_revision: Union[str, None] = "e1f4c2b9a017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))
    # Set default for existing users
    op.execute("UPDATE users SET role = 'member' WHERE role IS NULL")
    op.alter_column("users", "role", nullable=False, server_default="member")


def downgrade() -> None:
    op.drop_column("users", "role")
