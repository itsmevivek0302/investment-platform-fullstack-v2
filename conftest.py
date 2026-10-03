import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs lifespan -> creates tables + seed
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def user_token(client):
    import uuid
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"name": "Test User", "email": email, "password": "Passw0rd123"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]
