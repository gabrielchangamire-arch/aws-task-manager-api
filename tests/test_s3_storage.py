"""S3 attachment flow exercised against a moto-mocked S3."""
import io
import os

import boto3
import pytest
from moto import mock_aws

from app.config import get_settings
from app.storage import s3 as s3mod


@pytest.fixture
def s3_env(monkeypatch):
    monkeypatch.setenv("S3_ENABLED", "true")
    monkeypatch.setenv("S3_BUCKET_NAME", "task-attachments-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_get_s3_client_disabled(monkeypatch):
    monkeypatch.setenv("S3_ENABLED", "false")
    get_settings.cache_clear()
    with pytest.raises(s3mod.S3Disabled):
        s3mod.get_s3_client()


@mock_aws
def test_upload_attachment_writes_to_bucket(s3_env):
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="task-attachments-test")

    real_client, bucket = s3mod.get_s3_client()
    key = s3mod.upload_attachment(real_client, bucket, "task-123", "note.txt", io.BytesIO(b"hello"))

    assert key.startswith("tasks/task-123/")
    obj = client.get_object(Bucket=bucket, Key=key)
    assert obj["Body"].read() == b"hello"
