import os
import unittest
from unittest.mock import patch


class DemoMerchantConfigTest(unittest.TestCase):
    def test_uses_selected_provider_secret_from_gateway_mapping(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "SIMULATOR",
                "PROVIDER_CALLBACK_SECRETS": (
                    "other=other-secret,simulator=sandbox-secret"
                ),
            },
            clear=True,
        ):
            settings = DemoMerchantSettings.from_env()

        self.assertEqual(settings.provider_id, "simulator")
        self.assertEqual(settings.provider_callback_secret, "sandbox-secret")

    def test_explicit_demo_secret_overrides_gateway_mapping(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "simulator",
                "DEMO_PROVIDER_CALLBACK_SECRET": "explicit-secret",
                "PROVIDER_CALLBACK_SECRETS": "simulator=mapped-secret",
            },
            clear=True,
        ):
            settings = DemoMerchantSettings.from_env()

        self.assertEqual(settings.provider_callback_secret, "explicit-secret")

    def test_rejects_mapping_without_selected_provider(self) -> None:
        from demo_merchant.config import DemoMerchantSettings

        with patch.dict(
            os.environ,
            {
                "DEMO_PROVIDER_ID": "simulator",
                "PROVIDER_CALLBACK_SECRETS": "other=other-secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "No callback secret configured for provider 'simulator'",
            ):
                DemoMerchantSettings.from_env()


if __name__ == "__main__":
    unittest.main()
