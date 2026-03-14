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

def check_milvus_connection():
    """Check Milvus connection and list collections."""
    uri = settings.milvus_uri
    token = settings.milvus_token
    
    # Mask token for logging
    logger.info(f"Connecting to Milvus at {uri}")
    logger.info(f"Using token starting with: {token[:4]}...")
    
    try:
        connections.connect(alias="default", uri=uri, token=token)
        logger.info("Connected successfully.")
        
        collections = utility.list_collections()
        logger.info(f"Available collections: {collections}")
        
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {e}")
    finally:
        try:
            connections.disconnect("default")
        except:
            pass

if __name__ == "__main__":
    check_milvus_connection()
