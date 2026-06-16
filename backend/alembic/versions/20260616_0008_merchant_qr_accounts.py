"""merchant qr accounts

Revision ID: 20260616_0008
Revises: 20260609_0007
Create Date: 2026-06-16 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260616_0008"
down_revision: Union[str, None] = "20260609_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'MERCHANT_QR_ACCOUNT'")
        qr_provider = postgresql.ENUM("VIETQR", name="qr_provider", create_type=False)
        merchant_qr_account_status = postgresql.ENUM(
            "ACTIVE",
            "INACTIVE",
            name="merchant_qr_account_status",
            create_type=False,
        )
        qr_provider.create(bind, checkfirst=True)
        merchant_qr_account_status.create(bind, checkfirst=True)
    else:
        qr_provider = sa.Enum("VIETQR", name="qr_provider")
        merchant_qr_account_status = sa.Enum("ACTIVE", "INACTIVE", name="merchant_qr_account_status")

    op.create_table(
        "merchant_qr_accounts",
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", qr_provider, server_default="VIETQR", nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=False),
        sa.Column("bank_bin", sa.String(length=16), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("template", sa.String(length=32), server_default="compact", nullable=False),
        sa.Column("status", merchant_qr_account_status, server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["merchant_db_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_qr_accounts_merchant_db_id", "merchant_qr_accounts", ["merchant_db_id"])
    op.create_index(
        "ux_merchant_qr_accounts_active_provider_per_merchant",
        "merchant_qr_accounts",
        ["merchant_db_id", "provider"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.add_column("payment_transactions", sa.Column("qr_reference", sa.String(length=13), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_transactions", "qr_reference")
    op.drop_index("ux_merchant_qr_accounts_active_provider_per_merchant", table_name="merchant_qr_accounts")
    op.drop_index("ix_merchant_qr_accounts_merchant_db_id", table_name="merchant_qr_accounts")
    op.drop_table("merchant_qr_accounts")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="merchant_qr_account_status").drop(bind, checkfirst=True)
        postgresql.ENUM(name="qr_provider").drop(bind, checkfirst=True)
