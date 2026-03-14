import sys
import os
import logging
from pymilvus import connections, utility

# Add project root to sys.path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_milvus_collection():
    """Drop the existing Milvus collection to allow schema recreation."""
    collection_name = settings.milvus_collection
    uri = settings.milvus_uri
    token = settings.milvus_token

    logger.info(f"Connecting to Milvus at {uri}...")
    try:
        connections.connect(alias="default", uri=uri, token=token)
        logger.info("Connected successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {e}")
        return

    if utility.has_collection(collection_name):
        logger.info(f"Dropping collection: {collection_name}...")
        try:
            utility.drop_collection(collection_name)
            logger.info(f"Successfully dropped collection: {collection_name}")
            logger.info("The collection will be recreated with the new schema on the next application startup.")
        except Exception as e:
            logger.error(f"Failed to drop collection: {e}")
    else:
        logger.info(f"Collection '{collection_name}' does not exist. No action needed.")

    connections.disconnect("default")

if __name__ == "__main__":
    drop_milvus_collection()
