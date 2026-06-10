"""phase 11 merchant portal dashboard

Revision ID: 20260609_0007
Revises: 20260513_0006
Create Date: 2026-06-09 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260609_0007"
down_revision: Union[str, None] = "20260513_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "fk_audit_logs_actor_id_internal_users",
            "audit_logs",
            type_="foreignkey",
        )

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'MERCHANT_USER'")
        op.execute("ALTER TYPE actor_type ADD VALUE IF NOT EXISTS 'MERCHANT'")
        merchant_user_role = postgresql.ENUM(
            "MERCHANT_ADMIN",
            "MERCHANT_VIEWER",
            name="merchant_user_role",
            create_type=False,
        )
        merchant_user_status = postgresql.ENUM(
            "ACTIVE",
            "INACTIVE",
            name="merchant_user_status",
            create_type=False,
        )
        merchant_user_role.create(bind, checkfirst=True)
        merchant_user_status.create(bind, checkfirst=True)
    else:
        merchant_user_role = sa.Enum("MERCHANT_ADMIN", "MERCHANT_VIEWER", name="merchant_user_role")
        merchant_user_status = sa.Enum("ACTIVE", "INACTIVE", name="merchant_user_status")

    op.create_table(
        "merchant_users",
        sa.Column("merchant_db_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", merchant_user_role, nullable=False),
        sa.Column("status", merchant_user_status, server_default="ACTIVE", nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("merchant_db_id", "email", name="uq_merchant_users_merchant_email"),
    )
    op.create_index("ix_merchant_users_merchant_db_id", "merchant_users", ["merchant_db_id"])
    op.create_index("ix_merchant_users_email", "merchant_users", ["email"])
    op.create_index(
        "ix_payment_transactions_merchant_created_at",
        "payment_transactions",
        ["merchant_db_id", "created_at"],
    )
    op.create_index(
        "ix_refund_transactions_merchant_created_at",
        "refund_transactions",
        ["merchant_db_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_events_merchant_created_at",
        "webhook_events",
        ["merchant_db_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_events_merchant_created_at", table_name="webhook_events")
    op.drop_index("ix_refund_transactions_merchant_created_at", table_name="refund_transactions")
    op.drop_index("ix_payment_transactions_merchant_created_at", table_name="payment_transactions")
    op.drop_index("ix_merchant_users_email", table_name="merchant_users")
    op.drop_index("ix_merchant_users_merchant_db_id", table_name="merchant_users")
    op.drop_table("merchant_users")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="merchant_user_status").drop(bind, checkfirst=True)
        postgresql.ENUM(name="merchant_user_role").drop(bind, checkfirst=True)
        op.create_foreign_key(
            "fk_audit_logs_actor_id_internal_users",
            "audit_logs",
            "internal_users",
            ["actor_id"],
            ["id"],
        )
