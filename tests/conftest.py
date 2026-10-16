"""Shared fixtures for the API tests: a real Postgres test database and a client.

Domain tests need no database. The API tests run against real Postgres so the
constraints (unique email, no overlapping bookings) are tested for real.

The test database comes from TEST_DATABASE_URL (default below). It is created
if missing and migrated with pgmigrate once per run. Before each test every
table is emptied and the seed data is loaded again, so tests never see each
other's rows. If Postgres cannot be reached, the API tests are skipped.
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.config import Settings, get_settings
from app.main import app
from database.seed import seed

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://carwash:carwash@localhost:5432/carwash_test"
)
TEST_TOKEN = "test-token"
DATABASE_DIR = Path(__file__).parent.parent / "database"


def create_database_if_missing(url: str) -> None:
    """Connect to the server's 'postgres' database and create the test database."""
    info = psycopg.conninfo.conninfo_to_dict(url)
    name = info["dbname"]
    server_url = psycopg.conninfo.make_conninfo(url, dbname="postgres")
    with psycopg.connect(server_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name]).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture(scope="session")
def database_url() -> str:
    try:
        create_database_if_missing(TEST_DATABASE_URL)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not reachable at TEST_DATABASE_URL: {exc}")
    pgmigrate = Path(sys.executable).parent / "pgmigrate"
    subprocess.run(
        [pgmigrate, "-d", DATABASE_DIR, "-c", TEST_DATABASE_URL, "-t", "latest", "migrate"],
        check=True,
        capture_output=True,
    )
    return TEST_DATABASE_URL


@pytest.fixture
def client(database_url: str):
    """An API client on a freshly seeded database."""
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE appointments, customers, services, branches")
    seed(database_url)

    def test_settings() -> Settings:
        return Settings(database_url=database_url, api_token=TEST_TOKEN)

    app.dependency_overrides[get_settings] = test_settings
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth() -> dict:
    """The header that write endpoints need."""
    return {"Authorization": f"Bearer {TEST_TOKEN}"}
