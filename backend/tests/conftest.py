import os
from pathlib import Path
import pytest

TEST_DB = Path(__file__).resolve().parent.parent / "test_intentlock.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTH_SECRET"] = "test-secret-intentlock-phase4-32-bytes-minimum"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
