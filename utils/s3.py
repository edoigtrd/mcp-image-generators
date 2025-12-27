import os
from urllib.parse import urlparse
from pathlib import PurePosixPath
import uuid

import requests
import boto3
from botocore.config import Config


def validate_s3_env_vars() -> bool:
    required_vars = [
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_REGION",
        "S3_CDN_URL",
        "S3_BUCKET",
    ]

    for var_name in required_vars:
        value = os.environ.get(var_name, "")
        if value.strip() == "":
            return False

    return True


def create_s3_client():
    validate_s3_env_vars()  # Validate on creation

    endpoint_url = os.environ.get("S3_ENDPOINT_URL", "")
    region = os.environ.get("S3_REGION", "")
    access_key = os.environ.get("S3_ACCESS_KEY", "")
    secret_key = os.environ.get("S3_SECRET_KEY", "")

    # S3-compatible endpoints (MinIO/Scaleway) usually need path-style addressing
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(s3={"addressing_style": "path"}),
    )
    return s3


def fetch_url(url: str) -> tuple[bytes, str]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "application/octet-stream")
    return response.content, content_type


def copy_url_to_s3(source_url: str, destination_key: str | None = None) -> str:
    s3 = create_s3_client()
    bucket = os.environ.get("S3_BUCKET")

    if not (source_url.startswith("http://") or source_url.startswith("https://")):
        raise ValueError("source_url must be a valid HTTP/HTTPS URL")

    # set destination key as uuid4 + original file extension
    parsed_url = urlparse(source_url)
    original_path = PurePosixPath(parsed_url.path)
    file_extension = original_path.suffix
    destination_key = f"{uuid.uuid4()}{file_extension}"
    
    # Download then upload
    try:
        data, content_type = fetch_url(source_url)

        s3.put_object(
            Bucket=bucket,
            Key=destination_key,
            Body=data,
            ContentType=content_type,
            ACL="public-read",
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to copy {source_url} to S3: {exc}") from exc

    # Build public URL
    cdn_url = os.environ.get("S3_CDN_URL", "")
    if cdn_url:
        public_url = f"{cdn_url.rstrip('/')}/{destination_key}"
    else:
        # Kept as a close translation of your TS code (even if not very useful)
        public_url = f"{cdn_url}/{destination_key}"

    return public_url


__all__ = ["copy_url_to_s3", "validate_s3_env_vars"]
