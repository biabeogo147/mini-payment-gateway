import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4


class MerchantOpsServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.models.enums import ActorType
        from app.schemas.ops import OpsActorContext

        self.now = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
        self.actor_id = uuid4()
        self.actor = OpsActorContext(
            actor_type=ActorType.OPS,
            actor_id=self.actor_id,
            reason="Ops reviewed the change.",
        )

    def test_create_merchant_creates_pending_merchant_and_audit(self) -> None:
        from app.models.enums import EntityType, MerchantStatus
        from app.services.merchant_ops_service import create_merchant

        db = _FakeDb()
        store = _MerchantOpsStore()

        with store.patched_repositories():
            response = create_merchant(db, _create_merchant_request(self.actor), self.actor, now=self.now)

        self.assertTrue(db.committed)
        self.assertEqual(response.merchant_id, "m_demo")
        self.assertEqual(response.status, MerchantStatus.PENDING_REVIEW)
        self.assertEqual(store.merchants[0].status, MerchantStatus.PENDING_REVIEW)
        audit = db.audit_logs[0]
        self.assertEqual(audit.event_type, "MERCHANT_CREATED")
        self.assertEqual(audit.entity_type, EntityType.MERCHANT)
        self.assertEqual(audit.actor_id, self.actor_id)
        self.assertEqual(audit.after_state_json["merchant_id"], "m_demo")

    def test_create_merchant_rejects_duplicate_public_id(self) -> None:
        from app.core.errors import AppError
        from app.services.merchant_ops_service import create_merchant

        existing = _merchant(merchant_id="m_demo")
        store = _MerchantOpsStore(merchants=[existing])

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                create_merchant(_FakeDb(), _create_merchant_request(self.actor), self.actor, now=self.now)

        self.assertEqual(error.exception.error_code, "MERCHANT_ALREADY_EXISTS")
        self.assertEqual(error.exception.status_code, 409)

    def test_submit_onboarding_case_creates_updates_and_rejects_final_cases(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import EntityType, OnboardingCaseStatus
        from app.services.merchant_ops_service import submit_onboarding_case

        merchant = _merchant()
        db = _FakeDb()
        store = _MerchantOpsStore(merchants=[merchant])

        with store.patched_repositories():
            created = submit_onboarding_case(
                db,
                "m_demo",
                _submit_onboarding_request(self.actor, domain="Demo Shop"),
                self.actor,
                now=self.now,
            )

        self.assertTrue(db.committed)
        self.assertEqual(created.status, OnboardingCaseStatus.PENDING_REVIEW)
        self.assertEqual(store.onboarding_cases[0].domain_or_app_name, "Demo Shop")
        self.assertEqual(db.audit_logs[0].event_type, "ONBOARDING_CASE_SUBMITTED")
        self.assertEqual(db.audit_logs[0].entity_type, EntityType.ONBOARDING_CASE)

        db = _FakeDb()
        with store.patched_repositories():
            updated = submit_onboarding_case(
                db,
                "m_demo",
                _submit_onboarding_request(self.actor, domain="Updated Shop"),
                self.actor,
                now=self.now,
            )

        self.assertEqual(updated.status, OnboardingCaseStatus.PENDING_REVIEW)
        self.assertEqual(store.onboarding_cases[0].domain_or_app_name, "Updated Shop")

        store.onboarding_cases[0].status = OnboardingCaseStatus.APPROVED
        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                submit_onboarding_case(
                    _FakeDb(),
                    "m_demo",
                    _submit_onboarding_request(self.actor),
                    self.actor,
                    now=self.now,
                )

        self.assertEqual(error.exception.error_code, "ONBOARDING_CASE_FINAL")
        self.assertEqual(error.exception.status_code, 409)

    def test_approve_and_reject_onboarding_case_record_decision_fields_and_audit(self) -> None:
        from app.models.enums import OnboardingCaseStatus
        from app.services.merchant_ops_service import approve_onboarding_case, reject_onboarding_case

        merchant = _merchant()
        approved_case = _onboarding_case(merchant.id, status=OnboardingCaseStatus.PENDING_REVIEW)
        db = _FakeDb()
        store = _MerchantOpsStore(merchants=[merchant], onboarding_cases=[approved_case])

        with store.patched_repositories():
            response = approve_onboarding_case(
                db,
                "m_demo",
                _review_onboarding_request(self.actor, "Documents verified."),
                self.actor,
                now=self.now,
            )

        self.assertEqual(response.status, OnboardingCaseStatus.APPROVED)
        self.assertEqual(approved_case.reviewed_by, self.actor_id)
        self.assertEqual(approved_case.reviewed_at, self.now)
        self.assertEqual(approved_case.decision_note, "Documents verified.")
        self.assertEqual(db.audit_logs[0].event_type, "ONBOARDING_CASE_APPROVED")

        rejected_case = _onboarding_case(merchant.id, status=OnboardingCaseStatus.PENDING_REVIEW)
        db = _FakeDb()
        store = _MerchantOpsStore(merchants=[merchant], onboarding_cases=[rejected_case])

        with store.patched_repositories():
            response = reject_onboarding_case(
                db,
                "m_demo",
                _review_onboarding_request(self.actor, "Risk policy mismatch."),
                self.actor,
                now=self.now,
            )

        self.assertEqual(response.status, OnboardingCaseStatus.REJECTED)
        self.assertEqual(rejected_case.reviewed_by, self.actor_id)
        self.assertEqual(rejected_case.decision_note, "Risk policy mismatch.")
        self.assertEqual(db.audit_logs[0].event_type, "ONBOARDING_CASE_REJECTED")

    def test_create_credential_requires_merchant_and_single_active_credential(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import EntityType
        from app.services.merchant_ops_service import create_credential

        merchant = _merchant()
        db = _FakeDb()
        store = _MerchantOpsStore(merchants=[merchant])

        with store.patched_repositories():
            response = create_credential(
                db,
                "m_demo",
                _create_credential_request(self.actor, access_key="ak_new", secret_key="plain-secret"),
                self.actor,
                now=self.now,
            )

        credential = store.credentials[0]
        self.assertTrue(db.committed)
        self.assertEqual(response.access_key, "ak_new")
        self.assertEqual(response.secret_key_last4, "cret")
        self.assertFalse(hasattr(response, "secret_key"))
        self.assertEqual(credential.secret_key_encrypted, "plain-secret")
        self.assertEqual(credential.secret_key_last4, "cret")
        audit = db.audit_logs[0]
        self.assertEqual(audit.event_type, "CREDENTIAL_CREATED")
        self.assertEqual(audit.entity_type, EntityType.MERCHANT_CREDENTIAL)
        self.assertNotIn("plain-secret", str(audit.after_state_json))

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                create_credential(
                    _FakeDb(),
                    "m_demo",
                    _create_credential_request(self.actor, access_key="ak_dup", secret_key="another-secret"),
                    self.actor,
                    now=self.now,
                )

        self.assertEqual(error.exception.error_code, "ACTIVE_CREDENTIAL_EXISTS")

    def test_activate_merchant_requires_approved_onboarding_and_active_credential(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import MerchantStatus, OnboardingCaseStatus
        from app.services.merchant_ops_service import activate_merchant

        merchant = _merchant(status=MerchantStatus.PENDING_REVIEW)
        pending_case = _onboarding_case(merchant.id, status=OnboardingCaseStatus.PENDING_REVIEW)
        store = _MerchantOpsStore(
            merchants=[merchant],
            onboarding_cases=[pending_case],
            credentials=[_credential(merchant.id)],
        )

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                activate_merchant(_FakeDb(), "m_demo", _reason_request(self.actor), self.actor, now=self.now)

        self.assertEqual(error.exception.error_code, "ONBOARDING_CASE_NOT_APPROVED")

        pending_case.status = OnboardingCaseStatus.APPROVED
        store.credentials.clear()
        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                activate_merchant(_FakeDb(), "m_demo", _reason_request(self.actor), self.actor, now=self.now)

        self.assertEqual(error.exception.error_code, "ACTIVE_CREDENTIAL_REQUIRED")

        store.credentials.append(_credential(merchant.id))
        db = _FakeDb()
        with store.patched_repositories():
            response = activate_merchant(db, "m_demo", _reason_request(self.actor), self.actor, now=self.now)

        self.assertTrue(db.committed)
        self.assertEqual(response.status, MerchantStatus.ACTIVE)
        self.assertEqual(merchant.status, MerchantStatus.ACTIVE)
        self.assertEqual(db.audit_logs[0].event_type, "MERCHANT_ACTIVATED")

    def test_suspend_and_disable_merchant_update_status_and_audit(self) -> None:
        from app.models.enums import MerchantStatus
        from app.services.merchant_ops_service import disable_merchant, suspend_merchant

        merchant = _merchant(status=MerchantStatus.ACTIVE)
        store = _MerchantOpsStore(merchants=[merchant])

        db = _FakeDb()
        with store.patched_repositories():
            response = suspend_merchant(db, "m_demo", _reason_request(self.actor), self.actor, now=self.now)

        self.assertEqual(response.status, MerchantStatus.SUSPENDED)
        self.assertEqual(merchant.status, MerchantStatus.SUSPENDED)
        self.assertEqual(db.audit_logs[0].event_type, "MERCHANT_SUSPENDED")

        db = _FakeDb()
        with store.patched_repositories():
            response = disable_merchant(db, "m_demo", _reason_request(self.actor), self.actor, now=self.now)

        self.assertEqual(response.status, MerchantStatus.DISABLED)
        self.assertEqual(merchant.status, MerchantStatus.DISABLED)
        self.assertEqual(db.audit_logs[0].event_type, "MERCHANT_DISABLED")

    def test_rotate_credential_marks_old_rotated_creates_new_active_and_masks_audit_secret(self) -> None:
        from app.models.enums import CredentialStatus
        from app.services.merchant_ops_service import rotate_credential

        merchant = _merchant()
        old = _credential(merchant.id, access_key="ak_old", secret_key="old-secret")
        store = _MerchantOpsStore(merchants=[merchant], credentials=[old])
        db = _FakeDb()

        with store.patched_repositories():
            response = rotate_credential(
                db,
                "m_demo",
                _rotate_credential_request(self.actor, access_key="ak_new", secret_key="new-secret"),
                self.actor,
                now=self.now,
            )

        self.assertTrue(db.committed)
        self.assertEqual(old.status, CredentialStatus.ROTATED)
        self.assertEqual(old.rotated_at, self.now)
        self.assertEqual(old.expired_at, self.now)
        self.assertEqual(response.access_key, "ak_new")
        active = [credential for credential in store.credentials if credential.status == CredentialStatus.ACTIVE]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].access_key, "ak_new")
        audit = db.audit_logs[0]
        self.assertEqual(audit.event_type, "CREDENTIAL_ROTATED")
        self.assertNotIn("old-secret", str(audit.before_state_json))
        self.assertNotIn("new-secret", str(audit.after_state_json))


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False
        self.committed = False

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    @property
    def audit_logs(self):
        from app.models.audit_log import AuditLog

        return [item for item in self.added if isinstance(item, AuditLog)]


class _MerchantOpsStore:
    def __init__(self, merchants=None, onboarding_cases=None, credentials=None) -> None:
        self.merchants = merchants or []
        self.onboarding_cases = onboarding_cases or []
        self.credentials = credentials or []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.merchant_ops_service.merchant_repository.get_by_public_merchant_id",
                side_effect=self.get_merchant,
            ),
            patch(
                "app.services.merchant_ops_service.merchant_repository.create",
                side_effect=self.create_merchant,
            ),
            patch(
                "app.services.merchant_ops_service.merchant_repository.save",
                side_effect=self.save_merchant,
            ),
            patch(
                "app.services.merchant_ops_service.onboarding_repository.get_by_merchant",
                side_effect=self.get_onboarding_case_by_merchant,
            ),
            patch(
                "app.services.merchant_ops_service.onboarding_repository.create",
                side_effect=self.create_onboarding_case,
            ),
            patch(
                "app.services.merchant_ops_service.onboarding_repository.save",
                side_effect=self.save_onboarding_case,
            ),
            patch(
                "app.services.merchant_ops_service.credential_repository.get_active_by_merchant",
                side_effect=self.get_active_credential,
            ),
            patch(
                "app.services.merchant_ops_service.credential_repository.create",
                side_effect=self.create_credential,
            ),
            patch(
                "app.services.merchant_ops_service.credential_repository.save",
                side_effect=self.save_credential,
            ),
        )

    def get_merchant(self, db, merchant_id):
        for merchant in self.merchants:
            if merchant.merchant_id == merchant_id:
                return merchant
        return None

    def create_merchant(self, db, **kwargs):
        merchant = _merchant(
            merchant_id=kwargs["merchant_id"],
            merchant_name=kwargs["merchant_name"],
            status=kwargs.get("status"),
        )
        merchant.legal_name = kwargs.get("legal_name")
        merchant.contact_name = kwargs.get("contact_name")
        merchant.contact_email = kwargs["contact_email"]
        merchant.contact_phone = kwargs.get("contact_phone")
        merchant.webhook_url = kwargs.get("webhook_url")
        merchant.settlement_account_name = kwargs.get("settlement_account_name")
        merchant.settlement_account_number = kwargs.get("settlement_account_number")
        merchant.settlement_bank_code = kwargs.get("settlement_bank_code")
        self.merchants.append(merchant)
        return merchant

    def save_merchant(self, db, merchant):
        return merchant

    def get_onboarding_case_by_merchant(self, db, merchant_db_id):
        for onboarding_case in self.onboarding_cases:
            if onboarding_case.merchant_db_id == merchant_db_id:
                return onboarding_case
        return None

    def create_onboarding_case(self, db, **kwargs):
        onboarding_case = _onboarding_case(
            merchant_db_id=kwargs["merchant_db_id"],
            status=kwargs["status"],
            domain_or_app_name=kwargs.get("domain_or_app_name"),
        )
        onboarding_case.submitted_profile_json = kwargs["submitted_profile_json"]
        onboarding_case.documents_json = kwargs["documents_json"]
        onboarding_case.review_checks_json = kwargs["review_checks_json"]
        self.onboarding_cases.append(onboarding_case)
        return onboarding_case

    def save_onboarding_case(self, db, onboarding_case):
        return onboarding_case

    def get_active_credential(self, db, merchant_db_id):
        from app.models.enums import CredentialStatus

        for credential in self.credentials:
            if credential.merchant_db_id == merchant_db_id and credential.status == CredentialStatus.ACTIVE:
                return credential
        return None

    def create_credential(self, db, **kwargs):
        credential = _credential(
            merchant_db_id=kwargs["merchant_db_id"],
            access_key=kwargs["access_key"],
            secret_key=kwargs["secret_key"],
        )
        self.credentials.append(credential)
        return credential

    def save_credential(self, db, credential):
        return credential


