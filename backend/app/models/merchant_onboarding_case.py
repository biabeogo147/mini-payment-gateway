from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import OnboardingCaseStatus


class MerchantOnboardingCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    What this model means:
    Single onboarding and review record for a merchant in the MVP.

    Field meanings:
    - id: internal UUID primary key.
    - merchant_db_id: owned merchant internal UUID.
    - status: onboarding review lifecycle status.
    - domain_or_app_name: merchant integration system label.
    - submitted_profile_json: submitted onboarding profile snapshot.
    - documents_json: submitted legal/supporting documents metadata.
    - review_checks_json: reviewer checks and outcomes.
    - decision_note: reviewer note for approval or rejection.
    - reviewed_by/reviewed_at: final reviewer and decision timestamp.
    - created_at/updated_at: record timestamps.
    """

    __tablename__ = "merchant_onboarding_cases"
    __table_args__ = (
        UniqueConstraint("merchant_db_id", name="uq_merchant_onboarding_cases_merchant_db_id"),
    )

    merchant_db_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", name="fk_onboarding_cases_merchant"),
        nullable=False,
    )
    status: Mapped[OnboardingCaseStatus] = mapped_column(
        Enum(OnboardingCaseStatus, name="onboarding_case_status"),
        nullable=False,
        default=OnboardingCaseStatus.DRAFT,
        server_default=OnboardingCaseStatus.DRAFT.value,
    )
    domain_or_app_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_profile_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    documents_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    review_checks_json: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("internal_users.id", name="fk_onboarding_cases_reviewed_by"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
