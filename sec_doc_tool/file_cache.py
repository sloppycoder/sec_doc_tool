import logging
import os
from functools import lru_cache
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)


def load_obj_from_cache(cache_file_path: str) -> bytes | None:
    cache_prefix = os.environ.get("CACHE_PREFIX", "")
    bucket_name, prefix = _cache_prefix(cache_prefix)
    if bucket_name:
        # use GCS bucket
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{cache_file_path}")
        if blob.exists():
            return blob.download_as_bytes()
    else:
        # load from local file system
        output_path = Path(prefix) / cache_file_path
        if output_path.exists():
            with open(output_path, "rb") as f:
                return f.read()
    logger.debug(f"Cache miss: {cache_file_path}")
    return None


def write_obj_to_cache(
    cache_file_path: str,
    obj: bytes,
) -> bool:
    cache_prefix = os.environ.get("CACHE_PREFIX", "")
    bucket_name, prefix = _cache_prefix(cache_prefix)
    if bucket_name:
        # use GCS bucket
        bucket = _gcs_client().bucket(bucket_name)
        blob = bucket.blob(f"{prefix}/{cache_file_path}")
        blob.upload_from_string(obj)
        return True
    elif prefix and len(prefix) > 3:
        # save to local file system
        output_path = Path(prefix) / cache_file_path
        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(obj)
        logger.debug(f"Cache written: {cache_file_path}")
        return True
    return False


@lru_cache(maxsize=1)
def _gcs_client():
    return storage.Client()


def _cache_prefix(storage_base_path: str):
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
