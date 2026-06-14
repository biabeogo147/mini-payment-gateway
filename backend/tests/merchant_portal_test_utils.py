from datetime import datetime, timezone
from uuid import uuid4

from app.models.enums import MerchantStatus, MerchantUserRole, MerchantUserStatus
from app.models.merchant import Merchant
from app.models.merchant_user import MerchantUser


def make_merchant(
    *,
    merchant_id: str = "m_demo",
    merchant_name: str = "Demo Merchant",
    status: MerchantStatus = MerchantStatus.ACTIVE,
) -> Merchant:
    now = datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc)
    return Merchant(
        id=uuid4(),
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        contact_email=f"{merchant_id}@example.com",
        status=status,
        created_at=now,
        updated_at=now,
    )


def make_merchant_user(
    *,
    merchant: Merchant | None = None,
    role: MerchantUserRole = MerchantUserRole.MERCHANT_ADMIN,
    status: MerchantUserStatus = MerchantUserStatus.ACTIVE,
    email: str | None = None,
) -> MerchantUser:
    now = datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc)
    merchant = merchant or make_merchant()
    user = MerchantUser(
        id=uuid4(),
        merchant_db_id=merchant.id,
        email=email or f"{role.value.lower()}-{uuid4().hex[:8]}@example.com",
        full_name=f"{role.value.replace('_', ' ').title()} User",
        role=role,
        status=status,
        password_hash="pbkdf2_sha256$240000$testsalt$testdigest",
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    user.merchant = merchant
    return user


def override_current_merchant_user(app, user: MerchantUser) -> None:
    from app.controllers.deps import get_current_merchant_user

    def current_user_override() -> MerchantUser:
        return user

    app.dependency_overrides[get_current_merchant_user] = current_user_override
