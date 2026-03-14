import pytest
import time
from fastapi.testclient import TestClient
from limits.storage import MemoryStorage
from backend.api.main import app
from backend.core.limiter import limiter

# Mock dependency
from backend.core.security import get_current_user
from backend.models.schemas import User

@pytest.fixture
def mock_user():
    return User(id="user_rate_limit_test", email="test@example.com", is_active=True)

def test_rate_limiting_upload(client, mock_user):
    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    # Upload limit is 5/minute
    # We will try to upload 6 times
    
    file_content = b"test content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    
    # First 5 should succeed (or fail with 422/500 but NOT 429)
    for i in range(5):
        # We need to recreate files tuple for each request because TestClient consumes it
        files = {"file": (f"test_{i}.txt", file_content, "text/plain")}
        response = client.post("/api/v1/documents/upload", files=files)
        # We expect 429 ONLY when limit is exceeded. 
        # Other errors (DB connection etc) are fine for this test.
        assert response.status_code != 429, f"Request {i+1} failed with 429"
        
    # 6th should fail with 429
    files = {"file": ("test_6.txt", file_content, "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text
    
    app.dependency_overrides = {}
