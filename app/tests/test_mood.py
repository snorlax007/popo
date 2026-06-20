"""Tests for /api/mood — PRD P0: LLM Mood Classification + Logging."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_mood_classify_excited(client: TestClient, auth_headers: dict):
    """Excited transcript → mood=excited, popish_cue present."""
    resp = client.post(
        "/api/mood/classify",
        json={"transcript": "I am so excited about this!"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood"] == "excited"
    assert data["popish_cue"] == "Pi-pi-popo-ki-ya!"
    assert "confidence" in data
    assert "server_time" in data


def test_mood_classify_sad(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/mood/classify",
        json={"transcript": "I feel so sad and lonely"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mood"] == "sad"


def test_mood_classify_question_returns_confused(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/mood/classify",
        json={"transcript": "What time is it?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood"] in ("confused", "neutral")


def test_mood_classify_empty_returns_neutral(client: TestClient, auth_headers: dict):
    """Empty transcript → neutral."""
    resp = client.post(
        "/api/mood/classify",
        json={"transcript": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mood"] == "neutral"


def test_mood_log_persisted(client: TestClient, auth_headers: dict):
    """POST /api/mood/log → logged=True."""
    resp = client.post(
        "/api/mood/log",
        json={"mood": "happy", "intent": "greeting", "popish_cue": "Popo-ki!"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["logged"] is True
    assert "id" in resp.json()


def test_mood_requires_auth(client: TestClient):
    resp = client.post("/api/mood/classify", json={"transcript": "hello"})
    assert resp.status_code == 422


@pytest.mark.parametrize("mood", ["happy", "sad", "excited", "confused", "sleepy", "scared", "neutral"])
def test_all_valid_moods_log(client: TestClient, auth_headers: dict, mood: str):
    """All 7 valid mood labels should log successfully."""
    resp = client.post("/api/mood/log", json={"mood": mood}, headers=auth_headers)
    assert resp.status_code == 200
