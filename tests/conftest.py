from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend.database as dbmod
from backend.models.orm import Base
from backend.routers import auth, teachers
from backend.services.auth_utils import hash_password


@pytest.fixture()
def test_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.sqlite3"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(
        db_url,
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    monkeypatch.setattr(dbmod, "engine", engine, raising=True)
    monkeypatch.setattr(dbmod, "SessionLocal", testing_session_local, raising=True)

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (username, password_hash, role) VALUES (:u, :p, 'admin')"
            ),
            {"u": "admin", "p": hash_password("admin123")},
        )

    try:
        yield {"engine": engine, "db_url": db_url}
    finally:
        engine.dispose()


@pytest.fixture()
def app(test_db):
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(teachers.router)
    return app


@pytest.fixture()
def client(app: FastAPI):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("token")
    return data["token"]


@pytest.fixture()
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
