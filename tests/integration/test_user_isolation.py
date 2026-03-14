import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.models import Document, User
from backend.core.security import get_current_user

# Setup 2 mock users
user_a = User(id="user_a", email="a@example.com", is_active=True)
user_b = User(id="user_b", email="b@example.com", is_active=True)

@pytest.fixture
def client_with_db():
    return TestClient(app)

def test_user_isolation(client): # client from conftest
    # This test requires mocking the database queries to return documents owned by specific users.
    # Since we don't have a real DB easily set up in this environment (or we do but it's empty),
    # we will mock the get_db dependency to return a session with pre-populated objects.
    
    # However, testing with a real in-memory SQLite DB is better for integration tests.
    # Let's try to set up a temporary SQLite DB.
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from backend.models.database import Base, get_db
    
    # Create in-memory SQLite with StaticPool to share connection
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Ensure all models are registered
    print(f"Registered tables before create: {Base.metadata.tables.keys()}")
    Base.metadata.create_all(bind=engine)
    print(f"Registered tables after create: {Base.metadata.tables.keys()}")
    
    # Create test data
    db = TestingSessionLocal()
    
    # Create users? The User model might not be in Base if it's external (e.g. Auth0/Firebase)
    # But let's assume it is or we just need the ID in the token.
    # Actually, User model is in backend.models.schemas.
    
    # Create documents
    doc_a = Document(
        id="doc_a_1",
        filename="a.pdf",
        file_type="application/pdf",
        file_size=1024,
        s3_bucket="test-bucket",
        s3_key="uploads/a.pdf",
        user_id="user_a",
        status="completed"
    )
    doc_b = Document(
        id="doc_b_1",
        filename="b.pdf",
        file_type="application/pdf",
        file_size=2048,
        s3_bucket="test-bucket",
        s3_key="uploads/b.pdf",
        user_id="user_b", # Different user
        status="completed"
    )
    db.add(doc_a)
    db.add(doc_b)
    db.commit()
    
    # Override get_db
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    # 1. Login as User A
    app.dependency_overrides[get_current_user] = lambda: user_a
    
    # List documents -> Should only see doc_a
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    data = response.json()
    print(f"DEBUG: User A saw documents: {[d['id'] for d in data['documents']]}")
    assert len(data['documents']) == 1, f"Expected 1 document, got {len(data['documents'])}"
    assert data['documents'][0]["id"] == "doc_a_1"
    
    # Get document A -> OK
    response = client.get("/api/v1/documents/doc_a_1")
    assert response.status_code == 200
    
    # Get document B -> 404 Not Found (or 403 Forbidden)
    # Usually isolation implementation filters by user_id so it returns 404.
    response = client.get("/api/v1/documents/doc_b_1")
    assert response.status_code == 404
    
    # 2. Login as User B
    app.dependency_overrides[get_current_user] = lambda: user_b
    
    # List documents -> Should only see doc_b
    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    data = response.json()
    print(f"DEBUG: User B saw documents: {[d['id'] for d in data['documents']]}")
    assert len(data['documents']) == 1, f"Expected 1 document, got {len(data['documents'])}"
    assert data['documents'][0]["id"] == "doc_b_1"
    
    # Get document B -> OK
    response = client.get("/api/v1/documents/doc_b_1")
    assert response.status_code == 200
    
    # Get document A -> 404
    response = client.get("/api/v1/documents/doc_a_1")
    assert response.status_code == 404
    
    # Cleanup
    app.dependency_overrides = {}
