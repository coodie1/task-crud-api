"""
Automated unit tests for POST /triage endpoint and LLM Service.
Run with: pytest tests/test_triage.py
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from src.llm.schema import TriageResponse, CategoryEnum, UrgencyEnum


client = TestClient(app)


def test_1_triage_input_validation_empty_body():
    """Verify 400 Bad Request on empty or missing body."""
    res = client.post("/triage", json={})
    assert res.status_code == 400
    assert "text" in res.json().get("error", "").lower()


def test_2_triage_input_validation_empty_string():
    """Verify 400 Bad Request on whitespace-only string."""
    res = client.post("/triage", json={"text": "   "})
    assert res.status_code == 400
    assert "non-empty" in res.json().get("error", "").lower()


def test_3_triage_input_validation_max_length():
    """Verify 400 Bad Request when input exceeds 2000 characters."""
    long_text = "a" * 2001
    res = client.post("/triage", json={"text": long_text})
    assert res.status_code == 400
    assert "exceeds" in res.json().get("error", "").lower()


def test_4_triage_stub_mode_execution(monkeypatch):
    """Verify LLM_STUB=1 returns schema-valid response without network calls."""
    monkeypatch.setenv("LLM_STUB", "1")
    monkeypatch.setenv("LLM_ENABLED", "true")

    res = client.post("/triage", json={"text": "Please refund duplicate charge on invoice 101."})
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "billing"
    assert data["urgency"] == "high"
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["reason"]) > 0


def test_5_triage_kill_switch(monkeypatch):
    """Verify LLM_ENABLED=false returns safe deterministic fallback."""
    monkeypatch.setenv("LLM_ENABLED", "false")

    res = client.post("/triage", json={"text": "Any random support inquiry"})
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "other"
    assert "kill switch" in data["reason"].lower()


def test_6_schema_validation_closed_enums():
    """Verify Pydantic schema strictly enforces category and urgency enums."""
    valid_data = {
        "category": "bug",
        "urgency": "high",
        "confidence": 0.99,
        "reason": "Server crashes on login."
    }
    validated = TriageResponse.model_validate(valid_data)
    assert validated.category == CategoryEnum.BUG
    assert validated.urgency == UrgencyEnum.HIGH
