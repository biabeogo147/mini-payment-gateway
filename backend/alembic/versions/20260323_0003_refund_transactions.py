"""refund transactions

Revision ID: 20260323_0003
Revises: 20260323_0002
Create Date: 2026-03-23 01:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260323_0003"
down_revision = "20260323_0002"
branch_labels = None
depends_on = None


refund_status = postgresql.ENUM("REFUND_PENDING", "REFUNDED", "REFUND_FAILED", name="refund_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "refund_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("refund_transaction_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refund_id", sa.String(length=128), nullable=False),
        sa.Column("refund_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", refund_status, server_default="REFUND_PENDING", nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason_code", sa.String(length=64), nullable=True),
        sa.Column("failed_reason_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"], name="fk_refunds_merchant"),
        sa.ForeignKeyConstraint(["payment_transaction_id"], ["payment_transactions.id"], name="fk_refunds_payment"),
        sa.PrimaryKeyConstraint("id", name="pk_refund_transactions"),
        sa.UniqueConstraint("merchant_db_id", "refund_id", name="uq_refund_transactions_merchant_refund"),
        sa.UniqueConstraint("refund_transaction_id", name="uq_refund_transactions_refund_transaction_id"),
    )
    op.create_index("ix_refund_transactions_refund_id", "refund_transactions", ["refund_id"], unique=False)
    op.create_index("ix_refund_transactions_payment_transaction_id", "refund_transactions", ["payment_transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_refund_transactions_payment_transaction_id", table_name="refund_transactions")
    op.drop_index("ix_refund_transactions_refund_id", table_name="refund_transactions")
    op.drop_table("refund_transactions")
