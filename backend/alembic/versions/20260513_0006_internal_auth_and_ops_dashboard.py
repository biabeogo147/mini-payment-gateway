"""phase 10 internal auth and ops dashboard foundation

Revision ID: 20260513_0006
Revises: 20260323_0005
Create Date: 2026-05-13 19:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260513_0006"
down_revision: Union[str, None] = "20260323_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'INTERNAL_USER'")

    op.add_column("internal_users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column("internal_users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("internal_users", "last_login_at")
    op.drop_column("internal_users", "password_hash")
