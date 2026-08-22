"""add evidence gate audit tables

Revision ID: a4d8e7f1c2b3
Revises: f3a7b2c1d890
Create Date: 2026-08-22 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4d8e7f1c2b3"
down_revision: Union[str, None] = "f3a7b2c1d890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_gate_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("query_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default=sa.text("'shadow'")),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=True),
        sa.Column("candidate_answer_sha256", sa.String(length=64), nullable=False),
        sa.Column("delivered_answer_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("verifier_model", sa.String(length=100), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("claim_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("supported_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsupported_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unverified_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('shadow', 'annotate', 'enforce')",
            name="ck_evidence_gate_runs_mode",
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'degraded', 'abstained')",
            name="ck_evidence_gate_runs_status",
        ),
        sa.CheckConstraint(
            "action IS NULL OR action IN ('allow', 'annotate', 'abstain')",
            name="ck_evidence_gate_runs_action",
        ),
        sa.ForeignKeyConstraint(
            ["query_id"], ["queries.id"], name="fk_evidence_gate_runs_query_id_queries", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_evidence_gate_runs_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_gate_runs"),
        sa.UniqueConstraint(
            "query_id", "policy_version", "attempt",
            name="uq_evidence_gate_runs_query_policy_attempt",
        ),
    )
    op.create_index(
        "ix_evidence_gate_runs_user_created",
        "evidence_gate_runs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_evidence_gate_runs_query_created",
        "evidence_gate_runs",
        ["query_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "evidence_gate_claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("gate_run_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_sha256", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("supporting_source_numbers", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('supported', 'unsupported', 'unverified')",
            name="ck_evidence_gate_claims_verdict",
        ),
        sa.ForeignKeyConstraint(
            ["gate_run_id"],
            ["evidence_gate_runs.id"],
            name="fk_evidence_gate_claims_gate_run_id_evidence_gate_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_gate_claims"),
        sa.UniqueConstraint("gate_run_id", "ordinal", name="uq_evidence_gate_claims_run_ordinal"),
    )
    op.create_index(
        "ix_evidence_gate_claims_run_verdict",
        "evidence_gate_claims",
        ["gate_run_id", "verdict"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_gate_claims_run_verdict", table_name="evidence_gate_claims")
    op.drop_table("evidence_gate_claims")
    op.drop_index("ix_evidence_gate_runs_query_created", table_name="evidence_gate_runs")
    op.drop_index("ix_evidence_gate_runs_user_created", table_name="evidence_gate_runs")
    op.drop_table("evidence_gate_runs")