class _PatchGroup:
    def __init__(self, *patches) -> None:
        self.patches = patches

    def __enter__(self):
        for patcher in self.patches:
            patcher.__enter__()

    def __exit__(self, exc_type, exc, traceback):
        for patcher in reversed(self.patches):
            patcher.__exit__(exc_type, exc, traceback)


def _merchant(merchant_id="m_demo", merchant_name="Demo Merchant", status=None):
    from app.models.enums import MerchantStatus
    from app.models.merchant import Merchant

    return Merchant(
        id=uuid4(),
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        contact_email="ops@example.com",
        status=status or MerchantStatus.PENDING_REVIEW,
    )


def _onboarding_case(merchant_db_id, status, domain_or_app_name="Demo Shop"):
    from app.models.merchant_onboarding_case import MerchantOnboardingCase

    return MerchantOnboardingCase(
        id=uuid4(),
        merchant_db_id=merchant_db_id,
        status=status,
        domain_or_app_name=domain_or_app_name,
        submitted_profile_json={"business_type": "online_shop"},
        documents_json={"business_license": "demo-license.pdf"},
        review_checks_json={"risk_level": "LOW"},
    )


def _credential(merchant_db_id, access_key="ak_demo", secret_key="super-secret"):
    from app.models.enums import CredentialStatus
    from app.models.merchant_credential import MerchantCredential

    return MerchantCredential(
        id=uuid4(),
        merchant_db_id=merchant_db_id,
        access_key=access_key,
        secret_key_encrypted=secret_key,
        secret_key_last4=secret_key[-4:],
        status=CredentialStatus.ACTIVE,
    )


