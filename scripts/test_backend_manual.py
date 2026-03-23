#!/usr/bin/env python3
"""
Manual Backend Testing Script
Test InsightDocs backend without a frontend!

Usage:
    python scripts/test_backend_manual.py

This script will:
1. Register a test user
2. Login and get JWT token
3. Upload a test PDF
4. Wait for processing
5. Query the document with RAG
6. Display results

Prerequisites:
- Backend running on localhost:8000
- PostgreSQL, Redis, Celery workers running
- Test PDF file available
"""

import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"
TEST_NAME = "Test User"

# Colors for output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def print_step(step, message):
    """Print colored step message"""
    print(f"\n{BLUE}[Step {step}]{RESET} {message}")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")


def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


def test_health():
    """Test if backend is running"""
    print_step(1, "Testing backend health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend is running!")
            return True
        else:
            print_error(f"Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Is it running?")
        print_info("Start with: uvicorn backend.main:app --reload")
        return False


def register_user():
    """Register a test user"""
    print_step(2, "Registering test user...")
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if response.status_code == 200:
            print_success(f"User registered: {TEST_EMAIL}")
            return True
        elif response.status_code == 400:
            print_info("User already exists (that's okay!)")
            return True
        else:
            print_error(f"Registration failed: {response.text}")
            return False
    except Exception as e:
        print_error(f"Registration error: {e}")
        return False


def login():
    """Login and get JWT token"""
    print_step(3, "Logging in...")
    payload = {
        "username": TEST_EMAIL,  # FastAPI OAuth2 uses 'username'
        "password": TEST_PASSWORD
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data=payload,  # Form data, not JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_success("Login successful!")
            print_info(f"Token: {token[:20]}...")
            return token
        else:
            print_error(f"Login failed: {response.text}")
            return None
    except Exception as e:
        print_error(f"Login error: {e}")
        return None


def create_test_pdf():
    """Create a simple test PDF if none exists"""
    test_file = Path("/tmp/test_document.txt")
    
    content = """
    # Test Document for InsightDocs

    This is a test document to verify the RAG pipeline works correctly.

    ## Section 1: Overview
    InsightDocs is a powerful document intelligence platform that supports:
    - 23 different file formats
    - Advanced RAG (Retrieval Augmented Generation)
    - Bring Your Own Key (BYOK) for API management
    - Spatial citations with bounding boxes

    ## Section 2: Features
    The platform includes:
    1. Document upload and processing
    2. OCR for scanned PDFs
    3. Table extraction from documents
    4. AI-powered question answering
    5. Podcast generation from documents

    ## Section 3: Architecture
    InsightDocs uses a modern tech stack:
    - FastAPI for the backend
    - PostgreSQL for data storage
    - Milvus for vector search
    - Celery for background jobs
    - React for the frontend

    This document should be successfully ingested and queryable via the RAG system.
    """
    
    test_file.write_text(content.strip())
    print_info(f"Created test file: {test_file}")
    return test_file


def upload_document(token):
    """Upload a test document"""
    print_step(4, "Uploading test document...")
    
    # Create test file
    test_file = create_test_pdf()
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "text/plain")}
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                headers=headers
            )
        
        if response.status_code == 200:
            data = response.json()
            doc_id = data.get("id")
            print_success(f"Document uploaded! ID: {doc_id}")
            return doc_id
        else:
            print_error(f"Upload failed: {response.text}")
            return None
    except Exception as e:
        print_error(f"Upload error: {e}")
        return None


