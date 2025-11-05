"""File storage utilities for S3/MinIO."""
from typing import Optional
import logging
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from backend.config import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Handles file storage operations with S3/MinIO."""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.s3_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Created bucket {self.bucket_name}")
            except Exception as e:
                logger.error(f"Error creating bucket: {e}")
    
    async def store_file(
        self,
        file_path: str,
        filename: Optional[str] = None
    ) -> str:
        """Store a file in S3/MinIO.
        
        Args:
            file_path: Local file path
            filename: Optional custom filename
            
        Returns:
            S3 object key
        """
        try:
            if filename is None:
                filename = Path(file_path).name
            
            object_key = f"documents/{filename}"
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key
            )
            
            logger.info(f"Uploaded file to {object_key}")
            return object_key
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    async def retrieve_file(
        self,
        object_key: str,
        local_path: str
    ) -> str:
        """Retrieve a file from S3/MinIO.
        
        Args:
            object_key: S3 object key
            local_path: Local path to save file
            
        Returns:
            Local file path
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                local_path
            )
            
            logger.info(f"Downloaded file from {object_key}")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    async def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3/MinIO.
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted file {object_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for file access.
        
        Args:
            object_key: S3 object key
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL for {object_key}")
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
