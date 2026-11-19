# ============================================
# SupplyChainIQ — Storage Abstraction (S3/Local)
# ============================================
import os
import json
from pathlib import Path
from typing import Optional
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class StorageBackend:
    """Abstraction over S3 and local filesystem for raw data storage."""

    def __init__(self):
        self.use_s3 = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        self.local_root = Path(settings.LOCAL_STORAGE_PATH)
        if self.use_s3:
            import boto3
            self.s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            self.bucket = settings.S3_BUCKET_NAME
            logger.info("storage_backend", backend="s3", bucket=self.bucket)
        else:
            self.s3 = None
            self.bucket = None
            self._ensure_local_dirs()
            logger.info("storage_backend", backend="local", path=str(self.local_root))

    def _ensure_local_dirs(self):
        """Create the local storage directory structure."""
        dirs = [
            "raw/shipments", "raw/tracking_events", "raw/warehouse_events", "raw/weather",
            "processed/shipments", "processed/tracking_events",
            "models/delay_classifier", "models/delay_regressor",
            "reports",
        ]
        for d in dirs:
            (self.local_root / d).mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> bool:
        """Store a file by key (S3 key or local relative path)."""
        try:
            if self.use_s3:
                self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
            else:
                path = self.local_root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return True
        except Exception as e:
            logger.error("storage_put_error", key=key, error=str(e))
            return False

    def put_json(self, key: str, obj: dict) -> bool:
        return self.put(key, json.dumps(obj, default=str).encode("utf-8"))

    def get(self, key: str) -> Optional[bytes]:
        """Retrieve a file by key."""
        try:
            if self.use_s3:
                resp = self.s3.get_object(Bucket=self.bucket, Key=key)
                return resp["Body"].read()
            else:
                path = self.local_root / key
                if path.exists():
                    return path.read_bytes()
                return None
        except Exception as e:
            logger.error("storage_get_error", key=key, error=str(e))
            return None

    def get_json(self, key: str) -> Optional[dict]:
        data = self.get(key)
        return json.loads(data) if data else None

    def list_keys(self, prefix: str) -> list:
        """List keys under a prefix."""
        try:
            if self.use_s3:
                resp = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
                return [obj["Key"] for obj in resp.get("Contents", [])]
            else:
                base = self.local_root / prefix
                if not base.exists():
                    return []
                return [str(p.relative_to(self.local_root)) for p in base.rglob("*") if p.is_file()]
        except Exception as e:
            logger.error("storage_list_error", prefix=prefix, error=str(e))
            return []


# Singleton
storage = StorageBackend()
