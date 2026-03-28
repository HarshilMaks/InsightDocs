"""
End-to-end integration tests for BYOK user flows and encryption behavior.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from backend.api.main import app
from backend.core.security import decrypt_api_key, encrypt_api_key
from backend.models.database import Base, get_db
from backend.models.schemas import User


FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-pro",
]


TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(setup_database):
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_gemini_probe():
    def _probe(api_key, model_candidates=None):
        if not api_key:
            return {
                "status": "missing",
                "model_status": "unavailable",
                "message": "No Gemini API key has been saved yet.",
                "active_model": None,
                "fallback_models": FALLBACK_MODELS,
                "available_models": [],
                "checked_at": "2026-03-28T00:00:00",
            }

        return {
            "status": "healthy",
            "model_status": "primary",
            "message": "Gemini key is valid. Using gemini-2.5-flash.",
            "active_model": "gemini-2.5-flash",
            "fallback_models": FALLBACK_MODELS,
            "available_models": ["gemini-2.5-flash", "gemini-2.0-flash"],
            "checked_at": "2026-03-28T00:00:00",
        }

    with patch("backend.api.users.probe_gemini_status", side_effect=_probe):
        yield


def _register_and_login(client: TestClient, email: str, name: str, password: str = "SecurePass123!"):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": password},
    )
    assert r.status_code == 201, r.text

    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text

    payload = r.json()
    token = payload["token"]["access_token"]
    return token


class TestBYOKEndToEnd:
    def test_user_registration_and_login(self, client):
        token = _register_and_login(client, "alice@example.com", "Alice")
        assert token

    def test_save_api_key_invalid_format(self, client):
        token = _register_and_login(client, "charlie@example.com", "Charlie")
        headers = {"Authorization": f"Bearer {token}"}

        invalid_keys = [
            "invalid-key",
            "AIza123",
            "AIza" + "x" * 100,
            "AIza-abc@#$%",
            "",
        ]

        for key in invalid_keys:
            r = client.put(
                "/api/v1/users/me/api-key",
                json={"api_key": key},
                headers=headers,
            )
            assert r.status_code == 422, f"Expected 422 for key={key}, got {r.status_code}"

    def test_save_valid_api_key_and_status(self, client):
        token = _register_and_login(client, "dave@example.com", "Dave")
        headers = {"Authorization": f"Bearer {token}"}

        valid_key = "AIzaSyC_mock_key_for_testing_purposes_12345"
        r = client.put(
            "/api/v1/users/me/api-key",
            json={"api_key": valid_key},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        save_payload = r.json()
        assert save_payload["status"] == "healthy"
        assert save_payload["model_status"] == "primary"
        assert save_payload["active_model"] == "gemini-2.5-flash"

        r = client.get("/api/v1/users/me/byok-status", headers=headers)
        assert r.status_code == 200
        status = r.json()
        assert status["byok_enabled"] is True
        assert status["has_api_key"] is True
        assert status["status"] == "healthy"
        assert status["model_status"] == "primary"
        assert status["email"] == "dave@example.com"

    def test_remove_api_key(self, client):
        token = _register_and_login(client, "frank@example.com", "Frank")
        headers = {"Authorization": f"Bearer {token}"}

        valid_key = "AIzaSyC_key_to_be_removed_testing_11111"
        r = client.put("/api/v1/users/me/api-key", json={"api_key": valid_key}, headers=headers)
        assert r.status_code == 200

        r = client.delete("/api/v1/users/me/api-key", headers=headers)
        assert r.status_code == 200

        r = client.get("/api/v1/users/me/byok-status", headers=headers)
        assert r.status_code == 200
        status = r.json()
        assert status["byok_enabled"] is False
        assert status["has_api_key"] is False
        assert status["status"] == "missing"

    def test_save_api_key_reports_invalid_status(self, client):
        token = _register_and_login(client, "ivy@example.com", "Ivy")
        headers = {"Authorization": f"Bearer {token}"}

        invalid_status = {
            "status": "invalid",
            "model_status": "unavailable",
            "message": "The Gemini API key is invalid or unauthorized.",
            "active_model": None,
            "fallback_models": FALLBACK_MODELS,
            "available_models": [],
            "checked_at": "2026-03-28T00:00:00",
        }

        with patch("backend.api.users.probe_gemini_status", return_value=invalid_status):
            r = client.put(
                "/api/v1/users/me/api-key",
                json={"api_key": "AIzaSyC_invalid_status_key_for_testing_123"},
                headers=headers,
            )

            assert r.status_code == 200, r.text
            payload = r.json()
            assert payload["status"] == "invalid"
            assert payload["model_status"] == "unavailable"
            assert payload["byok_enabled"] is False

            status = client.get("/api/v1/users/me/byok-status", headers=headers).json()
            assert status["status"] == "invalid"
            assert status["model_status"] == "unavailable"

    def test_toggle_byok_settings(self, client):
        token = _register_and_login(client, "grace@example.com", "Grace")
        headers = {"Authorization": f"Bearer {token}"}

        r = client.patch("/api/v1/users/me/byok-settings", json={"enabled": True}, headers=headers)
        assert r.status_code == 400

        valid_key = "AIzaSyC_toggle_test_key_for_testing_22222"
        r = client.put("/api/v1/users/me/api-key", json={"api_key": valid_key}, headers=headers)
        assert r.status_code == 200

        r = client.patch("/api/v1/users/me/byok-settings", json={"enabled": False}, headers=headers)
        assert r.status_code == 200
        assert "disabled" in r.json()["message"]

        r = client.patch("/api/v1/users/me/byok-settings", json={"enabled": True}, headers=headers)
        assert r.status_code == 200
        assert "enabled" in r.json()["message"]


class TestEncryptionSecurity:
    def test_encryption_decryption_cycle(self):
        original_key = "AIzaSyC_test_encryption_key_33333"
        encrypted = encrypt_api_key(original_key)
        assert encrypted != original_key
        assert "$" in encrypted
        assert decrypt_api_key(encrypted) == original_key

    def test_different_encryptions_same_key(self):
        key = "AIzaSyC_test_randomness_key_44444"
        encrypted1 = encrypt_api_key(key)
        encrypted2 = encrypt_api_key(key)
        assert encrypted1 != encrypted2
        assert decrypt_api_key(encrypted1) == key
        assert decrypt_api_key(encrypted2) == key

    def test_invalid_encrypted_data_returns_none(self):
        assert decrypt_api_key("invalid-encrypted-data") is None
        assert decrypt_api_key("no-dollar-sign") is None
        assert decrypt_api_key("") is None


class TestMultiTenantIsolation:
    def test_users_have_separate_api_keys(self, client):
        token1 = _register_and_login(client, "user1@example.com", "User One")
        token2 = _register_and_login(client, "user2@example.com", "User Two")

        h1 = {"Authorization": f"Bearer {token1}"}
        h2 = {"Authorization": f"Bearer {token2}"}

        r1 = client.put(
            "/api/v1/users/me/api-key",
            json={"api_key": "AIzaSyC_user1_unique_key_55555_valid_len"},
            headers=h1,
        )
        r2 = client.put(
            "/api/v1/users/me/api-key",
            json={"api_key": "AIzaSyC_user2_unique_key_66666_valid_len"},
            headers=h2,
        )
        assert r1.status_code == 200
        assert r2.status_code == 200

        s1 = client.get("/api/v1/users/me/byok-status", headers=h1).json()
        s2 = client.get("/api/v1/users/me/byok-status", headers=h2).json()

        assert s1["has_api_key"] is True
        assert s2["has_api_key"] is True
        assert s1["email"] == "user1@example.com"
        assert s2["email"] == "user2@example.com"

        db = TestingSessionLocal()
        try:
            u1 = db.query(User).filter(User.email == "user1@example.com").first()
            u2 = db.query(User).filter(User.email == "user2@example.com").first()
            assert u1 is not None and u2 is not None
            assert u1.gemini_api_key_encrypted != u2.gemini_api_key_encrypted
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
