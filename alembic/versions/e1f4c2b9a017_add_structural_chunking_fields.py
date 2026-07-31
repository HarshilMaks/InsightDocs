"""add structural chunking fields to document_chunks

Revision ID: e1f4c2b9a017
Revises: caacedd57fb8
Create Date: 2026-07-31 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f4c2b9a017"
down_revision: Union[str, None] = "caacedd57fb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("section_title", sa.String(length=500), nullable=True))
    op.add_column("document_chunks", sa.Column("chunk_type", sa.String(length=20), nullable=True))
    op.add_column("document_chunks", sa.Column("parent_chunk_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_chunks_parent_chunk_id",
        "document_chunks",
        "document_chunks",
        ["parent_chunk_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chunks_parent", "document_chunks", ["parent_chunk_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chunks_parent", table_name="document_chunks")
    op.drop_constraint("fk_chunks_parent_chunk_id", "document_chunks", type_="foreignkey")
    op.drop_column("document_chunks", "parent_chunk_id")
    op.drop_column("document_chunks", "chunk_type")
    op.drop_column("document_chunks", "section_title")
