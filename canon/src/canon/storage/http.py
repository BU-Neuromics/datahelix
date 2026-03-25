"""HTTPStorageAdapter — read-only adapter for HTTP/HTTPS URIs."""

from __future__ import annotations

from pathlib import Path

import httpx

from canon.exceptions import CanonStorageError
from canon.storage.base import StorageAdapter


class HTTPStorageAdapter(StorageAdapter):
    """Read-only storage adapter for HTTP and HTTPS URIs.

    Downloads files via httpx streaming. put() is not supported.
    Registered as both 'https' and 'http' entry points.
    """

    name = "https"
    uri_schemes = ["https", "http"]

    def put(self, local_path: str | Path, dest_uri: str) -> str:
        raise CanonStorageError("HTTP adapter is read-only")

    def build_dest_uri(self, entity_type: str, entity_id: str, filename: str) -> str:
        raise CanonStorageError("HTTP adapter is read-only")

    def get(self, uri: str, local_dir: str | Path) -> Path:
        """Stream file from HTTP/HTTPS URI to local_dir.

        Returns:
            Local Path to the downloaded file.

        Raises:
            CanonStorageError: on HTTP error or network failure.
        """
        filename = uri.split("/")[-1]
        dest = Path(local_dir) / filename

        try:
            with httpx.stream("GET", uri) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise CanonStorageError(
                        f"HTTP {response.status_code} downloading {uri}"
                    )
                with dest.open("wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        except CanonStorageError:
            raise
        except Exception as e:
            raise CanonStorageError(
                f"Network error downloading {uri}: {e}"
            ) from e

        return dest

    def exists(self, uri: str) -> bool:
        """Return True if a HEAD request to the URI returns 2xx.

        Never raises — returns False on any error.
        """
        try:
            response = httpx.head(uri)
            return 200 <= response.status_code < 300
        except Exception:
            return False
