"""base enums and merchant tables

Revision ID: 20260323_0001
Revises:
Create Date: 2026-03-23 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260323_0001"
down_revision = None
branch_labels = None
depends_on = None


internal_user_role = postgresql.ENUM("ADMIN", "OPS", name="internal_user_role", create_type=False)
internal_user_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="internal_user_status", create_type=False)
merchant_status = postgresql.ENUM("PENDING_REVIEW", "ACTIVE", "REJECTED", "SUSPENDED", "DISABLED", name="merchant_status", create_type=False)
credential_status = postgresql.ENUM("ACTIVE", "INACTIVE", "ROTATED", name="credential_status", create_type=False)
payment_status = postgresql.ENUM("PENDING", "SUCCESS", "FAILED", "EXPIRED", name="payment_status", create_type=False)
refund_status = postgresql.ENUM("REFUND_PENDING", "REFUNDED", "REFUND_FAILED", name="refund_status", create_type=False)
onboarding_case_status = postgresql.ENUM("DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED", name="onboarding_case_status", create_type=False)
webhook_event_status = postgresql.ENUM("PENDING", "DELIVERED", "FAILED", name="webhook_event_status", create_type=False)
delivery_attempt_result = postgresql.ENUM("SUCCESS", "FAILED", "TIMEOUT", "NETWORK_ERROR", name="delivery_attempt_result", create_type=False)
reconciliation_status = postgresql.ENUM("MATCHED", "MISMATCHED", "PENDING_REVIEW", "RESOLVED", name="reconciliation_status", create_type=False)
callback_source_type = postgresql.ENUM("BANK", "NAPAS", "SIMULATOR", "QR_PROVIDER", name="callback_source_type", create_type=False)
callback_type = postgresql.ENUM("PAYMENT_RESULT", "REFUND_RESULT", name="callback_type", create_type=False)
callback_processing_result = postgresql.ENUM("PROCESSED", "IGNORED", "FAILED", "PENDING_REVIEW", name="callback_processing_result", create_type=False)
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
actor_type = postgresql.ENUM("SYSTEM", "ADMIN", "OPS", name="actor_type", create_type=False)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    for enum_type in (
        internal_user_role,
        internal_user_status,
        merchant_status,
        credential_status,
        payment_status,
        refund_status,
        onboarding_case_status,
        webhook_event_status,
        delivery_attempt_result,
        reconciliation_status,
        callback_source_type,
        callback_type,
        callback_processing_result,
        entity_type,
        actor_type,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "internal_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", internal_user_role, nullable=False),
        sa.Column("status", internal_user_status, server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_internal_users"),
        sa.UniqueConstraint("email", name="uq_internal_users_email"),
    )

    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("allowed_ip_list", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("status", merchant_status, server_default="PENDING_REVIEW", nullable=False),
        sa.Column("settlement_account_name", sa.String(length=255), nullable=True),
        sa.Column("settlement_account_number", sa.String(length=64), nullable=True),
        sa.Column("settlement_bank_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_merchants"),
        sa.UniqueConstraint("merchant_id", name="uq_merchants_merchant_id"),
    )
    op.create_index("ix_merchants_merchant_id", "merchants", ["merchant_id"], unique=False)

    op.create_table(
        "merchant_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_key", sa.String(length=128), nullable=False),
        sa.Column("secret_key_encrypted", sa.Text(), nullable=False),
        sa.Column("secret_key_last4", sa.String(length=4), nullable=False),
        sa.Column("status", credential_status, server_default="ACTIVE", nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_merchant_credentials_merchant_db_id_merchants"),
        sa.PrimaryKeyConstraint("id", name="pk_merchant_credentials"),
        sa.UniqueConstraint("access_key", name="uq_merchant_credentials_access_key"),
    )
    op.create_index("ix_merchant_credentials_merchant_db_id", "merchant_credentials", ["merchant_db_id"], unique=False)
    op.create_index(
        "ux_merchant_credentials_active_per_merchant",
        "merchant_credentials",
        ["merchant_db_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "merchant_onboarding_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", onboarding_case_status, server_default="DRAFT", nullable=False),
        sa.Column("domain_or_app_name", sa.String(length=255), nullable=True),
        sa.Column("submitted_profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("documents_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("review_checks_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_onboarding_cases_merchant"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["internal_users.id"], name="fk_onboarding_cases_reviewed_by"),
        sa.PrimaryKeyConstraint("id", name="pk_merchant_onboarding_cases"),
        sa.UniqueConstraint("merchant_db_id", name="uq_merchant_onboarding_cases_merchant_db_id"),
    )


def downgrade() -> None:
    op.drop_table("merchant_onboarding_cases")
    op.drop_index("ux_merchant_credentials_active_per_merchant", table_name="merchant_credentials")
    op.drop_index("ix_merchant_credentials_merchant_db_id", table_name="merchant_credentials")
    op.drop_table("merchant_credentials")
    op.drop_index("ix_merchants_merchant_id", table_name="merchants")
    op.drop_table("merchants")
    op.drop_table("internal_users")

    for enum_type in (
        actor_type,
        entity_type,
        callback_processing_result,
        callback_type,
        callback_source_type,
        reconciliation_status,
        delivery_attempt_result,
        webhook_event_status,
        onboarding_case_status,
        refund_status,
        payment_status,
        credential_status,
        merchant_status,
        internal_user_status,
        internal_user_role,
    ):
        enum_type.drop(op.get_bind(), checkfirst=True)
