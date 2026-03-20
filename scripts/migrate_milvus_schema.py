"""
Milvus Schema Migration Script
================================
Drops the existing InsightDocs collection and recreates it with the
new hybrid schema (dense_vector + sparse_vector fields) AND user_id field
for multi-tenant isolation (BYOK support).

Usage:
    uv run python scripts/migrate_milvus_schema.py

WARNING: This will delete all existing vectors. Re-ingest your documents
         after running this script.
"""
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.config import settings
from pymilvus import connections, utility, Collection

def migrate():
    print("=" * 60)
    print("Milvus Schema Migration: Hybrid Search + User Isolation")
    print("=" * 60)

    print(f"\n→ Connecting to Milvus at {settings.milvus_uri}...")
    connections.connect(
        alias="default",
        uri=settings.milvus_uri,
        token=settings.milvus_token
    )
    print("  ✓ Connected")

    collection_name = settings.milvus_collection

    if utility.has_collection(collection_name):
        print(f"\n→ Found existing collection '{collection_name}'")
        col = Collection(collection_name)
        num_entities = col.num_entities
        print(f"  ℹ  Contains {num_entities} vectors — these will be deleted")
        confirm = input("\nDrop and recreate collection? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Aborted — no changes made.")
            return

        col.release()
        utility.drop_collection(collection_name)
        print(f"  ✓ Dropped collection '{collection_name}'")
    else:
        print(f"\n→ Collection '{collection_name}' does not exist — will create fresh.")

    # Recreate with hybrid schema
    print("\n→ Creating new hybrid collection...")
    from pymilvus import CollectionSchema, FieldSchema, DataType

    fields = [
        FieldSchema(name="id",            dtype=DataType.VARCHAR, is_primary=True, max_length=100),
        FieldSchema(name="document_id",   dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="user_id",       dtype=DataType.VARCHAR, max_length=100),  # NEW: Tenant isolation
        FieldSchema(name="text",          dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="dense_vector",  dtype=DataType.FLOAT_VECTOR, dim=settings.vector_dimension),
        FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
    ]
    schema = CollectionSchema(fields=fields, description="Document embeddings (Hybrid + Multi-Tenant)")
    col = Collection(name=collection_name, schema=schema)
    print(f"  ✓ Collection '{collection_name}' created")

    # Create indexes
    print("\n→ Creating indexes...")
    col.create_index(
        field_name="dense_vector",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
    )
    print("  ✓ Dense vector index (COSINE / IVF_FLAT)")

    col.create_index(
        field_name="sparse_vector",
        index_params={
            "metric_type": "IP",
            "index_type": "SPARSE_INVERTED_INDEX",
            "params": {"drop_ratio_build": 0.2}
        }
    )
    print("  ✓ Sparse vector index (IP / SPARSE_INVERTED_INDEX)")

    col.load()
    print("  ✓ Collection loaded into memory")

    print("\n" + "=" * 60)
    print("Migration complete! Re-ingest your documents to populate")
    print("the new hybrid collection.")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
