"""add conversation fields to queries

Revision ID: b8e1f6c3a924
Revises: 4d2f9c1a7b21
Create Date: 2026-03-25 21:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8e1f6c3a924"
down_revision: Union[str, None] = "4d2f9c1a7b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("queries", sa.Column("conversation_id", sa.String(length=100), nullable=True))
    op.add_column("queries", sa.Column("turn_index", sa.Integer(), nullable=True))
    op.create_index(
        "ix_queries_user_conversation_turn",
        "queries",
        ["user_id", "conversation_id", "turn_index"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_queries_user_conversation_turn", table_name="queries")
    op.drop_column("queries", "turn_index")
    op.drop_column("queries", "conversation_id")
