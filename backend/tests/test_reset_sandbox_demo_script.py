import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "deploy" / "reset_sandbox_demo.sh"


class ResetSandboxDemoScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT)
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.app_dir = self.root / "app"
        self.app_dir.mkdir()
        (self.app_dir / ".git").mkdir()
        (self.app_dir / ".env").write_text(
            "APP_ENV=sandbox\n"
            "BACKEND_BIND_ADDR=127.0.0.1\n"
            "BACKEND_PORT=8000\n"
            "DEMO_MERCHANT_BIND_ADDR=127.0.0.1\n"
            "DEMO_MERCHANT_PORT=8100\n",
            encoding="utf-8",
        )
        (self.app_dir / "docker-compose.sandbox.yml").write_text(
            "services: {}\n",
            encoding="utf-8",
        )

        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.docker_log = self.root / "docker.log"
        self.sql_log = self.root / "truncate.sql"
        self.backup_dir = self.root / "backups"
        self.bash_environment = self.root / "bash_env"
        self.bash_environment.write_text(
            "curl() { printf '%s\\n' '{\"status\":\"ok\"}'; }\n",
            encoding="utf-8",
            newline="\n",
        )
        self._write_executable(
            "docker",
            """#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
if [[ "$*" == *"stop backend worker demo-merchant"* ]] \
  && [[ "${FAKE_STOP_FAIL:-0}" == "1" ]]; then
  exit 8
elif [[ "$*" == *"ps --status running --services postgres"* ]]; then
  printf '%s\n' postgres
elif [[ "$*" == *"pg_dump"* ]]; then
  printf '%s\n' 'fake postgres dump'
elif [[ "$*" == *"psql"* ]]; then
  cat > "$FAKE_SQL_LOG"
  if [[ "${FAKE_PSQL_FAIL:-0}" == "1" ]]; then
    exit 9
  fi
fi
""",
        )
        self._write_executable(
            "curl",
            """#!/usr/bin/env bash
printf '%s\n' '{"status":"ok"}'
""",
        )

    def test_requires_explicit_confirmation(self) -> None:
        result = self._run_script()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Pass --confirm-reset", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_refuses_non_sandbox_environment(self) -> None:
        (self.app_dir / ".env").write_text("APP_ENV=production\n", encoding="utf-8")

        result = self._run_script("--confirm-reset")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("APP_ENV=sandbox", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_backs_up_truncates_and_restarts_services(self) -> None:
        result = self._run_script("--confirm-reset")

        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list(self.backup_dir.glob("pre-demo-reset-*.sql.gz"))
        self.assertEqual(len(backups), 1)
        self.assertGreater(backups[0].stat().st_size, 0)

        docker_calls = self.docker_log.read_text(encoding="utf-8")
        self.assertIn("stop backend worker demo-merchant", docker_calls)
        self.assertIn("pg_dump", docker_calls)
        self.assertIn("psql", docker_calls)
        self.assertIn("up -d backend worker demo-merchant", docker_calls)

        truncate_sql = self.sql_log.read_text(encoding="utf-8")
        self.assertIn("tablename <> 'alembic_version'", truncate_sql)
        self.assertIn("TRUNCATE TABLE", truncate_sql)
        self.assertIn("Sandbox demo reset complete", result.stdout)

    def test_restarts_services_when_truncate_fails(self) -> None:
        result = self._run_script("--confirm-reset", FAKE_PSQL_FAIL="1")

        self.assertNotEqual(result.returncode, 0)
        docker_calls = (
            self.docker_log.read_text(encoding="utf-8")
            if self.docker_log.exists()
            else ""
        )
        self.assertIn("stop backend worker demo-merchant", docker_calls)
        self.assertIn("up -d backend worker demo-merchant", docker_calls)

    def test_restarts_services_when_stop_partially_fails(self) -> None:
        result = self._run_script("--confirm-reset", FAKE_STOP_FAIL="1")

        self.assertNotEqual(result.returncode, 0)
        docker_calls = self.docker_log.read_text(encoding="utf-8")
        self.assertIn("stop backend worker demo-merchant", docker_calls)
        self.assertIn("up -d backend worker demo-merchant", docker_calls)

    def _run_script(self, *arguments: str, **extra_environment: str) -> subprocess.CompletedProcess:
        bash = os.getenv("BASH_EXE") or shutil.which("bash")
        if bash is None:
            self.fail("Bash is required to test reset_sandbox_demo.sh")
        environment = os.environ.copy()
        environment.update(
            {
                "APP_DIR": self._bash_path(self.app_dir),
                "BACKUP_DIR": self._bash_path(self.backup_dir),
                "BASH_ENV": self._bash_path(self.bash_environment),
                "COMPOSE_FILE": "docker-compose.sandbox.yml",
                "FAKE_DOCKER_LOG": self._bash_path(self.docker_log),
                "FAKE_SQL_LOG": self._bash_path(self.sql_log),
                "HEALTH_ATTEMPTS": "1",
                "HEALTH_SLEEP_SECONDS": "0",
                "PATH": f"{self._bash_path(self.bin_dir)}:/usr/bin:/bin",
            }
        )
        environment.update(extra_environment)
        return subprocess.run(
            [bash, self._bash_path(SCRIPT_PATH), *arguments],
            cwd=self.app_dir,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _write_executable(self, name: str, content: str) -> None:
        path = self.bin_dir / name
        path.write_text(content, encoding="utf-8", newline="\n")
        path.chmod(0o755)

    @staticmethod
    def _bash_path(path: Path) -> str:
        resolved = path.resolve()
        if os.name != "nt":
            return resolved.as_posix()
        drive = resolved.drive.rstrip(":").lower()
        return f"/{drive}{resolved.as_posix()[2:]}"


if __name__ == "__main__":
    unittest.main()
