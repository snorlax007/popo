from __future__ import annotations

import hashlib
import logging

from ..config import settings

logger = logging.getLogger(__name__)


def _get_s3():
    if not settings.aws_access_key_id:
        return None
    try:
        import boto3
        kwargs = {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        }
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        return boto3.client("s3", **kwargs)
    except Exception as exc:
        logger.warning("S3 client init failed: %s", exc)
        return None


async def upload_firmware(content: bytes, version: str) -> tuple[str, str]:
    """Upload firmware binary; return (s3_key, sha256)."""
    sha256 = hashlib.sha256(content).hexdigest()
    key = f"firmware/popo-{version}.bin"

    s3 = _get_s3()
    if s3:
        try:
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=content,
                ContentType="application/octet-stream",
                Metadata={"sha256": sha256, "version": version},
            )
            return key, sha256
        except Exception as exc:
            logger.error("S3 upload failed: %s", exc)
            raise

    # Local dev fallback: store in /tmp
    import aiofiles
    local_path = f"/tmp/popo-{version}.bin"
    async with aiofiles.open(local_path, "wb") as f:
        await f.write(content)
    logger.info("S3 not configured — firmware saved locally at %s", local_path)
    return local_path, sha256


def generate_download_url(s3_key: str) -> str:
    """Generate a pre-signed S3 URL or a local path URL for dev."""
    s3 = _get_s3()
    if s3 and not s3_key.startswith("/tmp"):
        try:
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": s3_key},
                ExpiresIn=settings.ota_url_expiry,
            )
        except Exception as exc:
            logger.warning("Pre-sign failed: %s", exc)
    return f"/api/ota/download/{s3_key.replace('/', '_')}"