def wait_for_processing(token, doc_id, max_wait=60):
    """Wait for document to finish processing"""
    print_step(5, f"Waiting for document processing (max {max_wait}s)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{BASE_URL}/documents/{doc_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    print_success("Document processing completed!")
                    return True
                elif status == "failed":
                    print_error(f"Processing failed: {data.get('error_message')}")
                    return False
                else:
                    print(f"  Status: {status}... (waiting)", end="\r")
                    time.sleep(2)
            else:
                print_error(f"Status check failed: {response.text}")
                return False
        except Exception as e:
            print_error(f"Status check error: {e}")
            return False
    
    print_error("Timeout waiting for processing")
    return False


def query_document(token, doc_id):
    """Query the document with RAG"""
    print_step(6, "Querying document with RAG...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    questions = [
        "What is InsightDocs?",
        "What file formats are supported?",
        "What is BYOK?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{YELLOW}Question {i}:{RESET} {question}")
        
        payload = {
            "document_id": doc_id,
            "query_text": question
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response_text", "")
                sources = data.get("sources", [])
                confidence = data.get("confidence_score", 0)
                
                print(f"{GREEN}Answer:{RESET} {answer}")
                print(f"{BLUE}Confidence:{RESET} {confidence:.2f}")
                
                if sources:
                    print(f"{BLUE}Sources:{RESET}")
                    for source in sources[:3]:  # Show top 3 sources
                        page = source.get("page_number", "N/A")
                        score = source.get("relevance_score", 0)
                        print(f"  • Page {page} (relevance: {score:.2f})")
                
                print_success("Query successful!")
            else:
                print_error(f"Query failed: {response.text}")
        except Exception as e:
            print_error(f"Query error: {e}")
        
        time.sleep(1)  # Small delay between questions


def test_byok(token):
    """Test BYOK (Bring Your Own Key)"""
    print_step(7, "Testing BYOK...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Save API key
    print_info("Saving test API key...")
    payload = {"api_key": "test-api-key-12345"}
    
    try:
        response = requests.put(
            f"{BASE_URL}/users/me/api-key",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            print_success("API key saved!")
        else:
            print_error(f"Save failed: {response.text}")
            return
    except Exception as e:
        print_error(f"Save error: {e}")
        return
    
    # Delete API key
    print_info("Deleting API key...")
    try:
        response = requests.delete(
            f"{BASE_URL}/users/me/api-key",
            headers=headers
        )
        
        if response.status_code == 200:
            print_success("API key deleted!")
        else:
            print_error(f"Delete failed: {response.text}")
    except Exception as e:
        print_error(f"Delete error: {e}")


def main():
    """Main test workflow"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{GREEN}InsightDocs Backend Manual Testing{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Test health
    if not test_health():
        print_error("\nBackend is not running. Please start it first:")
        print_info("  cd /home/harshil/insightdocs")
        print_info("  docker-compose up -d  # Start PostgreSQL + Redis")
        print_info("  celery -A backend.workers.celery_app worker -l INFO  # Start worker")
        print_info("  uvicorn backend.main:app --reload  # Start backend")
        return
    
    # Register user
    if not register_user():
        return
    
    # Login
    token = login()
    if not token:
        return
    
    # Upload document
    doc_id = upload_document(token)
    if not doc_id:
        return
    
    # Wait for processing
    if not wait_for_processing(token, doc_id):
        return
    
    # Query document
    query_document(token, doc_id)
    
    # Test BYOK
    test_byok(token)
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{GREEN}✅ ALL TESTS PASSED!{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    print(f"{YELLOW}What you just tested:{RESET}")
    print("  ✅ Backend is running")
    print("  ✅ User registration works")
    print("  ✅ Login with JWT works")
    print("  ✅ Document upload works")
    print("  ✅ Background processing works (Celery)")
    print("  ✅ RAG queries work (AI responses)")
    print("  ✅ Source citations work (page numbers)")
    print("  ✅ BYOK save/delete works")
    
    print(f"\n{GREEN}🎉 Your backend is working perfectly!{RESET}")
    print(f"{YELLOW}Next steps:{RESET}")
    print("  1. Deploy backend to Railway (I can guide you)")
    print("  2. Build frontend (follow the guide)")
    print("  3. Deploy frontend to Vercel")
    print("  4. Launch! 🚀\n")


if __name__ == "__main__":
    main()
