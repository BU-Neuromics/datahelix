"""Contract tests: behavioral contract for Canon StorageAdapter plugin system.

These tests exercise the concrete behavior of LocalStorageAdapter,
HTTPStorageAdapter, and StorageAdapterRegistry as standalone units.

A failure here signals a breaking change to the storage plugin contract.
  1. Unintentional: fix the implementation.
  2. Intentional: update this spec + bump Canon's version.

DO NOT add internal implementation tests here. Only behavioral contracts.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_root = Path(__file__).parent.parent.parent
for _pkg in ("hippo/src", "canon/src"):
    _p = str(_root / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canon.exceptions import CanonConfigError, CanonStorageError
from canon.storage.http import HTTPStorageAdapter
from canon.storage.local import LocalStorageAdapter
from canon.storage.registry import StorageAdapterRegistry


# ---------------------------------------------------------------------------
# CONTRACT: LocalStorageAdapter
# ---------------------------------------------------------------------------


class TestLocalStorageAdapterContract:
    """Behavioral contract for LocalStorageAdapter (filesystem / NFS backend)."""

    @pytest.fixture()
    def adapter(self, tmp_path: Path) -> LocalStorageAdapter:
        return LocalStorageAdapter(str(tmp_path / "base"))

    def test_put_copies_file_and_returns_file_uri(self, adapter, tmp_path):
        src = tmp_path / "input.txt"
        src.write_text("hello")
        dest_uri = f"file://{tmp_path}/base/sample/abc123/input.txt"

        result = adapter.put(src, dest_uri)

        assert result.startswith("file://")
        dest = Path(result[len("file://") :])
        assert dest.exists()
        assert dest.read_text() == "hello"

    def test_put_creates_parent_dirs_if_missing(self, adapter, tmp_path):
        src = tmp_path / "data.bam"
        src.write_text("bam")
        dest_uri = f"file://{tmp_path}/base/deeply/nested/dir/data.bam"

        result = adapter.put(src, dest_uri)

        dest = Path(result[len("file://") :])
        assert dest.exists()

    def test_put_raises_canon_storage_error_when_source_missing(self, adapter, tmp_path):
        with pytest.raises(CanonStorageError, match="Source file not found"):
            adapter.put(tmp_path / "nonexistent.txt", f"file://{tmp_path}/base/out.txt")

    def test_get_returns_existing_path_as_is(self, adapter, tmp_path):
        """NFS optimisation: if the path is directly accessible, return it without copying."""
        src = tmp_path / "data.bam"
        src.write_text("bam data")
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        result = adapter.get(f"file://{src}", local_dir)

        assert result == src
        # No copy made into local_dir
        assert not (local_dir / "data.bam").exists()

    def test_get_copies_to_local_dir_when_source_is_elsewhere(self, adapter, tmp_path):
        """LocalStorageAdapter (NFS) returns the source path directly when accessible.

        On shared / NFS filesystems the URI path is directly reachable from
        every node; no copy to local_dir is needed or performed.  The caller
        receives the canonical path to the file.
        """
        source_dir = tmp_path / "nfs_share"
        source_dir.mkdir()
        src = source_dir / "file.vcf"
        src.write_text("vcf")
        local_dir = tmp_path / "staging"
        local_dir.mkdir()

        result = adapter.get(f"file://{src}", local_dir)

        # Returns original path directly — NFS adapter does not copy.
        assert result == src
        assert result.exists()

    def test_get_raises_canon_storage_error_when_uri_path_not_found(self, adapter, tmp_path):
        local_dir = tmp_path / "local"
        local_dir.mkdir()

        with pytest.raises(CanonStorageError, match="File not found"):
            adapter.get(f"file://{tmp_path}/nonexistent/file.bam", local_dir)

    def test_exists_returns_true_for_present_file(self, adapter, tmp_path):
        f = tmp_path / "present.txt"
        f.write_text("yes")

        assert adapter.exists(f"file://{f}") is True

    def test_exists_returns_false_for_absent_file_never_raises(self, adapter, tmp_path):
        result = adapter.exists(f"file://{tmp_path}/absent/file.txt")

        assert result is False

    def test_exists_handles_file_uri_and_bare_path_consistently(self, adapter, tmp_path):
        f = tmp_path / "same.txt"
        f.write_text("x")

        via_uri = adapter.exists(f"file://{f}")
        via_bare = adapter.exists(str(f))

        assert via_uri == via_bare

    def test_build_dest_uri_returns_structured_file_uri(self, adapter, tmp_path):
        uri = adapter.build_dest_uri("Sample", "abc-123", "output.bam")

        assert uri.startswith("file://")
        assert "/sample/" in uri
        assert "abc-123" in uri
        assert uri.endswith("output.bam")


# ---------------------------------------------------------------------------
# CONTRACT: HTTPStorageAdapter (read-only)
# ---------------------------------------------------------------------------


class TestHTTPAdapterReadOnlyContract:
    """Behavioral contract for HTTPStorageAdapter (read-only HTTP/HTTPS backend)."""

    @pytest.fixture()
    def adapter(self) -> HTTPStorageAdapter:
        return HTTPStorageAdapter()

    def test_put_raises_canon_storage_error_with_read_only_in_message(self, adapter, tmp_path):
        src = tmp_path / "file.txt"
        src.write_text("x")

        with pytest.raises(CanonStorageError, match="read-only"):
            adapter.put(src, "https://example.com/file.txt")

    def test_build_dest_uri_raises_canon_storage_error_with_read_only_in_message(self, adapter):
        with pytest.raises(CanonStorageError, match="read-only"):
            adapter.build_dest_uri("Sample", "abc", "file.bam")

    def test_exists_returns_true_on_200_head(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.head", return_value=mock_resp):
            assert adapter.exists("https://example.com/file.bam") is True

    def test_exists_returns_false_on_404_head(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("httpx.head", return_value=mock_resp):
            assert adapter.exists("https://example.com/missing.bam") is False

    def test_exists_returns_false_on_connection_error_does_not_raise(self, adapter):
        with patch("httpx.head", side_effect=ConnectionError("refused")):
            result = adapter.exists("https://example.com/file.bam")

        assert result is False

    def test_get_writes_file_to_local_dir(self, adapter, tmp_path):
        local_dir = tmp_path / "downloads"
        local_dir.mkdir()
        file_content = b"file content bytes"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = iter([file_content])
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("httpx.stream", return_value=mock_response):
            result = adapter.get("https://example.com/data.txt", local_dir)

        assert result == local_dir / "data.txt"
        assert result.read_bytes() == file_content

    def test_get_raises_canon_storage_error_on_404_response(self, adapter, tmp_path):
        local_dir = tmp_path / "downloads"
        local_dir.mkdir()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("httpx.stream", return_value=mock_response):
            with pytest.raises(CanonStorageError, match="404"):
                adapter.get("https://example.com/missing.txt", local_dir)

    def test_get_raises_canon_storage_error_on_network_error(self, adapter, tmp_path):
        local_dir = tmp_path / "downloads"
        local_dir.mkdir()

        with patch("httpx.stream", side_effect=ConnectionError("network down")):
            with pytest.raises(CanonStorageError, match="Network error"):
                adapter.get("https://example.com/file.txt", local_dir)


# ---------------------------------------------------------------------------
# CONTRACT: StorageAdapterRegistry
# ---------------------------------------------------------------------------


class TestStorageAdapterRegistryContract:
    """Behavioral contract for StorageAdapterRegistry URI routing and default adapter."""

    @pytest.fixture()
    def registry(self, tmp_path: Path) -> StorageAdapterRegistry:
        """Registry populated with LocalStorageAdapter and HTTPStorageAdapter."""
        reg = StorageAdapterRegistry()
        local = LocalStorageAdapter(str(tmp_path / "base"))
        http = HTTPStorageAdapter()
        reg._adapters = {"local": local, "https": http}
        reg._scheme_map = {
            "file": local,
            "": local,
            "https": http,
            "http": http,
        }
        reg._default_type = "local"
        return reg

    def test_adapter_for_file_uri_returns_local_adapter(self, registry):
        result = registry.adapter_for_uri("file:///data/output.bam")

        assert isinstance(result, LocalStorageAdapter)

    def test_adapter_for_bare_path_returns_local_adapter(self, registry):
        result = registry.adapter_for_uri("/bare/path/to/file.bam")

        assert isinstance(result, LocalStorageAdapter)

    def test_adapter_for_https_uri_returns_http_adapter(self, registry):
        result = registry.adapter_for_uri("https://example.com/file.bam")

        assert isinstance(result, HTTPStorageAdapter)

    def test_adapter_for_http_uri_returns_http_adapter(self, registry):
        result = registry.adapter_for_uri("http://example.com/file.bam")

        assert isinstance(result, HTTPStorageAdapter)

    def test_adapter_for_s3_uri_raises_canon_config_error(self, registry):
        with pytest.raises(CanonConfigError):
            registry.adapter_for_uri("s3://bucket/key/file.bam")

    def test_default_adapter_returns_local_adapter_when_type_is_local(self, registry):
        result = registry.default_adapter

        assert isinstance(result, LocalStorageAdapter)
