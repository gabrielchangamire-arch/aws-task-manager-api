"""Optional S3 attachment storage.

The API works without S3 (the attachment endpoint just returns 503).
Set S3_ENABLED=true and S3_BUCKET_NAME to turn it on, either against
real AWS or against a local fake (e.g. moto, MinIO) in dev.
"""
from __future__ import annotations

import uuid
from typing import IO, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings


class S3Disabled(RuntimeError):
    pass


class S3UploadError(RuntimeError):
    pass


def get_s3_client() -> Tuple[object, str]:
    settings = get_settings()
    if not settings.s3_enabled:
        raise S3Disabled("S3 attachments are disabled. Set S3_ENABLED=true to enable.")
    if not settings.s3_bucket_name:
        raise S3Disabled("S3_BUCKET_NAME is not configured.")
    client = boto3.client("s3", region_name=settings.aws_region)
    return client, settings.s3_bucket_name


def build_key(task_id: str, filename: str) -> str:
    safe = filename.replace("/", "_").replace("\\", "_")
    return f"tasks/{task_id}/{uuid.uuid4().hex}_{safe}"


def upload_attachment(client, bucket: str, task_id: str, filename: str, fileobj: IO[bytes]) -> str:
    key = build_key(task_id, filename)
    try:
        client.upload_fileobj(fileobj, bucket, key)
    except (BotoCoreError, ClientError) as exc:
        raise S3UploadError(f"failed to upload to s3: {exc}") from exc
    return key
