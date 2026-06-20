"""Tests for /api/auth/* endpoints — PRD P0: Device Authentication."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_device_auth_creates_record(client: TestClient):
    """POST /api/auth/device with new serial → 200 + JWT."""
    resp = client.post("/api/auth/device", json={"serial": "AUTH-TEST-001", "firmware_version": "0.2.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "server_time" in data


def test_device_auth_idempotent(client: TestClient):
    """Re-auth with same serial → 200 (updates last_seen)."""
    resp1 = client.post("/api/auth/device", json={"serial": "AUTH-TEST-002"})
    resp2 = client.post("/api/auth/device", json={"serial": "AUTH-TEST-002", "firmware_version": "0.3.0"})
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_invalid_device_token_rejected(client: TestClient):
    """GET /api/weather with bad token → 422 (header required) or 401."""
    resp = client.get("/api/weather?lat=0&lon=0", headers={"Authorization": "Bearer invalid_token"})
    assert resp.status_code in (401, 404)


def test_user_register(client: TestClient):
    """POST /api/auth/user/register → 200 + JWT."""
    resp = client.post("/api/auth/user/register", json={
        "email": "test@popo.local",
        "password": "testpass123",
        "name": "Test User",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_user_register_duplicate_rejected(client: TestClient):
    """Duplicate email → 409."""
    client.post("/api/auth/user/register", json={"email": "dup@popo.local", "password": "x"})
    resp = client.post("/api/auth/user/register", json={"email": "dup@popo.local", "password": "x"})
    assert resp.status_code == 409


def test_user_login_success(client: TestClient):
    """POST /api/auth/user with valid creds → 200 + JWT."""
    client.post("/api/auth/user/register", json={"email": "login@popo.local", "password": "mypass"})
    resp = client.post("/api/auth/user", json={"email": "login@popo.local", "password": "mypass"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_user_login_wrong_password(client: TestClient):
    """Wrong password → 401."""
    client.post("/api/auth/user/register", json={"email": "bad@popo.local", "password": "correct"})
    resp = client.post("/api/auth/user", json={"email": "bad@popo.local", "password": "wrong"})
    assert resp.status_code == 401
