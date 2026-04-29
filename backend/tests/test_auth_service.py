import hashlib
import hmac
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.core.errors import AppError
from app.models.enums import CredentialStatus, MerchantStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential


class SecurityHelperTest(unittest.TestCase):
    def test_sha256_hex_hashes_request_body(self) -> None:
        from app.core.security import sha256_hex

        self.assertEqual(sha256_hex(b'{"amount":"100.00"}'), hashlib.sha256(b'{"amount":"100.00"}').hexdigest())

    def test_build_signing_string_uses_timestamp_method_path_and_body_hash(self) -> None:
        from app.core.security import build_signing_string

        signing_string = build_signing_string(
            timestamp="2026-04-29T10:00:00Z",
            method="post",
            path="/v1/payments",
            body=b"{}",
        )

        self.assertEqual(
            signing_string,
            f"2026-04-29T10:00:00Z.POST./v1/payments.{hashlib.sha256(b'{}').hexdigest()}",
        )

    def test_hmac_signature_matches_standard_library(self) -> None:
        from app.core.security import sign_hmac_sha256

        self.assertEqual(
            sign_hmac_sha256("secret", "message"),
            hmac.new(b"secret", b"message", hashlib.sha256).hexdigest(),
        )


class AuthServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        self.body = b'{"order_id":"ORDER-1"}'
        self.merchant = Merchant(
            id=uuid4(),
            merchant_id="m_demo",
            merchant_name="Demo Merchant",
            contact_email="ops@example.com",
            status=MerchantStatus.ACTIVE,
        )
        self.credential = MerchantCredential(
            id=uuid4(),
            merchant_db_id=self.merchant.id,
            access_key="ak_demo",
            secret_key_encrypted="super-secret",
            secret_key_last4="cret",
            status=CredentialStatus.ACTIVE,
        )

    def test_valid_signature_returns_authenticated_merchant(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers()

        with self._patched_repositories():
            authenticated = authenticate_merchant_request(
                db=object(),
                method="POST",
                path="/v1/payments",
                body=self.body,
                headers=headers,
                now=self.now,
            )

        self.assertIs(authenticated.merchant, self.merchant)
        self.assertIs(authenticated.credential, self.credential)
        self.assertEqual(authenticated.merchant_id, "m_demo")

    def test_missing_required_header_fails_with_specific_error_code(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers()
        del headers["X-Signature"]

        with self.assertRaises(AppError) as error:
            authenticate_merchant_request(
                db=object(),
                method="POST",
                path="/v1/payments",
                body=self.body,
                headers=headers,
                now=self.now,
            )

        self.assertEqual(error.exception.error_code, "AUTH_MISSING_HEADER")
        self.assertEqual(error.exception.status_code, 401)

    def test_invalid_signature_fails_with_specific_error_code(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers()
        headers["X-Signature"] = "bad-signature"

        with self._patched_repositories():
            with self.assertRaises(AppError) as error:
                authenticate_merchant_request(
                    db=object(),
                    method="POST",
                    path="/v1/payments",
                    body=self.body,
                    headers=headers,
                    now=self.now,
                )

        self.assertEqual(error.exception.error_code, "AUTH_INVALID_SIGNATURE")
        self.assertEqual(error.exception.status_code, 401)

    def test_expired_timestamp_fails_with_specific_error_code(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers(timestamp=self.now - timedelta(minutes=6))

        with self.assertRaises(AppError) as error:
            authenticate_merchant_request(
                db=object(),
                method="POST",
                path="/v1/payments",
                body=self.body,
                headers=headers,
                now=self.now,
            )

        self.assertEqual(error.exception.error_code, "AUTH_TIMESTAMP_EXPIRED")
        self.assertEqual(error.exception.status_code, 401)

    def test_unknown_merchant_fails_with_specific_error_code(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers()

        with patch("app.services.auth_service.merchant_repository.get_by_public_merchant_id", return_value=None):
            with self.assertRaises(AppError) as error:
                authenticate_merchant_request(
                    db=object(),
                    method="POST",
                    path="/v1/payments",
                    body=self.body,
                    headers=headers,
                    now=self.now,
                )

        self.assertEqual(error.exception.error_code, "AUTH_INVALID_MERCHANT")

    def test_inactive_credential_fails_with_specific_error_code(self) -> None:
        from app.services.auth_service import authenticate_merchant_request

        headers = self._signed_headers()

        with patch(
            "app.services.auth_service.merchant_repository.get_by_public_merchant_id",
            return_value=self.merchant,
        ):
            with patch(
                "app.services.auth_service.credential_repository.get_active_by_merchant_and_access_key",
                return_value=None,
            ):
                with self.assertRaises(AppError) as error:
                    authenticate_merchant_request(
                        db=object(),
                        method="POST",
                        path="/v1/payments",
                        body=self.body,
                        headers=headers,
                        now=self.now,
                    )

        self.assertEqual(error.exception.error_code, "AUTH_INVALID_CREDENTIAL")

    def _signed_headers(self, timestamp: datetime | None = None) -> dict[str, str]:
        timestamp_value = (timestamp or self.now).isoformat().replace("+00:00", "Z")
        body_hash = hashlib.sha256(self.body).hexdigest()
        signing_string = f"{timestamp_value}.POST./v1/payments.{body_hash}"
        signature = hmac.new(b"super-secret", signing_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "X-Merchant-Id": "m_demo",
            "X-Access-Key": "ak_demo",
            "X-Timestamp": timestamp_value,
            "X-Signature": signature,
        }

    def _patched_repositories(self):
        merchant_patch = patch(
            "app.services.auth_service.merchant_repository.get_by_public_merchant_id",
            return_value=self.merchant,
        )
        credential_patch = patch(
            "app.services.auth_service.credential_repository.get_active_by_merchant_and_access_key",
            return_value=self.credential,
        )
        return _PatchGroup(merchant_patch, credential_patch)


class _PatchGroup:
    def __init__(self, *patches):
        self.patches = patches

    def __enter__(self):
        for patcher in self.patches:
            patcher.__enter__()

    def __exit__(self, exc_type, exc, traceback):
        for patcher in reversed(self.patches):
            patcher.__exit__(exc_type, exc, traceback)


if __name__ == "__main__":
    unittest.main()