def _create_merchant_request(actor):
    from app.schemas.ops import CreateMerchantRequest

    return CreateMerchantRequest(
        actor=actor,
        merchant_id="m_demo",
        merchant_name="Demo Merchant",
        legal_name="Demo Merchant LLC",
        contact_name="Demo Ops",
        contact_email="ops@example.com",
        contact_phone="+84000000000",
        webhook_url="https://merchant.example.com/webhooks/payment-gateway",
        settlement_account_name="Demo Merchant LLC",
        settlement_account_number="123456789",
        settlement_bank_code="DEMO",
    )


def _submit_onboarding_request(actor, domain="Demo Shop"):
    from app.schemas.ops import SubmitOnboardingCaseRequest

    return SubmitOnboardingCaseRequest(
        actor=actor,
        domain_or_app_name=domain,
        submitted_profile_json={"business_type": "online_shop"},
        documents_json={"business_license": "demo-license.pdf"},
        review_checks_json={"risk_level": "LOW"},
    )


def _review_onboarding_request(actor, decision_note):
    from app.schemas.ops import ReviewOnboardingCaseRequest

    return ReviewOnboardingCaseRequest(
        actor=actor,
        decision_note=decision_note,
    )


def _create_credential_request(actor, access_key, secret_key):
    from app.schemas.ops import CreateCredentialRequest

    return CreateCredentialRequest(
        actor=actor,
        access_key=access_key,
        secret_key=secret_key,
    )


def _rotate_credential_request(actor, access_key, secret_key):
    from app.schemas.ops import RotateCredentialRequest

    return RotateCredentialRequest(
        actor=actor,
        access_key=access_key,
        secret_key=secret_key,
    )


def _reason_request(actor):
    from app.schemas.ops import OpsReasonRequest

    return OpsReasonRequest(actor=actor)


if __name__ == "__main__":
    unittest.main()
