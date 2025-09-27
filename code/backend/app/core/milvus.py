from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from app.core.config import settings


def connect_milvus():
    """Establish connection to Milvus/Zilliz Cloud."""
    connections.connect(
        alias="default",
        uri=settings.MILVUS_URI,
        token=settings.MILVUS_TOKEN
    )


def create_collection_if_not_exists():
    """Create collection in Milvus if it doesn't already exist."""
    connect_milvus()

    if utility.has_collection(settings.MILVUS_COLLECTION):
        return Collection(settings.MILVUS_COLLECTION)

    # Define schema
    id_field = FieldSchema(
        name="id",
        dtype=DataType.INT64,
        is_primary=True,
        auto_id=True
    )

    vector_field = FieldSchema(
        name="vector",
        dtype=DataType.FLOAT_VECTOR,
        dim=settings.MILVUS_DIM
    )

    doc_id_field = FieldSchema(
        name="doc_id",
        dtype=DataType.VARCHAR,
        max_length=512
    )

    source_field = FieldSchema(
        name="source",
        dtype=DataType.VARCHAR,
        max_length=256
    )

    # Optional: store chunk text (can also use Postgres instead)
    chunk_field = FieldSchema(
        name="chunk_text",
        dtype=DataType.VARCHAR,
        max_length=65535
    )

    schema = CollectionSchema(
        fields=[id_field, vector_field, doc_id_field, source_field, chunk_field],
        description="InsightOps document embeddings"
    )

    collection = Collection(
        name=settings.MILVUS_COLLECTION,
        schema=schema,
        using="default"
    )

    # Create index for fast search
    index_params = {
        "index_type": "AUTOINDEX",   # Serverless Milvus recommends AUTOINDEX
        "metric_type": settings.MILVUS_METRIC,
        "params": {}
    }
    collection.create_index(field_name="vector", index_params=index_params)

    return collection


def get_collection() -> Collection:
    """Get existing Milvus collection."""
    connect_milvus()
    return Collection(settings.MILVUS_COLLECTION)
