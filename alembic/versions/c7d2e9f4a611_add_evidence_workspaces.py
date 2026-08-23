"""add evidence workspaces

Revision ID: c7d2e9f4a611
Revises: b6f2d9e4a8c1
Create Date: 2026-08-23 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d2e9f4a611"
down_revision: Union[str, None] = "b6f2d9e4a8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_evidence_workspaces_user", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_workspaces"),
    )
    op.create_index(
        "ix_evidence_workspaces_user_updated",
        "evidence_workspaces",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "evidence_workspace_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["evidence_workspaces.id"],
            name="fk_ew_documents_workspace",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_ew_documents_document", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_workspace_documents"),
        sa.UniqueConstraint(
            "workspace_id",
            "document_id",
            name="uq_evidence_workspace_documents_workspace_document",
        ),
    )
    op.create_index(
        "ix_evidence_workspace_documents_document",
        "evidence_workspace_documents",
        ["document_id"],
        unique=False,
    )

    op.add_column("queries", sa.Column("workspace_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_queries_workspace",
        "queries",
        "evidence_workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_queries_workspace_created",
        "queries",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_queries_workspace_created", table_name="queries")
    op.drop_constraint("fk_queries_workspace", "queries", type_="foreignkey")
    op.drop_column("queries", "workspace_id")
    op.drop_index("ix_evidence_workspace_documents_document", table_name="evidence_workspace_documents")
    op.drop_table("evidence_workspace_documents")
    op.drop_index("ix_evidence_workspaces_user_updated", table_name="evidence_workspaces")
    op.drop_table("evidence_workspaces")
