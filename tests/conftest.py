import os
import tempfile

import pytest

# Use a throwaway SQLite DB per test session and keep S3 off by default.
_tmp = tempfile.NamedTemporaryFile(prefix="taskdb_", suffix=".sqlite", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["S3_ENABLED"] = "false"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# Make sure cached settings see the test env vars above.
get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
