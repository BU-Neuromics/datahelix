"""S3StorageAdapter — Amazon S3 storage backend for Canon."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from canon.exceptions import CanonStorageError
from canon.storage.base import StorageAdapter


def _build_boto3_client(credentials: str, region_name: str | None = None) -> Any:
    """Construct a boto3 S3 client based on a credentials config string.

    credentials values:
        "env"            — use AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars
        "instance_role"  — use EC2/ECS instance role (no explicit credentials)
        "profile:<name>" — use a named AWS CLI profile

    Raises:
        CanonStorageError: if boto3 is not installed.
    """
    try:
        import boto3
        import boto3.session
    except ImportError as exc:
        raise CanonStorageError(
            "boto3 is required for S3 storage. "
            "Install it with: pip install canon[storage-s3]"
        ) from exc

    kwargs: dict[str, Any] = {}
    if region_name:
        kwargs["region_name"] = region_name

    if credentials.startswith("profile:"):
        profile_name = credentials[len("profile:"):]
        session = boto3.session.Session(profile_name=profile_name)
        return session.client("s3", **kwargs)

    # "env" and "instance_role" both rely on boto3's default credential chain
    return boto3.client("s3", **kwargs)


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    """Parse s3://bucket/key or s3a://bucket/key → (bucket, key).

    Raises:
        CanonStorageError: if the URI is malformed.
    """
    if "://" not in uri:
        raise CanonStorageError(f"Invalid S3 URI (missing scheme): {uri!r}")
    _, rest = uri.split("://", 1)
    if "/" not in rest:
        raise CanonStorageError(f"Invalid S3 URI (missing key path): {uri!r}")
    bucket, key = rest.split("/", 1)
    if not bucket:
        raise CanonStorageError(f"Invalid S3 URI (empty bucket): {uri!r}")
    return bucket, key


class S3StorageAdapter(StorageAdapter):
    """Storage adapter for Amazon S3 (and S3-compatible) backends.

    Handles s3:// and s3a:// URIs. Requires boto3 (install canon[storage-s3]).

    Constructor args:
        bucket:      S3 bucket name.
        prefix:      Key prefix for all stored objects (default: "").
        credentials: "env" | "instance_role" | "profile:<name>" (default: "env").
        region_name: Optional AWS region override.
    """

    name = "s3"
    uri_schemes = ["s3", "s3a"]

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        credentials: str = "env",
        region_name: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._client = _build_boto3_client(credentials, region_name)

    def put(self, local_path: str | Path, dest_uri: str) -> str:
        """Upload a local file to S3.

        Args:
            local_path: Local file to upload.
            dest_uri:   Destination s3:// URI.

        Returns:
            Canonical s3:// URI of the stored object.

        Raises:
            CanonStorageError: if the source file doesn't exist or upload fails.
        """
        src = Path(local_path)
        if not src.exists():
            raise CanonStorageError(f"Source file not found: {src}")

        _, key = _parse_s3_uri(dest_uri)
        try:
            self._client.upload_file(str(src), self._bucket, key)
        except CanonStorageError:
            raise
        except Exception as e:
            raise CanonStorageError(
                f"Failed to upload {src} to s3://{self._bucket}/{key}: {e}"
            ) from e

        return f"s3://{self._bucket}/{key}"

    def get(self, uri: str, local_dir: str | Path) -> Path:
        """Download an S3 object to a local directory.

        Args:
            uri:       s3:// URI of the object to download.
            local_dir: Local directory to download into.

        Returns:
            Local Path of the downloaded file.

        Raises:
            CanonStorageError: if download fails.
        """
        _, key = _parse_s3_uri(uri)
        filename = Path(key).name
        dest = Path(local_dir) / filename

        try:
            self._client.download_file(self._bucket, key, str(dest))
        except Exception as e:
            raise CanonStorageError(
                f"Failed to download s3://{self._bucket}/{key}: {e}"
            ) from e

        return dest

    def exists(self, uri: str) -> bool:
        """Return True if the S3 object exists, False otherwise. Never raises."""
        try:
            _, key = _parse_s3_uri(uri)
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        """Construct a destination S3 URI.

        Format: s3://bucket/[prefix/]entity_type_lower/entity_id/filename
        """
        parts: list[str] = []
        if self._prefix:
            parts.append(self._prefix)
        parts.extend([entity_type.lower(), entity_id, filename])
        key = "/".join(parts)
        return f"s3://{self._bucket}/{key}"
