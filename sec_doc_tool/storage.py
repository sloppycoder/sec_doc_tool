import logging
import os
from functools import lru_cache
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)


def load_obj_from_storage(obj_path: str) -> bytes | None:
    storage_prefix = _get_prefix()
    bucket_name, prefix = _storage_prefix(storage_prefix)
    if bucket_name:
        # use GCS bucket
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{obj_path}")
        if blob.exists():
            return blob.download_as_bytes()
    else:
        # load from local file system
        output_path = Path(prefix) / obj_path
        if output_path.exists():
            with open(output_path, "rb") as f:
                return f.read()
    logger.debug(f"Not found in storage: {obj_path}")
    return None


def write_obj_to_storage(
    obj_path: str,
    obj: bytes,
) -> bool:
    storage_prefix = _get_prefix()
    bucket_name, prefix = _storage_prefix(storage_prefix)
    if bucket_name:
        # use GCS bucket
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{obj_path}")
        blob.upload_from_string(obj)
        logger.debug(f"Object written: {obj_path}")
        return True
    elif prefix and len(prefix) > 3:
        # save to local file system
        output_path = Path(prefix) / obj_path
        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(obj)
        logger.debug(f"Object written: {obj_path}")
        return True
    return False


def delete_obj_from_storage(
    obj_path: str,
    obj: bytes,
) -> bool:
    storage_prefix = _get_prefix()
    bucket_name, prefix = _storage_prefix(storage_prefix)
    if bucket_name:
        # use GCS bucket
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{obj_path}")
        blob.delete()
        logger.debug("Object deleted: {obj_path}")
        return True
    elif prefix and len(prefix) > 3:
        output_path = Path(prefix) / obj_path
        if os.path.exists(output_path):
            os.remove(output_path)
            logger.debug("Object deleted: {obj_path}")
        else:
            logger.debug("Object not exist: {obj_path}")

        return True
    return False


@lru_cache(maxsize=1)
def _gcs_client():
    return storage.Client()


def _storage_prefix(storage_base_path: str):
    # return tuple of (bucket_name, prefix)
    # if the env var does not beginw with "gs://", returns ""
    if storage_base_path.startswith("gs://"):
        parts = storage_base_path[5:].split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""
    else:
        if storage_base_path.startswith("/"):
            return None, storage_base_path
        else:
            local_path = Path(__file__).parent.parent / storage_base_path
            return None, str(local_path)


def _get_prefix():
    cache_prefix = os.environ.get("CACHE_PREFIX", "")
    storage_prefix = os.environ.get("STORAGE_PREFIX", "")
    if storage_prefix:
        return storage_prefix
    elif cache_prefix:
        # backward compatibility
        logger.debug("Using CACHE_PREFIX when STORAGE_PREFIX is not set")
        return cache_prefix
    else:
        logger.info(
            "Neither STORAGE_CACHE nor CACHE_PREFIX is set, storage will be disaled"
        )
        return ""
