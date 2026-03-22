"""order references and payment transactions

Revision ID: 20260323_0002
Revises: 20260323_0001
Create Date: 2026-03-23 01:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260323_0002"
down_revision = "20260323_0001"
branch_labels = None
depends_on = None


payment_status = postgresql.ENUM("PENDING", "SUCCESS", "FAILED", "EXPIRED", name="payment_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "order_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=False),
        sa.Column("order_status_snapshot", sa.String(length=64), nullable=True),
        sa.Column("latest_payment_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_order_references_merchant_db_id_merchants"),
        sa.PrimaryKeyConstraint("id", name="pk_order_references"),
        sa.UniqueConstraint("merchant_db_id", "order_id", name="uq_order_references_merchant_order"),
    )
    op.create_index("ix_order_references_merchant_db_id", "order_references", ["merchant_db_id"], unique=False)

    op.create_table(
        "payment_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="VND", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", payment_status, server_default="PENDING", nullable=False),
        sa.Column("qr_content", sa.Text(), nullable=False),
        sa.Column("qr_image_url", sa.Text(), nullable=True),
        sa.Column("qr_image_base64", sa.Text(), nullable=True),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason_code", sa.String(length=64), nullable=True),
        sa.Column("failed_reason_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_payment_transactions_merchant_db_id_merchants"),
        sa.ForeignKeyConstraint(["order_reference_id"], ["order_references.id"], name="fk_payments_order_ref"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_transactions"),
        sa.UniqueConstraint("transaction_id", name="uq_payment_transactions_transaction_id"),
    )
    op.create_index("ix_payment_transactions_transaction_id", "payment_transactions", ["transaction_id"], unique=False)
    op.create_index("ix_payment_transactions_merchant_order", "payment_transactions", ["merchant_db_id", "order_id"], unique=False)
    op.create_index(
        "ux_payment_transactions_active_order",
        "payment_transactions",
        ["merchant_db_id", "order_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_foreign_key(
        "fk_order_references_latest_payment_transaction_id",
        "order_references",
        "payment_transactions",
        ["latest_payment_transaction_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_references_latest_payment_transaction_id", "order_references", type_="foreignkey")
    op.drop_index("ux_payment_transactions_active_order", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_merchant_order", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_transaction_id", table_name="payment_transactions")
    op.drop_table("payment_transactions")
    op.drop_index("ix_order_references_merchant_db_id", table_name="order_references")
    op.drop_table("order_references")
