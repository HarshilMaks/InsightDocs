import os
import time
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from utils.logger import get_logger, log_file_processing
from services.llm_service import LLMService
from core import s3
from core.milvus import insert_embeddings
from models.db_models import Document, DocumentChunk

logger = get_logger("files")


class FileService:
    """Service for handling file ingestion pipeline: S3 → DB → Milvus"""

    def __init__(self):
        self.llm = LLMService()

    async def upload_and_process(
        self,
        file,
        document_id: str,
        db: AsyncSession,
        background_tasks=None,
        user_id: str = "system",  # could come from auth
    ) -> Dict[str, Any]:
        """
        Handles upload to S3, metadata DB insert,
        text extraction, embedding, and Milvus indexing.
        """

        start_time = time.time()
        filename = file.filename
        file_ext = os.path.splitext(filename)[1].lower()
        bucket = getattr(s3.settings, "S3_BUCKET_NAME")

        try:
            # 1. Upload raw file → S3
            s3_key = s3.build_s3_key(filename, prefix=s3.settings.S3_UPLOAD_PREFIX)
            file_bytes = await file.read()
            await s3.upload_bytes(s3_key, file_bytes, content_type=file.content_type, bucket=bucket)
            file_size = len(file_bytes)

            # 2. Insert document metadata into Postgres
            doc = Document(
                id=document_id,
                user_id=user_id,
                filename=filename,
                file_type=file_ext.replace(".", ""),
                file_size=file_size,
                s3_bucket=bucket,
                s3_key=s3_key,
                status="processing",
            )
            db.add(doc)
            await db.flush()  # so chunks can reference it

            # 3. Extract text (stub for now)
            text = await self._extract_text_stub(file_bytes, file_ext)

            # 4. Chunk text
            chunks = self._chunk_text(text, chunk_size=500)

            # 5. Embed + store in Milvus + DB
            embeddings_payload: List[Dict[str, Any]] = []
            for idx, chunk_content in enumerate(chunks):
                embedding = await self.llm.embed_text(chunk_content)

                # -> for Milvus
                embeddings_payload.append({"embedding": embedding, "content": chunk_content})

                # -> for Postgres
                chunk_row = DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=chunk_content,
                    embedding_model=s3.settings.GEMINI_MODEL,
                    embedding_dimension=len(embedding),
                )
                db.add(chunk_row)

            if embeddings_payload:
                insert_embeddings(file_id=document_id, source=filename, chunks=embeddings_payload)

            # update Document status
            doc.status = "completed"
            await db.commit()

            processing_time = time.time() - start_time
            log_file_processing(
                file_id=document_id,
                filename=filename,
                file_size=file_size,
                processing_time=processing_time,
                status="completed",
            )

            return {
                "document_id": document_id,
                "filename": filename,
                "file_size": file_size,
                "file_type": file_ext,
                "status": "completed",
                "s3_key": s3_key,
                "processing_time": processing_time,
                "num_chunks": len(chunks),
            }

        except Exception as e:
            # Mark DB record as failed if exists
            if "doc" in locals():
                doc.status = "failed"
                doc.error_message = str(e)
                await db.commit()

            log_file_processing(
                file_id=document_id,
                filename=filename,
                file_size=None,
                processing_time=time.time() - start_time,
                status="failed",
                error=str(e),
            )
            raise

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    async def _extract_text_stub(self, file_bytes: bytes, file_ext: str) -> str:
        """
        Stub method for text extraction.
        Replace with pdfplumber, python-docx, etc. as needed.
        """
        if file_ext == ".pdf":
            return "Stub: extracted PDF text..."
        elif file_ext == ".docx":
            return "Stub: extracted DOCX text..."
        elif file_ext in [".txt", ".csv"]:
            return file_bytes.decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """
        Simple character-based chunking. Replace with smarter
        sentence/paragraph splitters when needed.
        """
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]