"""remove podcast fields from documents

Revision ID: 4d2f9c1a7b21
Revises: 962463129f99
Create Date: 2026-03-24 20:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d2f9c1a7b21"
down_revision: Union[str, None] = "962463129f99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("documents", "podcast_duration")
    op.drop_column("documents", "podcast_s3_key")
    op.drop_column("documents", "has_podcast")


def downgrade() -> None:
    op.add_column("documents", sa.Column("has_podcast", sa.Boolean(), nullable=True))
    op.add_column("documents", sa.Column("podcast_s3_key", sa.String(length=500), nullable=True))
    op.add_column("documents", sa.Column("podcast_duration", sa.Float(), nullable=True))
