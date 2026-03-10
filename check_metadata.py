from backend.models.database import Base
from backend.models.schemas import User, Document, DocumentChunk, Task, Query
print("Tables in metadata:", list(Base.metadata.tables.keys()))
