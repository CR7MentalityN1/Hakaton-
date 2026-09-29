import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "sqlite:///" + str(ROOT / "data" / "v2-tests.db")
)
os.environ["DATA_DIR"] = str(ROOT / "data" / "v2-tests-files")
os.environ["MPLCONFIGDIR"] = str(ROOT / "data" / "matplotlib")
os.environ["TESTING"] = "true"

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, engine
from app.db.seed import seed
from app.security.auth import current_user
from app.core.cache import cache
from app.models import Employee
import fakeredis


@pytest.fixture(scope="session", autouse=True)
def schema():
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    seed()
    cache.client = fakeredis.FakeRedis(decode_responses=True)
    yield
    engine.dispose()


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def login():
    def as_user(id):
        def dependency():
            with SessionLocal() as db:
                return db.get(Employee, id)

        app.dependency_overrides[current_user] = dependency

    return as_user
