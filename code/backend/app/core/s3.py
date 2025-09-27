import logging
import boto3
import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _boto3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    )


def build_s3_key(filename, prefix=None):
    """Build S3 key using optional prefix."""
    prefix = prefix if prefix is not None else getattr(settings, "S3_UPLOAD_PREFIX", "")
    prefix = prefix.rstrip("/") if prefix else ""
    return f"{prefix}/{filename}" if prefix else filename


def generate_presigned_post(filename, content_type=None, expires_in=3600, bucket=None, acl="private"):
    """
    Generate presigned POST data for direct browser upload.
    Returns dict with 'url', 'fields', and 's3_key'.
    """
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    key = build_s3_key(filename)
    client = _boto3_client()

    fields = {"acl": acl}
    conditions = [{"acl": acl}]
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
        logger.exception("Presigned POST generation failed for %s: %s", key, exc)
        raise


def generate_presigned_get_url(s3_key, expires_in=3600, bucket=None):
    """Generate presigned GET URL for an object."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    client = _boto3_client()
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as exc:
        logger.exception("Presigned GET URL generation failed for %s: %s", s3_key, exc)
        raise


async def upload_bytes(s3_key, content, content_type=None, bucket=None):
    """Upload raw bytes to S3 asynchronously."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    session = aioboto3.Session()
    async with session.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    ) as s3:
        extra = {}
        if content_type:
            extra["ContentType"] = content_type
        try:
            await s3.put_object(Bucket=bucket, Key=s3_key, Body=content, **extra)
            logger.debug("Uploaded to s3://%s/%s", bucket, s3_key)
            return {"bucket": bucket, "key": s3_key}
        except ClientError as exc:
            logger.exception("Async upload failed for %s: %s", s3_key, exc)
            raise


async def download_bytes(s3_key, bucket=None):
    """Download an S3 object and return its bytes."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    session = aioboto3.Session()
    async with session.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    ) as s3:
        try:
            resp = await s3.get_object(Bucket=bucket, Key=s3_key)
            body = await resp["Body"].read()
            return body
        except ClientError as exc:
            logger.exception("Async download failed for %s: %s", s3_key, exc)
            raise


async def delete_object(s3_key, bucket=None):
    """Delete an object from S3."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    session = aioboto3.Session()
    async with session.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    ) as s3:
        try:
            await s3.delete_object(Bucket=bucket, Key=s3_key)
            logger.debug("Deleted s3://%s/%s", bucket, s3_key)
            return {"bucket": bucket, "key": s3_key}
        except ClientError as exc:
            logger.exception("Async delete failed for %s: %s", s3_key, exc)
            raise


async def list_objects(prefix=None, bucket=None, max_keys=100):
    """List objects under a prefix (returns list of dicts)."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    prefix = prefix if prefix is not None else getattr(settings, "S3_UPLOAD_PREFIX", "")
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

    session = aioboto3.Session()
    async with session.client(
        "s3",
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        region_name=getattr(settings, "AWS_DEFAULT_REGION", None),
    ) as s3:
        try:
            paginator = s3.get_paginator("list_objects_v2")
            page_iter = paginator.paginate(Bucket=bucket, Prefix=prefix, PaginationConfig={"MaxItems": max_keys})
            results = []
            async for page in page_iter:
                for obj in page.get("Contents", []):
                    results.append({"Key": obj["Key"], "Size": obj["Size"], "LastModified": obj["LastModified"]})
            return results
        except ClientError as exc:
            logger.exception("Async list_objects failed for prefix=%s: %s", prefix, exc)
            raise


def ensure_bucket_exists(bucket=None, create_if_missing=False):
    """Check if a bucket exists. Optionally create it."""
    bucket = bucket or getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        raise RuntimeError("S3 bucket not configured")

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
            logger.exception("Failed to create bucket %s: %s", bucket, exc)
            raise
