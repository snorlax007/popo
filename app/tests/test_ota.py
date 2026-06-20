"""Tests for /api/ota — PRD P0: OTA Firmware Distribution."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_ota_check_no_firmware(client: TestClient, auth_headers: dict):
    """No firmware uploaded → update_available=False."""
    resp = client.get("/api/ota/check?version=0.1.0", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is False
    assert "server_time" in data


def test_ota_check_requires_version(client: TestClient, auth_headers: dict):
    """Missing version param → 422."""
    resp = client.get("/api/ota/check", headers=auth_headers)
    assert resp.status_code == 422


def test_ota_check_requires_auth(client: TestClient):
    resp = client.get("/api/ota/check?version=0.1.0")
    assert resp.status_code == 422


def test_healthz(client: TestClient):
    """Health endpoint returns ok + db status."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
