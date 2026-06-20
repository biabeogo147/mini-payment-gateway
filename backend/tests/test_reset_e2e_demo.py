import subprocess
import sys
import unittest
from pathlib import Path


class ResetE2eDemoSafetyTest(unittest.TestCase):
    def test_reset_script_can_run_as_a_direct_cli(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(backend_root / "scripts" / "reset_e2e_demo.py"), "--help"],
            cwd=backend_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--confirm-reset", result.stdout)

    def test_allows_only_explicit_local_database_targets(self) -> None:
        from scripts.reset_e2e_demo import assert_demo_reset_allowed

        assert_demo_reset_allowed(
            app_env="local",
            database_url="postgresql+psycopg2://postgres:postgres@localhost:5432/demo",
            confirmed=True,
        )

        rejected = (
            ("sandbox", "postgresql+psycopg2://postgres:postgres@localhost:5432/demo", True),
            ("local", "postgresql+psycopg2://postgres:postgres@db.example.com:5432/demo", True),
            ("local", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/demo", False),
        )
        for app_env, database_url, confirmed in rejected:
            with self.subTest(app_env=app_env, database_url=database_url, confirmed=confirmed):
                with self.assertRaises(ValueError):
                    assert_demo_reset_allowed(
                        app_env=app_env,
                        database_url=database_url,
                        confirmed=confirmed,
                    )


if __name__ == "__main__":
    unittest.main()
