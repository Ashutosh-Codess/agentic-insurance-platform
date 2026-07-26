"""
Same caveat as test_health.py - needs the full stack + a real Postgres
database to actually run. Uses a throwaway email per test run so it's
safe to run against a real dev database repeatedly.
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _unique_email():
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def test_register_then_login():
    email = _unique_email()

    register_response = client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    assert register_response.status_code == 200
    assert register_response.json()["role"] == "customer"

    login_response = client.post("/api/v1/auth/login", data={"username": email, "password": "testpass123"})
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_login_with_wrong_password_fails():
    email = _unique_email()
    client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})

    response = client.post("/api/v1/auth/login", data={"username": email, "password": "wrongpassword"})
    assert response.status_code == 401


def test_duplicate_registration_fails():
    email = _unique_email()
    client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})

    second_attempt = client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    assert second_attempt.status_code == 400
