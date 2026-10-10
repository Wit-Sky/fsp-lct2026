import os
import sys
import tempfile
from pathlib import Path

import pytest

# По умолчанию тесты идут на SQLite с той же схемой и тем же сидом, что и в Postgres.
# Прогон на Postgres: TEST_DATABASE_URL=postgresql+asyncpg://... (база должна быть пустой).
_tmp = Path(tempfile.mkdtemp(prefix="fsp-test-"))
os.environ["DATABASE_URL"] = (os.environ.get("TEST_DATABASE_URL")
                              or f"sqlite+aiosqlite:///{(_tmp / 'test.db').as_posix()}")
os.environ.setdefault("DEMO_COOLDOWN_MIN", "2")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-32")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    yield
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register(client, email: str, role: str = "candidate") -> dict:
    r = await client.post("/api/auth/register", json={"email": email, "password": "secret1", "role": role})
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/verify", json={"email": email, "code": r.json()["verify_code"]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def demo(client, role: str) -> dict:
    r = await client.post(f"/api/auth/demo/{role}")
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
