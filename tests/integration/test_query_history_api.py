"""Integration tests for authenticated query-history ordering and isolation."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.models import Base, Query, User
from backend.models.database import get_db


engine = create_engine(
    "sqlite:///:memory:",
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


@pytest.fixture
def client(setup_database):
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, name: str) -> tuple[str, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": name, "password": "SecurePass123!"},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "SecurePass123!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["token"]["access_token"], registered.json()["id"]


def _seed_query(query_id: str, user_id: str, query_text: str, created_at: datetime, conversation_id: str | None = None, turn_index: int | None = None):
    db = TestingSessionLocal()
    try:
        db.add(
            Query(
                id=query_id,
                user_id=user_id,
                query_text=query_text,
                response_text=f"Answer for {query_text}",
                sources=[],
                conversation_id=conversation_id,
                turn_index=turn_index,
                created_at=created_at,
                updated_at=created_at,
            )
        )
        db.commit()
    finally:
        db.close()


def test_history_is_private_paginated_and_correctly_ordered(client):
    owner_token, owner_id = _register_and_login(client, "history-owner@example.com", "History Owner")
    other_token, other_id = _register_and_login(client, "history-other@example.com", "History Other")
    base = datetime(2026, 8, 23, tzinfo=timezone.utc)
    _seed_query("history-old", owner_id, "old question", base)
    _seed_query("history-middle", owner_id, "middle question", base + timedelta(minutes=1))
    _seed_query("history-new", owner_id, "new question", base + timedelta(minutes=2))
    _seed_query("history-other", other_id, "private other question", base + timedelta(minutes=3))

    headers = {"Authorization": f"Bearer {owner_token}"}
    page = client.get("/api/v1/query/history", params={"skip": 0, "limit": 2}, headers=headers)
    assert page.status_code == 200, page.text
    payload = page.json()
    assert payload["total"] == 3
    assert [item["id"] for item in payload["queries"]] == ["history-new", "history-middle"]
    assert all(item["id"] != "history-other" for item in payload["queries"])

    second_page = client.get("/api/v1/query/history", params={"skip": 2, "limit": 2}, headers=headers)
    assert second_page.status_code == 200, second_page.text
    assert [item["id"] for item in second_page.json()["queries"]] == ["history-old"]

    other_history = client.get("/api/v1/query/history", headers={"Authorization": f"Bearer {other_token}"})
    assert other_history.status_code == 200, other_history.text
    assert [item["id"] for item in other_history.json()["queries"]] == ["history-other"]


def test_conversation_history_is_ascending_and_owner_scoped(client):
    token, user_id = _register_and_login(client, "history-conversation@example.com", "Conversation Owner")
    _, other_id = _register_and_login(client, "history-conversation-other@example.com", "Conversation Other")
    base = datetime(2026, 8, 23, tzinfo=timezone.utc)
    _seed_query("history-turn-two", user_id, "second question", base + timedelta(minutes=1), "thread-1", 2)
    _seed_query("history-turn-one", user_id, "first question", base, "thread-1", 1)
    _seed_query("history-turn-other", other_id, "other question", base, "thread-1", 1)

    response = client.get(
        "/api/v1/query/history",
        params={"conversation_id": "thread-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 2
    assert [item["id"] for item in payload["queries"]] == ["history-turn-one", "history-turn-two"]
    assert [item["turn_index"] for item in payload["queries"]] == [1, 2]
