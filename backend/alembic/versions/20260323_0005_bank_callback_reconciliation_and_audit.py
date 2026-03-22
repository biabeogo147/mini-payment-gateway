"""bank callback reconciliation and audit

Revision ID: 20260323_0005
Revises: 20260323_0004
Create Date: 2026-03-23 01:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260323_0005"
down_revision = "20260323_0004"
branch_labels = None
depends_on = None


callback_source_type = postgresql.ENUM("BANK", "NAPAS", "SIMULATOR", "QR_PROVIDER", name="callback_source_type", create_type=False)
callback_type = postgresql.ENUM("PAYMENT_RESULT", "REFUND_RESULT", name="callback_type", create_type=False)
callback_processing_result = postgresql.ENUM("PROCESSED", "IGNORED", "FAILED", "PENDING_REVIEW", name="callback_processing_result", create_type=False)
entity_type = postgresql.ENUM("PAYMENT", "REFUND", "MERCHANT", "WEBHOOK_EVENT", "RECONCILIATION", name="entity_type", create_type=False)
reconciliation_status = postgresql.ENUM("MATCHED", "MISMATCHED", "PENDING_REVIEW", "RESOLVED", name="reconciliation_status", create_type=False)
actor_type = postgresql.ENUM("SYSTEM", "ADMIN", "OPS", name="actor_type", create_type=False)


def upgrade() -> None:
    op.create_table(
        "bank_callback_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_type", callback_source_type, nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("transaction_reference", sa.String(length=128), nullable=True),
        sa.Column("callback_type", callback_type, nullable=False),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_status", sa.String(length=64), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_result", callback_processing_result, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_bank_callback_logs"),
    )

    op.create_table(
        "reconciliation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_status", sa.String(length=64), nullable=False),
        sa.Column("external_status", sa.String(length=64), nullable=False),
        sa.Column("internal_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("external_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("match_result", reconciliation_status, nullable=False),
        sa.Column("mismatch_reason_code", sa.String(length=64), nullable=True),
        sa.Column("mismatch_reason_message", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by"], ["internal_users.id"], name="fk_reconciliation_records_reviewed_by_internal_users"),
        sa.PrimaryKeyConstraint("id", name="pk_reconciliation_records"),
    )
    op.create_index("ix_reconciliation_records_match_result", "reconciliation_records", ["match_result"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["internal_users.id"], name="fk_audit_logs_actor_id_internal_users"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_reconciliation_records_match_result", table_name="reconciliation_records")
    op.drop_table("reconciliation_records")
    op.drop_table("bank_callback_logs")
