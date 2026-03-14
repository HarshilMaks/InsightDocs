import pytest
from backend.core.limiter import limiter
from limits.storage import MemoryStorage
from fastapi.testclient import TestClient
from backend.api.main import app

@pytest.fixture(scope="function", autouse=True)
def mock_rate_limiter():
    """
    Mock the rate limiter to use memory storage for all integration tests.
    This prevents Redis connection errors and isolates tests.
    """
    mem_storage = MemoryStorage()
    
    # Update slowapi storage reference (for reset())
    limiter._storage = mem_storage
    
    # Update limits strategy storage reference (for hit())
    if hasattr(limiter, "limiter"):
         limiter.limiter.storage = mem_storage
         
    limiter.reset()
    yield
    limiter.reset()

@pytest.fixture
def client():
    return TestClient(app)
