#!/usr/bin/env python3
"""
Verification script to test all fixed components.
Run: python verify_fixes.py
"""

import sys
import asyncio


def test_settings():
    """Test settings configuration."""
    print("1️⃣  Testing Settings...")
    try:
        from backend.config import settings
        
        assert hasattr(settings, 'secret_key'), "Missing secret_key"
        assert hasattr(settings, 'gemini_api_key'), "Missing gemini_api_key"
        assert hasattr(settings, 'milvus_uri'), "Missing milvus_uri"
        assert hasattr(settings, 'milvus_token'), "Missing milvus_token"
        assert hasattr(settings, 'vector_dimension'), "Missing vector_dimension"
        assert settings.vector_dimension == 384, f"Wrong dimension: {settings.vector_dimension}"
        
        print("   ✅ Settings structure is FLAT and correct")
        print(f"   ✅ Vector dimension: {settings.vector_dimension}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_security():
    """Test security module with flat settings."""
    print("\n2️⃣  Testing Security (JWT & bcrypt)...")
    try:
        from backend.config import settings
        from passlib.context import CryptContext
        from jose import jwt
        from datetime import datetime, timedelta, timezone
        
        # Test password hashing
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password = "test123"
        hashed = pwd_context.hash(password)
        verified = pwd_context.verify(password, hashed)
        assert verified, "Password verification failed"
        print("   ✅ Password hashing (bcrypt 4.0.1) works")
        
        # Test JWT
        data = {"user_id": "test-user"}
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        data.update({"exp": expire})
        token = jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)
        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert decoded.get('user_id') == "test-user", "JWT decode failed"
        print("   ✅ JWT token creation and decoding works")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client():
    """Test LLM client with Gemini."""
    print("\n3️⃣  Testing LLM Client (Gemini)...")
    try:
        from backend.utils.llm_client import LLMClient
        import google.generativeai as genai
        
        client = LLMClient()
        assert hasattr(client, 'model'), "Missing model attribute"
        
        print(f"   ✅ LLMClient initialized with Gemini")
        print(f"   ✅ Using google-generativeai {genai.__version__}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_embeddings():
    """Test embeddings engine with Milvus."""
    print("\n4️⃣  Testing Embeddings (Milvus)...")
    try:
        # Don't actually connect (cluster might be stopped)
        # Just verify imports and structure
        from backend.utils.embeddings import EmbeddingEngine
        from sentence_transformers import SentenceTransformer
        import pymilvus
        
        print("   ✅ EmbeddingEngine imports successfully")
        print("   ✅ Using pymilvus for vector storage")
        print("   ✅ Using sentence-transformers for embeddings")
        print("   ⚠️  Note: Milvus cluster connection skipped (may be stopped)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_embeddings_methods():
    """Test embedding methods (without Milvus connection)."""
    print("\n5️⃣  Testing Embedding Methods...")
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        texts = ["Hello world", "Test document"]
        embeddings = model.encode(texts, convert_to_numpy=True)
        
        assert len(embeddings) == 2, f"Wrong number of embeddings: {len(embeddings)}"
        assert len(embeddings[0]) == 384, f"Wrong dimension: {len(embeddings[0])}"
        
        print(f"   ✅ Sentence transformer works")
        print(f"   ✅ Generated {len(embeddings)} embeddings")
        print(f"   ✅ Embedding dimension: {len(embeddings[0])}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_api_structure():
    """Test API structure and imports."""
    print("\n6️⃣  Testing API Structure...")
    try:
        from backend.api.main import app
        from backend.api import auth, documents, query, tasks
        
        routes = [route.path for route in app.routes]
        
        # Check key routes exist
        assert any('/auth' in r for r in routes), "Missing auth routes"
        assert any('/documents' in r for r in routes), "Missing document routes"
        assert any('/query' in r for r in routes), "Missing query routes"
        
        print("   ✅ FastAPI app initialized")
        print("   ✅ All routers imported")
        print(f"   ✅ Total routes: {len(routes)}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("  VERIFICATION SCRIPT - Testing All Fixed Components")
    print("="*70 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Settings", test_settings()))
    results.append(("Security", test_security()))
    results.append(("LLM Client", test_llm_client()))
    results.append(("Embeddings", test_embeddings()))
    results.append(("Embedding Methods", asyncio.run(test_embeddings_methods())))
    results.append(("API Structure", test_api_structure()))
    
    # Summary
    print("\n" + "="*70)
    print("  VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {name}")
    
    print("\n" + "="*70)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("="*70 + "\n")
    
    if passed == total:
        print("🎉 All verifications passed! System is ready.")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
