"""Tests for StorageAdapter ABC, LocalStorageAdapter, and StorageAdapterRegistry."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from canon.exceptions import CanonError, CanonStorageError, CanonConfigError
from canon.storage.base import StorageAdapter


# ---------------------------------------------------------------------------
# CanonStorageError
# ---------------------------------------------------------------------------

def test_canon_storage_error_is_subclass_of_canon_error():
    err = CanonStorageError("disk full")
    assert isinstance(err, CanonError)


def test_canon_storage_error_message():
    err = CanonStorageError("cannot write to /tmp/out.bam")
    assert "cannot write" in str(err)


# ---------------------------------------------------------------------------
# StorageAdapter ABC
# ---------------------------------------------------------------------------

def test_storage_adapter_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        StorageAdapter()  # type: ignore[abstract]


def test_storage_adapter_subclass_must_implement_put_get_exists():
    class Incomplete(StorageAdapter):
        name = "incomplete"
        uri_schemes = []
        # Missing put, get, exists

    with pytest.raises(TypeError):
        Incomplete()


def test_storage_adapter_build_dest_uri_default_raises():
    class Minimal(StorageAdapter):
        name = "minimal"
        uri_schemes = []

        def put(self, local_path, dest_uri):
            pass

        def get(self, uri, local_dir):
            pass

        def exists(self, uri):
            return False

    adapter = Minimal()
    with pytest.raises(NotImplementedError):
        adapter.build_dest_uri("Foo", "id-1", "file.txt")


# ---------------------------------------------------------------------------
# LocalStorageAdapter — unit tests
# ---------------------------------------------------------------------------

from canon.storage.local import LocalStorageAdapter


def test_local_adapter_name():
    adapter = LocalStorageAdapter(base_path="/tmp/canon-storage")
    assert adapter.name == "local"


def test_local_adapter_uri_schemes():
    adapter = LocalStorageAdapter(base_path="/tmp/canon-storage")
    assert "file" in adapter.uri_schemes
    assert "" in adapter.uri_schemes


def test_local_adapter_put_copies_file(tmp_path):
    src = tmp_path / "input.bam"
    src.write_bytes(b"FAKE_BAM_DATA")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    dest_uri = f"file://{dest_dir}/output.bam"

    adapter = LocalStorageAdapter(base_path=str(tmp_path / "storage"))
    result_uri = adapter.put(str(src), dest_uri)

    dest_path = dest_dir / "output.bam"
    assert dest_path.exists()
    assert dest_path.read_bytes() == b"FAKE_BAM_DATA"
    assert result_uri.startswith("file://")
    assert "output.bam" in result_uri


def test_local_adapter_put_creates_parent_directories(tmp_path):
    src = tmp_path / "result.txt"
    src.write_text("hello")
    dest_uri = f"file://{tmp_path}/deep/nested/dir/result.txt"

    adapter = LocalStorageAdapter(base_path=str(tmp_path / "storage"))
    adapter.put(str(src), dest_uri)

    assert (tmp_path / "deep" / "nested" / "dir" / "result.txt").exists()


def test_local_adapter_put_raises_on_missing_source(tmp_path):
    adapter = LocalStorageAdapter(base_path=str(tmp_path))
    dest_uri = f"file://{tmp_path}/out.bam"

    with pytest.raises(CanonStorageError, match="not found"):
        adapter.put(str(tmp_path / "nonexistent.bam"), dest_uri)


def test_local_adapter_get_returns_path_if_exists(tmp_path):
    existing = tmp_path / "output.bam"
    existing.write_bytes(b"DATA")
    adapter = LocalStorageAdapter(base_path=str(tmp_path))

    result = adapter.get(f"file://{existing}", str(tmp_path / "local"))
    assert result == existing


def test_local_adapter_get_handles_bare_path(tmp_path):
    existing = tmp_path / "output.bam"
    existing.write_bytes(b"DATA")
    adapter = LocalStorageAdapter(base_path=str(tmp_path))

    result = adapter.get(str(existing), str(tmp_path / "local"))
    assert result == existing


def test_local_adapter_get_raises_on_missing_uri(tmp_path):
    adapter = LocalStorageAdapter(base_path=str(tmp_path))

    with pytest.raises(CanonStorageError, match="not found"):
        adapter.get(f"file://{tmp_path}/nonexistent.bam", str(tmp_path / "local"))


def test_local_adapter_exists_true(tmp_path):
    f = tmp_path / "exists.txt"
    f.write_text("yes")
    adapter = LocalStorageAdapter(base_path=str(tmp_path))

    assert adapter.exists(f"file://{f}") is True


def test_local_adapter_exists_false(tmp_path):
    adapter = LocalStorageAdapter(base_path=str(tmp_path))
    assert adapter.exists(f"file://{tmp_path}/nope.txt") is False


def test_local_adapter_exists_handles_bare_path(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("data")
    adapter = LocalStorageAdapter(base_path=str(tmp_path))

    assert adapter.exists(str(f)) is True
    assert adapter.exists(str(tmp_path / "missing.txt")) is False


def test_local_adapter_build_dest_uri(tmp_path):
    base = str(tmp_path / "storage")
    adapter = LocalStorageAdapter(base_path=base)

    uri = adapter.build_dest_uri("AlignmentFile", "abc-123", "output.bam")
    assert uri == f"file://{base}/alignmentfile/abc-123/output.bam"


def test_local_adapter_build_dest_uri_lowercases_entity_type(tmp_path):
    adapter = LocalStorageAdapter(base_path=str(tmp_path))
    uri = adapter.build_dest_uri("AlignedReads", "run-999", "out.bam")
    assert "/alignedreads/" in uri


# ---------------------------------------------------------------------------
# StorageAdapterRegistry — unit tests
# ---------------------------------------------------------------------------

from canon.storage.registry import StorageAdapterRegistry


def _make_registry_with_local(tmp_path):
    """Build a registry with a real LocalStorageAdapter."""
    local = LocalStorageAdapter(base_path=str(tmp_path / "storage"))
    registry = StorageAdapterRegistry.__new__(StorageAdapterRegistry)
    registry._adapters = {"local": local}
    registry._scheme_map = {}
    for scheme in local.uri_schemes:
        registry._scheme_map[scheme] = local
    registry._default_type = "local"
    return registry


def test_registry_adapter_for_uri_file_scheme(tmp_path):
    registry = _make_registry_with_local(tmp_path)
    adapter = registry.adapter_for_uri("file:///data/output.bam")
    assert isinstance(adapter, LocalStorageAdapter)


def test_registry_adapter_for_uri_bare_path(tmp_path):
    registry = _make_registry_with_local(tmp_path)
    adapter = registry.adapter_for_uri("/data/output.bam")
    assert isinstance(adapter, LocalStorageAdapter)


def test_registry_adapter_for_uri_unknown_scheme_raises(tmp_path):
    registry = _make_registry_with_local(tmp_path)
    with pytest.raises(CanonConfigError, match="s3"):
        registry.adapter_for_uri("s3://bucket/key")


def test_registry_default_adapter_returns_configured(tmp_path):
    registry = _make_registry_with_local(tmp_path)
    adapter = registry.default_adapter
    assert isinstance(adapter, LocalStorageAdapter)


def test_registry_load_from_entry_points_raises_on_unknown_type(tmp_path):
    config = MagicMock()
    config.output_storage.type = "gcs"
    config.output_storage.model_extra = {}

    with pytest.raises(CanonConfigError, match="gcs"):
        StorageAdapterRegistry.load_from_entry_points(config)


# ---------------------------------------------------------------------------
# Integration: entry point discovery
# ---------------------------------------------------------------------------

def test_entry_point_discovery_finds_local_adapter(tmp_path):
    """entry_points('canon.storage_adapters') must include 'local' → LocalStorageAdapter."""
    import importlib.metadata
    eps = importlib.metadata.entry_points(group="canon.storage_adapters")
    names = [ep.name for ep in eps]
    assert "local" in names

    local_ep = next(ep for ep in eps if ep.name == "local")
    loaded_cls = local_ep.load()
    assert loaded_cls is LocalStorageAdapter


def test_registry_load_from_entry_points_with_local_config(tmp_path):
    """Full entry point load with local type succeeds and contains LocalStorageAdapter."""
    config = MagicMock()
    config.output_storage.type = "local"
    config.output_storage.base_path = str(tmp_path / "storage")
    config.output_storage.model_extra = {}

    registry = StorageAdapterRegistry.load_from_entry_points(config)
    assert isinstance(registry.default_adapter, LocalStorageAdapter)
    assert isinstance(registry.adapter_for_uri("file:///tmp/out.bam"), LocalStorageAdapter)
    assert isinstance(registry.adapter_for_uri("/bare/path"), LocalStorageAdapter)


# ---------------------------------------------------------------------------
# HTTPStorageAdapter — unit tests
# ---------------------------------------------------------------------------

from canon.storage.http import HTTPStorageAdapter


def test_http_adapter_name():
    adapter = HTTPStorageAdapter()
    assert adapter.name == "https"


def test_http_adapter_uri_schemes():
    adapter = HTTPStorageAdapter()
    assert "https" in adapter.uri_schemes
    assert "http" in adapter.uri_schemes


def test_http_adapter_put_raises_read_only():
    adapter = HTTPStorageAdapter()
    with pytest.raises(CanonStorageError, match="read-only"):
        adapter.put("/local/file.txt", "https://example.com/file.txt")


def test_http_adapter_build_dest_uri_raises():
    adapter = HTTPStorageAdapter()
    with pytest.raises((CanonStorageError, NotImplementedError)):
        adapter.build_dest_uri("GenomeBuild", "abc-123", "genome.fa.gz")


def test_http_adapter_get_downloads_file(tmp_path):
    """get() streams file and writes to local_dir/<filename>."""
    import httpx
    from unittest.mock import patch, MagicMock

    adapter = HTTPStorageAdapter()
    uri = "https://example.com/data/genome.fa.gz"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_bytes.return_value = [b"FAKEDATA"]
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("httpx.stream", return_value=mock_response):
        result = adapter.get(uri, str(tmp_path))

    assert result == tmp_path / "genome.fa.gz"
    assert (tmp_path / "genome.fa.gz").read_bytes() == b"FAKEDATA"


def test_http_adapter_get_raises_on_404(tmp_path):
    """get() raises CanonStorageError on non-2xx HTTP status."""
    from unittest.mock import patch, MagicMock

    adapter = HTTPStorageAdapter()

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("httpx.stream", return_value=mock_response):
        with pytest.raises(CanonStorageError, match="404"):
            adapter.get("https://example.com/missing.fa", str(tmp_path))


def test_http_adapter_get_raises_on_connection_error(tmp_path):
    """get() raises CanonStorageError on network failure."""
    import httpx
    from unittest.mock import patch

    adapter = HTTPStorageAdapter()

    with patch("httpx.stream", side_effect=httpx.ConnectError("DNS failure")):
        with pytest.raises(CanonStorageError):
            adapter.get("https://example.com/file.fa", str(tmp_path))


def test_http_adapter_exists_true_on_200():
    """exists() returns True when HEAD returns 2xx."""
    from unittest.mock import patch, MagicMock

    adapter = HTTPStorageAdapter()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.head", return_value=mock_response):
        assert adapter.exists("https://example.com/file.fa") is True


def test_http_adapter_exists_false_on_404():
    """exists() returns False when HEAD returns 404."""
    from unittest.mock import patch, MagicMock

    adapter = HTTPStorageAdapter()

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("httpx.head", return_value=mock_response):
        assert adapter.exists("https://example.com/missing.fa") is False


def test_http_adapter_exists_false_on_connection_error():
    """exists() returns False (no raise) on network failure."""
    import httpx
    from unittest.mock import patch

    adapter = HTTPStorageAdapter()

    with patch("httpx.head", side_effect=httpx.ConnectError("unreachable")):
        assert adapter.exists("https://example.com/file.fa") is False


def test_http_adapter_get_filename_from_uri_path(tmp_path):
    """Filename is derived from the last component of the URI path."""
    from unittest.mock import patch, MagicMock

    adapter = HTTPStorageAdapter()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_bytes.return_value = [b"DATA"]
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("httpx.stream", return_value=mock_response):
        result = adapter.get("https://example.com/data/genome.fa.gz", str(tmp_path))

    assert result.name == "genome.fa.gz"


# ---------------------------------------------------------------------------
# Integration: entry point discovery for https/http
# ---------------------------------------------------------------------------

def test_entry_point_discovery_finds_https_adapter():
    """entry_points('canon.storage_adapters') must include 'https' → HTTPStorageAdapter."""
    import importlib.metadata
    eps = importlib.metadata.entry_points(group="canon.storage_adapters")
    names = [ep.name for ep in eps]
    assert "https" in names
    assert "http" in names

    https_ep = next(ep for ep in eps if ep.name == "https")
    loaded_cls = https_ep.load()
    assert loaded_cls is HTTPStorageAdapter


def test_registry_adapter_for_https_uri():
    """StorageAdapterRegistry.adapter_for_uri returns HTTPStorageAdapter for https://."""
    adapter = HTTPStorageAdapter()
    registry = StorageAdapterRegistry.__new__(StorageAdapterRegistry)
    registry._adapters = {"https": adapter}
    registry._scheme_map = {"https": adapter, "http": adapter}
    registry._default_type = "https"

    result = registry.adapter_for_uri("https://example.com/file.fa")
    assert isinstance(result, HTTPStorageAdapter)
