"""Tests for /api/weather — PRD P0: Weather Proxy with Cache."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_weather_requires_auth(client: TestClient):
    """No auth → missing header error."""
    resp = client.get("/api/weather?lat=48.85&lon=2.35")
    assert resp.status_code == 422  # missing required header


def test_weather_returns_mock_without_api_key(client: TestClient, auth_headers: dict):
    """With no OWM API key, returns mock weather data."""
    resp = client.get("/api/weather?lat=48.85&lon=2.35", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "condition" in data
    assert "temp_c" in data
    assert "icon" in data
    assert "server_time" in data


def test_weather_requires_lat_lon(client: TestClient, auth_headers: dict):
    """Missing lat/lon → 422."""
    resp = client.get("/api/weather", headers=auth_headers)
    assert resp.status_code == 422


def test_weather_response_has_server_time(client: TestClient, auth_headers: dict):
    """Response includes server_time for device clock sync."""
    resp = client.get("/api/weather?lat=35.6&lon=139.7", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["server_time"] is not None
