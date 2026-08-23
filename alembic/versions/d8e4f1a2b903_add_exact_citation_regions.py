"""add exact citation regions

Revision ID: d8e4f1a2b903
Revises: c7d2e9f4a611
Create Date: 2026-08-23 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8e4f1a2b903"
down_revision: Union[str, None] = "c7d2e9f4a611"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("bbox_regions", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "bbox_regions")
