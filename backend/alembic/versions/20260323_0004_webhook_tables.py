"""webhook tables

Revision ID: 20260323_0004
Revises: 20260323_0003
Create Date: 2026-03-23 01:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260323_0004"
down_revision = "20260323_0003"
branch_labels = None
depends_on = None


entity_type = postgresql.ENUM(
    "PAYMENT",
    "REFUND",
    "MERCHANT",
    "MERCHANT_CREDENTIAL",
    "ONBOARDING_CASE",
    "WEBHOOK_EVENT",
    "RECONCILIATION",
    name="entity_type",
    create_type=False,
)
webhook_event_status = postgresql.ENUM("PENDING", "DELIVERED", "FAILED", name="webhook_event_status", create_type=False)
delivery_attempt_result = postgresql.ENUM("SUCCESS", "FAILED", "TIMEOUT", "NETWORK_ERROR", name="delivery_attempt_result", create_type=False)


def upgrade() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("status", webhook_event_status, server_default="PENDING", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_webhook_events_attempt_count_non_negative"),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_webhook_events_merchant"),
        sa.PrimaryKeyConstraint("id", name="pk_webhook_events"),
        sa.UniqueConstraint("event_id", name="uq_webhook_events_event_id"),
    )
    op.create_index("ix_webhook_events_merchant_status_retry", "webhook_events", ["merchant_db_id", "status", "next_retry_at"], unique=False)

    op.create_table(
        "webhook_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("webhook_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("request_headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_body_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body_snippet", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", delivery_attempt_result, nullable=False),
        sa.ForeignKeyConstraint(["webhook_event_id"], ["webhook_events.id"], name="fk_webhook_attempts_event"),
        sa.PrimaryKeyConstraint("id", name="pk_webhook_delivery_attempts"),
    )
    op.create_index("ix_webhook_delivery_attempts_webhook_event_id", "webhook_delivery_attempts", ["webhook_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_attempts_webhook_event_id", table_name="webhook_delivery_attempts")
    op.drop_table("webhook_delivery_attempts")
    op.drop_index("ix_webhook_events_merchant_status_retry", table_name="webhook_events")
    op.drop_table("webhook_events")
