from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MerchantStatus, MerchantUserRole, MerchantUserStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_user import MerchantUser
from app.schemas.ops_dashboard import MerchantCredentialDetailResponse, PaymentStatusChartPoint, RefundCountChartPoint, WebhookStatusChartPoint


def _serialize_datetime(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class MerchantPortalBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={
            datetime: _serialize_datetime,
            Decimal: lambda value: str(value),
        },
    )


class MerchantPortalUserResponse(MerchantPortalBaseModel):
    user_id: str
    merchant_id: str
    email: str
    full_name: str
    role: MerchantUserRole
    status: MerchantUserStatus
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: MerchantUser) -> "MerchantPortalUserResponse":
        return cls(
            user_id=str(user.id),
            merchant_id=user.merchant.merchant_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class MerchantPortalUserListResponse(MerchantPortalBaseModel):
    users: list[MerchantPortalUserResponse]


class MerchantPortalGeneratedPasswordResponse(MerchantPortalBaseModel):
    user: MerchantPortalUserResponse
    generated_password: str


class MerchantPortalAuthLoginRequest(MerchantPortalBaseModel):
    merchant_id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class MerchantPortalAuthChangePasswordRequest(MerchantPortalBaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class MerchantPortalAuthSessionResponse(MerchantPortalBaseModel):
    user: MerchantPortalUserResponse
    merchant_status: MerchantStatus

    @classmethod
    def from_user(cls, user: MerchantUser) -> "MerchantPortalAuthSessionResponse":
        return cls(
            user=MerchantPortalUserResponse.from_user(user),
            merchant_status=user.merchant.status,
        )


class MerchantPortalStatusResponse(MerchantPortalBaseModel):
    status: str


class CreateMerchantPortalUserRequest(MerchantPortalBaseModel):
    email: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: MerchantUserRole
    status: MerchantUserStatus = MerchantUserStatus.ACTIVE


class UpdateMerchantPortalUserRequest(MerchantPortalBaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: MerchantUserRole | None = None
    status: MerchantUserStatus | None = None


class MerchantPortalDashboardSummaryResponse(MerchantPortalBaseModel):
    payments_last_24h: int
    successful_payment_amount_last_24h: Decimal
    pending_payments: int
    refunds_last_24h: int
    open_webhook_events: int


class MerchantPortalPaymentAmountChartPoint(MerchantPortalBaseModel):
    date: date
    amount: Decimal


class MerchantPortalDashboardChartsResponse(MerchantPortalBaseModel):
    payment_status_by_day: list[PaymentStatusChartPoint]
    successful_payment_amount_by_day: list[MerchantPortalPaymentAmountChartPoint]
    refund_count_by_day: list[RefundCountChartPoint]
    webhook_status_by_day: list[WebhookStatusChartPoint]


class MerchantPortalAnalyticsRange(MerchantPortalBaseModel):
    days: int
    start_date: date
    end_date: date


class MerchantPortalAnalyticsTotals(MerchantPortalBaseModel):
    payment_count: int
    successful_payment_count: int
    successful_payment_amount: Decimal
    success_rate: float
    refund_count: int
    refunded_amount: Decimal
    webhook_count: int
    webhook_delivery_rate: float


class MerchantPortalPaymentAnalyticsPoint(MerchantPortalBaseModel):
    date: date
    pending: int
    success: int
    failed: int
    expired: int
    total: int
    successful_amount: Decimal
    success_rate: float


class MerchantPortalRefundAnalyticsPoint(MerchantPortalBaseModel):
    date: date
    pending: int
    refunded: int
    failed: int
    count: int
    amount: Decimal


class MerchantPortalWebhookAnalyticsPoint(MerchantPortalBaseModel):
    date: date
    pending: int
    delivered: int
    failed: int
    total: int
    delivery_rate: float


class MerchantPortalAnalyticsSeries(MerchantPortalBaseModel):
    payment_by_day: list[MerchantPortalPaymentAnalyticsPoint]
    refund_by_day: list[MerchantPortalRefundAnalyticsPoint]
    webhook_by_day: list[MerchantPortalWebhookAnalyticsPoint]


class MerchantPortalTopWebhookEventType(MerchantPortalBaseModel):
    event_type: str
    count: int
    pending: int
    failed: int


class MerchantPortalAnalyticsAttention(MerchantPortalBaseModel):
    failed_or_expired_payments: int
    refund_failures: int
    open_webhooks: int
    top_webhook_event_types: list[MerchantPortalTopWebhookEventType]


class MerchantPortalAnalyticsResponse(MerchantPortalBaseModel):
    range: MerchantPortalAnalyticsRange
    totals: MerchantPortalAnalyticsTotals
    series: MerchantPortalAnalyticsSeries
    attention: MerchantPortalAnalyticsAttention


class MerchantPortalProfileResponse(MerchantPortalBaseModel):
    merchant_id: str
    merchant_name: str
    legal_name: str | None = None
    contact_name: str | None = None
    contact_email: str
    contact_phone: str | None = None
    webhook_url: str | None = None
    allowed_ip_list: list[str] | None = None
    status: MerchantStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_merchant(cls, merchant: Merchant) -> "MerchantPortalProfileResponse":
        return cls(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            legal_name=merchant.legal_name,
            contact_name=merchant.contact_name,
            contact_email=merchant.contact_email,
            contact_phone=merchant.contact_phone,
            webhook_url=merchant.webhook_url,
            allowed_ip_list=merchant.allowed_ip_list,
            status=merchant.status,
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
        )


class MerchantPortalCredentialListResponse(MerchantPortalBaseModel):
    credentials: list[MerchantCredentialDetailResponse]

    @classmethod
    def from_credentials(
        cls,
        credentials: list[MerchantCredential],
    ) -> "MerchantPortalCredentialListResponse":
        return cls(
            credentials=[
                MerchantCredentialDetailResponse.from_credential(credential)
                for credential in credentials
            ]
        )
