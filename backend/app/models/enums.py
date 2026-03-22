import enum


class InternalUserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    OPS = "OPS"


class InternalUserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MerchantStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class CredentialStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ROTATED = "ROTATED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class RefundStatus(str, enum.Enum):
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    REFUND_FAILED = "REFUND_FAILED"


class WebhookEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class DeliveryAttemptResult(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"
    PENDING_REVIEW = "PENDING_REVIEW"
    RESOLVED = "RESOLVED"


class CallbackSourceType(str, enum.Enum):
    BANK = "BANK"
    NAPAS = "NAPAS"
    SIMULATOR = "SIMULATOR"
    QR_PROVIDER = "QR_PROVIDER"


class CallbackType(str, enum.Enum):
    PAYMENT_RESULT = "PAYMENT_RESULT"
    REFUND_RESULT = "REFUND_RESULT"


class CallbackProcessingResult(str, enum.Enum):
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
    PENDING_REVIEW = "PENDING_REVIEW"


class EntityType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    MERCHANT = "MERCHANT"
    WEBHOOK_EVENT = "WEBHOOK_EVENT"
    RECONCILIATION = "RECONCILIATION"


class ActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    ADMIN = "ADMIN"
    OPS = "OPS"
