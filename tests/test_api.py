"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "components" in data
    assert data["components"]["api"] == "healthy"


def test_api_docs_available(client):
    """Test that API docs are available."""
    response = client.get("/api/v1/docs")
    assert response.status_code == 200


def test_openapi_schema_available(client):
    """Test that OpenAPI schema is available."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "InsightDocs"
