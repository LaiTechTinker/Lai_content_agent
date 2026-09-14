import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import router as auth_router
from app.db.database import get_connection
from app.services import auth_service
from app.services import generated_content_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "auth.db")
    monkeypatch.setattr(auth_service, "get_connection", lambda: get_connection(db_path))
    monkeypatch.setattr(generated_content_service, "get_connection", lambda: get_connection(db_path))
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    return TestClient(app), db_path


def register(client, email, name="Test User"):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "correct horse battery staple"},
    )


def login(client, email):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )


def test_registration_hashes_password_and_normalizes_email(client):
    api, db_path = client
    response = register(api, "  User@Example.COM ")
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "user@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]

    with get_connection(db_path) as connection:
        row = connection.execute("SELECT email, password_hash FROM users").fetchone()
        assert row["email"] == "user@example.com"
        assert row["password_hash"] != "correct horse battery staple"
        assert row["password_hash"].startswith("$argon2")

    assert register(api, "USER@example.com").status_code == 409
    assert api.post(
        "/api/auth/register",
        json={"name": "Short", "email": "short@example.com", "password": "short"},
    ).status_code == 422


def test_login_me_refresh_rotation_and_logout(client):
    api, db_path = client
    register(api, "user@example.com")

    assert login(api, "USER@EXAMPLE.COM").status_code == 200
    failed = api.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrong password"},
    )
    assert failed.status_code == 401

    tokens = login(api, "user@example.com").json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = api.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    rotated = api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert api.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401

    assert api.post("/api/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}).status_code == 200
    assert api.post("/api/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}).status_code == 401

    with get_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM refresh_sessions").fetchone()[0] == 3


def test_auth_rejects_missing_invalid_and_wrong_type_tokens(client):
    api, _ = client
    register(api, "user@example.com")
    assert api.get("/api/auth/me").status_code == 401
    assert api.get("/api/auth/me", headers={"Authorization": "Bearer malformed"}).status_code == 401


def test_user_owned_content_isolation(client):
    api, db_path = client
    register(api, "a@example.com", "User A")
    token_a = login(api, "a@example.com").json()["access_token"]
    register(api, "b@example.com", "User B")
    token_b = login(api, "b@example.com").json()["access_token"]

    with get_connection(db_path) as connection:
        user_a = connection.execute("SELECT id FROM users WHERE email = ?", ("a@example.com",)).fetchone()[0]
        user_b = connection.execute("SELECT id FROM users WHERE email = ?", ("b@example.com",)).fetchone()[0]

    content_a = generated_content_service.save_generated_content(
        user_id=user_a, idea_id=None, platform="X", content_type="technical", content="A", quality_score=8
    )
    content_b = generated_content_service.save_generated_content(
        user_id=user_b, idea_id=None, platform="X", content_type="technical", content="B", quality_score=8
    )

    assert generated_content_service.get_content(content_a, user_id=user_a)["content"] == "A"
    assert generated_content_service.get_content(content_b, user_id=user_a) is None
    assert generated_content_service.update_content_metadata(content_b, final_content="tampered", user_id=user_a) is None
    assert generated_content_service.delete_content(content_b, user_id=user_a) is False
    assert generated_content_service.get_content(content_b, user_id=user_b)["content"] == "B"

    assert api.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()["email"] == "a@example.com"
    assert api.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()["email"] == "b@example.com"
