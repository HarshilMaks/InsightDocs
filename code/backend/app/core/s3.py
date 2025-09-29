"""
S3 Utilities
Low-level helpers for interacting with AWS S3.
Supports presigned URLs, async upload/download, and safe bucket management.
"""

import logging
from typing import Dict, Any, List, Optional, Union

import boto3
import aioboto3
from botocore.exceptions import ClientError

from core.config import settings

# -------------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StorageError(Exception):
    """Custom exception for S3 storage errors."""


def _boto3_client():
    """Create a boto3 S3 client with settings or fallback IAM credentials."""
    return boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    )


def build_s3_key(filename: str, prefix: Optional[str] = None) -> str:
    """Build S3 object key using optional prefix."""
    prefix = prefix if prefix is not None else getattr(settings, "S3_UPLOAD_PREFIX", "")
    prefix = prefix.rstrip("/") if prefix else ""
    return f"{prefix}/{filename}" if prefix else filename


# -------------------------------------------------------------------------
# Presigned URLs
# -------------------------------------------------------------------------

def generate_presigned_post(
    filename: str,
    content_type: Optional[str] = None,
    expires_in: int = 3600,
    bucket: Optional[str] = None,
    acl: str = "private"
) -> Dict[str, Any]:
    """Generate presigned POST data for direct browser uploads."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    client = _boto3_client()
    key = build_s3_key(filename)

    fields = {"acl": acl}
    conditions: List[Union[Dict[str, str], List[Any]]] = [{"acl": acl}]
    if content_type:
        fields["Content-Type"] = content_type
        conditions.append({"Content-Type": content_type})

    try:
        post = client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_in,
        )
        post["s3_key"] = key
        post["bucket"] = bucket
        return post
    except ClientError as exc:
        logger.exception("Presigned POST generation failed for %s", key, exc_info=True)
        raise StorageError(f"Presigned POST generation failed: {str(exc)}")


def generate_presigned_get_url(
    s3_key: str,
    expires_in: int = 3600,
    bucket: Optional[str] = None
) -> str:
    """Generate a presigned GET URL for an object."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    client = _boto3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )
    except ClientError as exc:
        logger.exception("Presigned GET URL generation failed for %s", s3_key, exc_info=True)
        raise StorageError(f"Presigned GET URL generation failed: {str(exc)}")


# -------------------------------------------------------------------------
# Async operations
# -------------------------------------------------------------------------

async def upload_bytes(
    s3_key: str,
    content: bytes,
    content_type: Optional[str] = None,
    bucket: Optional[str] = None
) -> Dict[str, str]:
    """Upload raw bytes to S3 asynchronously."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    session = aioboto3.Session()
    extra = {"ContentType": content_type} if content_type else {}

    try:
        async with session.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
            region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
        ) as s3:
            await s3.put_object(Bucket=bucket, Key=s3_key, Body=content, **extra)
            logger.info("Uploaded %s (%d bytes) to s3://%s/%s", s3_key, len(content), bucket, s3_key)
            return {"bucket": bucket, "key": s3_key}
    except ClientError as exc:
        logger.exception("Async upload failed for %s", s3_key, exc_info=True)
        raise StorageError(f"S3 upload failed: {str(exc)}")


async def download_bytes(s3_key: str, bucket: Optional[str] = None) -> bytes:
    """Download an S3 object and return its bytes."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
            region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
        ) as s3:
            resp = await s3.get_object(Bucket=bucket, Key=s3_key)
            return await resp["Body"].read()
    except ClientError as exc:
        logger.exception("Async download failed for %s", s3_key, exc_info=True)
        raise StorageError(f"S3 download failed: {str(exc)}")


async def delete_object(s3_key: str, bucket: Optional[str] = None) -> Dict[str, str]:
    """Delete an S3 object asynchronously."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
            region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
        ) as s3:
            await s3.delete_object(Bucket=bucket, Key=s3_key)
            logger.info("Deleted s3://%s/%s", bucket, s3_key)
            return {"bucket": bucket, "key": s3_key}
    except ClientError as exc:
        logger.exception("Async delete failed for %s", s3_key, exc_info=True)
        raise StorageError(f"S3 delete failed: {str(exc)}")


async def list_objects(
    prefix: Optional[str] = None,
    bucket: Optional[str] = None,
    max_keys: int = 100
) -> List[Dict[str, Any]]:
    """List objects under a prefix (returns list of dicts)."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    prefix = prefix if prefix is not None else getattr(settings, "S3_UPLOAD_PREFIX", "")
    if not bucket:
        raise StorageError("S3 bucket not configured")

    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None) or None,
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None) or None,
            region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            page_iter = paginator.paginate(
                Bucket=bucket, Prefix=prefix, PaginationConfig={"MaxItems": max_keys}
            )
            results: List[Dict[str, Any]] = []
            async for page in page_iter:
                for obj in page.get("Contents", []):
                    results.append({
                        "Key": obj["Key"],
                        "Size": obj["Size"],
                        "LastModified": obj["LastModified"],
                    })
            return results
    except ClientError as exc:
        logger.exception("Async list_objects failed for prefix=%s", prefix, exc_info=True)
        raise StorageError(f"S3 list_objects failed: {str(exc)}")


# -------------------------------------------------------------------------
# Bucket helpers
# -------------------------------------------------------------------------

def ensure_bucket_exists(bucket: Optional[str] = None, create_if_missing: bool = False) -> bool:
    """Check if a bucket exists. Optionally create it."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise StorageError("S3 bucket not configured")

    client = _boto3_client()
    try:
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        if not create_if_missing:
            return False
        region = getattr(settings, "AWS_DEFAULT_REGION", None)
        create_args = {"Bucket": bucket}
        if region and region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {"LocationConstraint": region}
        try:
            client.create_bucket(**create_args)
            logger.info("Created bucket %s", bucket)
            return True
        except ClientError as exc:
            logger.exception("Failed to create bucket %s", bucket, exc_info=True)
            raise StorageError(f"Failed to create bucket {bucket}: {str(exc)}")


def object_exists(s3_key: str, bucket: Optional[str] = None) -> bool:
    """Check if an object exists in S3."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    client = _boto3_client()
    try:
        client.head_object(Bucket=bucket, Key=s3_key)
        return True
    except ClientError:
        return False


def get_object_metadata(s3_key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
    """Get metadata (size, ETag, last-modified) for an object."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    client = _boto3_client()
    try:
        resp = client.head_object(Bucket=bucket, Key=s3_key)
        return resp
    except ClientError as exc:
        logger.exception("Failed to fetch metadata for %s", s3_key, exc_info=True)
        raise StorageError(f"Metadata retrieval failed: {str(exc)}")


def copy_object(src_key: str, dest_key: str, bucket: Optional[str] = None) -> Dict[str, str]:
    """Copy an existing object within the same bucket."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    client = _boto3_client()
    try:
        client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": src_key},
            Key=dest_key,
        )
        logger.info("Copied s3://%s/%s → s3://%s/%s", bucket, src_key, bucket, dest_key)
        return {"bucket": bucket, "source": src_key, "destination": dest_key}
    except ClientError as exc:
        logger.exception("Failed to copy %s → %s", src_key, dest_key, exc_info=True)
        raise StorageError(f"S3 copy failed: {str(exc)}")