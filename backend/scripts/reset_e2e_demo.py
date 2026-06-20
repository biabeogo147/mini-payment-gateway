from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base

ALLOWED_ENVIRONMENTS = {"local", "demo", "test"}
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}


def assert_demo_reset_allowed(*, app_env: str, database_url: str, confirmed: bool) -> None:
    if not confirmed:
        raise ValueError("Pass --confirm-reset to acknowledge destructive demo data removal.")
    if app_env.lower() not in ALLOWED_ENVIRONMENTS:
        raise ValueError("Demo reset is allowed only in local, demo, or test environments.")
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("Demo reset currently supports PostgreSQL only.")
    if url.host not in ALLOWED_HOSTS:
        raise ValueError("Demo reset refuses non-local database hosts.")


def reset_database(database_url: str) -> None:
    engine = create_engine(database_url)
    table_names = [table.name for table in Base.metadata.sorted_tables]
    with engine.begin() as connection:
        preparer = connection.dialect.identifier_preparer
        quoted = ", ".join(preparer.quote(name) for name in table_names)
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    engine.dispose()


def reset_demo_merchant(base_url: str) -> None:
    import httpx

    try:
        response = httpx.post(f"{base_url.rstrip('/')}/api/demo/reset", timeout=2)
        response.raise_for_status()
    except httpx.HTTPError:
        print("Demo merchant is not running; its in-memory state will reset on next start.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset local data for the end-to-end demo.")
    parser.add_argument("--confirm-reset", action="store_true")
    args = parser.parse_args()
    app_env = os.getenv("APP_ENV", "local")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/mini_payment_gateway",
    )
    assert_demo_reset_allowed(
        app_env=app_env,
        database_url=database_url,
        confirmed=args.confirm_reset,
    )
    reset_database(database_url)
    reset_demo_merchant(os.getenv("DEMO_MERCHANT_BASE_URL", "http://127.0.0.1:8100"))
    print("End-to-end demo data reset. Ops Dashboard will require first-admin bootstrap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
