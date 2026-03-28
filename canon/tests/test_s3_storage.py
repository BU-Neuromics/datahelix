"""Tests for S3StorageAdapter — boto3 is mocked completely, no real AWS credentials needed."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from canon.exceptions import CanonStorageError
from canon.storage.base import StorageAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(bucket="test-bucket", prefix="", credentials="env"):
    """Build an S3StorageAdapter with a mocked boto3 client."""
    mock_client = MagicMock()
    with patch("canon.storage.s3._build_boto3_client", return_value=mock_client):
        from canon.storage.s3 import S3StorageAdapter
        adapter = S3StorageAdapter(bucket=bucket, prefix=prefix, credentials=credentials)
    return adapter, mock_client


# ---------------------------------------------------------------------------
# Class-level attributes
# ---------------------------------------------------------------------------

def test_s3_adapter_name():
    adapter, _ = _make_adapter()
    assert adapter.name == "s3"


def test_s3_adapter_uri_schemes():
    adapter, _ = _make_adapter()
    assert "s3" in adapter.uri_schemes
    assert "s3a" in adapter.uri_schemes


def test_s3_adapter_is_storage_adapter_subclass():
    adapter, _ = _make_adapter()
    assert isinstance(adapter, StorageAdapter)


# ---------------------------------------------------------------------------
# put()
# ---------------------------------------------------------------------------

def test_s3_put_calls_upload_file(tmp_path):
    src = tmp_path / "output.bam"
    src.write_bytes(b"FAKE_BAM")

    adapter, mock_client = _make_adapter(bucket="my-bucket", prefix="outputs")
    result = adapter.put(str(src), "s3://my-bucket/outputs/alignedreads/abc-123/output.bam")

    mock_client.upload_file.assert_called_once_with(
        str(src), "my-bucket", "outputs/alignedreads/abc-123/output.bam"
    )
    assert result == "s3://my-bucket/outputs/alignedreads/abc-123/output.bam"


def test_s3_put_raises_on_missing_source(tmp_path):
    adapter, _ = _make_adapter()
    with pytest.raises(CanonStorageError, match="not found"):
        adapter.put(str(tmp_path / "nonexistent.bam"), "s3://bucket/key.bam")


def test_s3_put_raises_on_upload_failure(tmp_path):
    src = tmp_path / "file.bam"
    src.write_bytes(b"DATA")

    adapter, mock_client = _make_adapter()
    mock_client.upload_file.side_effect = RuntimeError("S3 unavailable")

    with pytest.raises(CanonStorageError, match="Failed to upload"):
        adapter.put(str(src), "s3://bucket/key.bam")


def test_s3_put_returns_canonical_s3_uri(tmp_path):
    src = tmp_path / "result.txt"
    src.write_text("hello")

    adapter, mock_client = _make_adapter(bucket="lab-bucket")
    result = adapter.put(str(src), "s3://lab-bucket/data/result.txt")

    assert result.startswith("s3://lab-bucket/")
    assert "result.txt" in result


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------

def test_s3_get_calls_download_file(tmp_path):
    adapter, mock_client = _make_adapter(bucket="my-bucket")

    result = adapter.get("s3://my-bucket/some/path/output.bam", str(tmp_path))

    mock_client.download_file.assert_called_once_with(
        "my-bucket", "some/path/output.bam", str(tmp_path / "output.bam")
    )
    assert result == tmp_path / "output.bam"


def test_s3_get_derives_filename_from_key(tmp_path):
    adapter, mock_client = _make_adapter(bucket="bucket")

    result = adapter.get("s3://bucket/deep/nested/path/genome.fa.gz", str(tmp_path))

    assert result.name == "genome.fa.gz"


def test_s3_get_raises_on_download_failure(tmp_path):
    adapter, mock_client = _make_adapter()
    mock_client.download_file.side_effect = RuntimeError("NoSuchKey")

    with pytest.raises(CanonStorageError, match="Failed to download"):
        adapter.get("s3://bucket/missing/file.bam", str(tmp_path))


def test_s3_get_handles_s3a_uri(tmp_path):
    adapter, mock_client = _make_adapter(bucket="my-bucket")

    result = adapter.get("s3a://my-bucket/data/file.vcf", str(tmp_path))

    mock_client.download_file.assert_called_once_with(
        "my-bucket", "data/file.vcf", str(tmp_path / "file.vcf")
    )
    assert result == tmp_path / "file.vcf"


# ---------------------------------------------------------------------------
# exists()
# ---------------------------------------------------------------------------

def test_s3_exists_true_when_head_object_succeeds():
    adapter, mock_client = _make_adapter(bucket="bucket")
    mock_client.head_object.return_value = {"ContentLength": 1234}

    assert adapter.exists("s3://bucket/path/file.bam") is True
    mock_client.head_object.assert_called_once_with(Bucket="bucket", Key="path/file.bam")


def test_s3_exists_false_when_head_object_raises():
    adapter, mock_client = _make_adapter(bucket="bucket")
    mock_client.head_object.side_effect = Exception("404 Not Found")

    assert adapter.exists("s3://bucket/missing/file.bam") is False


def test_s3_exists_never_raises_on_any_exception():
    adapter, mock_client = _make_adapter(bucket="bucket")
    mock_client.head_object.side_effect = RuntimeError("Network unreachable")

    # Must return False, not raise
    assert adapter.exists("s3://bucket/any/key") is False


def test_s3_exists_false_on_malformed_uri():
    adapter, _ = _make_adapter()
    # Malformed URI causes _parse_s3_uri to raise, which exists() should swallow
    assert adapter.exists("not-a-valid-uri") is False


# ---------------------------------------------------------------------------
# build_dest_uri()
# ---------------------------------------------------------------------------

def test_s3_build_dest_uri_with_prefix():
    adapter, _ = _make_adapter(bucket="lab-outputs", prefix="outputs")
    uri = adapter.build_dest_uri("AlignedReads", "abc-123", "output.bam")
    assert uri == "s3://lab-outputs/outputs/alignedreads/abc-123/output.bam"


def test_s3_build_dest_uri_without_prefix():
    adapter, _ = _make_adapter(bucket="lab-bucket", prefix="")
    uri = adapter.build_dest_uri("AlignedReads", "xyz-789", "output.bam")
    assert uri == "s3://lab-bucket/alignedreads/xyz-789/output.bam"


def test_s3_build_dest_uri_lowercases_entity_type():
    adapter, _ = _make_adapter(bucket="bucket")
    uri = adapter.build_dest_uri("DifferentialExpression", "run-1", "result.tsv")
    assert "/differentialexpression/" in uri


def test_s3_build_dest_uri_strips_trailing_slash_from_prefix():
    adapter, _ = _make_adapter(bucket="bucket", prefix="outputs/")
    uri = adapter.build_dest_uri("AlignedReads", "id-1", "file.bam")
    # Should not produce double slashes
    assert "outputs/alignedreads/id-1/file.bam" in uri
    assert "//" not in uri.split("s3://bucket/")[1]


# ---------------------------------------------------------------------------
# _parse_s3_uri helper
# ---------------------------------------------------------------------------

def test_parse_s3_uri_valid():
    from canon.storage.s3 import _parse_s3_uri
    bucket, key = _parse_s3_uri("s3://my-bucket/some/path/file.bam")
    assert bucket == "my-bucket"
    assert key == "some/path/file.bam"


def test_parse_s3_uri_s3a_scheme():
    from canon.storage.s3 import _parse_s3_uri
    bucket, key = _parse_s3_uri("s3a://my-bucket/data/file.vcf")
    assert bucket == "my-bucket"
    assert key == "data/file.vcf"


def test_parse_s3_uri_missing_scheme_raises():
    from canon.storage.s3 import _parse_s3_uri
    with pytest.raises(CanonStorageError, match="missing scheme"):
        _parse_s3_uri("my-bucket/some/key")


def test_parse_s3_uri_empty_bucket_raises():
    from canon.storage.s3 import _parse_s3_uri
    with pytest.raises(CanonStorageError, match="empty bucket"):
        _parse_s3_uri("s3:///some/key")


# ---------------------------------------------------------------------------
# boto3 import error
# ---------------------------------------------------------------------------

def test_boto3_import_error_raises_canon_storage_error():
    """If boto3 is not installed, _build_boto3_client raises CanonStorageError."""
    import sys
    # Temporarily hide boto3 from imports
    original = sys.modules.get("boto3")
    sys.modules["boto3"] = None  # type: ignore[assignment]
    try:
        from canon.storage import s3 as s3_module
        import importlib
        importlib.reload(s3_module)
        with pytest.raises((CanonStorageError, ImportError)):
            s3_module._build_boto3_client("env")
    finally:
        if original is None:
            sys.modules.pop("boto3", None)
        else:
            sys.modules["boto3"] = original


# ---------------------------------------------------------------------------
# Credentials config
# ---------------------------------------------------------------------------

def test_profile_credentials_uses_session():
    """profile:<name> creates a boto3.Session with that profile."""
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client.return_value = mock_client

    with patch("boto3.session.Session", return_value=mock_session) as mock_session_cls:
        with patch("boto3.client"):
            from canon.storage.s3 import _build_boto3_client
            client = _build_boto3_client("profile:my-profile")

    mock_session_cls.assert_called_once_with(profile_name="my-profile")
    mock_session.client.assert_called_once_with("s3")
    assert client is mock_client


def test_env_credentials_uses_boto3_client_directly():
    """env credentials calls boto3.client directly (default credential chain)."""
    mock_client = MagicMock()
    with patch("boto3.client", return_value=mock_client) as mock_boto3_client:
        with patch("boto3.session.Session"):
            from canon.storage.s3 import _build_boto3_client
            client = _build_boto3_client("env")

    mock_boto3_client.assert_called_once_with("s3")
    assert client is mock_client
