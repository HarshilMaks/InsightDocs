"""add evidence gate review state

Revision ID: b6f2d9e4a8c1
Revises: a4d8e7f1c2b3
Create Date: 2026-08-22 17:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6f2d9e4a8c1"
down_revision: Union[str, None] = "a4d8e7f1c2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evidence_gate_runs",
        sa.Column(
            "review_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.add_column(
        "evidence_gate_runs",
        sa.Column(
            "review_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "evidence_gate_runs",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_evidence_gate_runs_review_status",
        "evidence_gate_runs",
        "review_status IN ('pending', 'accepted', 'rejected')",
    )
    op.create_index(
        "ix_evidence_gate_runs_user_review_created",
        "evidence_gate_runs",
        ["user_id", "review_status", "created_at"],
        unique=False,
    )

    op.create_table(
        "evidence_gate_review_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("gate_run_id", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column("result_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('accepted', 'rejected')",
            name="ck_evidence_gate_review_decisions_decision",
        ),
        sa.ForeignKeyConstraint(
            ["gate_run_id"],
            ["evidence_gate_runs.id"],
            name="fk_evidence_gate_review_decisions_gate_run_id_evidence_gate_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name="fk_evidence_gate_review_decisions_reviewer_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_gate_review_decisions"),
        sa.UniqueConstraint(
            "gate_run_id", "result_version",
            name="uq_evidence_gate_review_decisions_run_result_version",
        ),
    )
    op.create_index(
        "ix_evidence_gate_review_decisions_run_created",
        "evidence_gate_review_decisions",
        ["gate_run_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_gate_review_decisions_run_created",
        table_name="evidence_gate_review_decisions",
    )
    op.drop_table("evidence_gate_review_decisions")
    op.drop_index("ix_evidence_gate_runs_user_review_created", table_name="evidence_gate_runs")
    op.drop_constraint(
        "ck_evidence_gate_runs_review_status",
        "evidence_gate_runs",
        type_="check",
    )
    op.drop_column("evidence_gate_runs", "reviewed_at")
    op.drop_column("evidence_gate_runs", "review_version")
    op.drop_column("evidence_gate_runs", "review_status")
