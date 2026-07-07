"""Tests for the certified-frontier ledger tooling (platform ADR-0001).

These run against a throwaway git repo in a tmp dir, so they exercise the real
tag plumbing (annotated tags carrying JSON) without any network or components.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ledger import (
    Component,
    GateError,
    LedgerEntry,
    assemble,
    check_pair,
    find_entry,
    is_certified,
    partners_for_line,
    read_entries,
    write_entry,
)

D_AP = "sha256:" + "a" * 64
D_HI = "sha256:" + "b" * 64


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "seed").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    return tmp_path


def _entry(ap="1.4.2", hi="1.2.3", result="pass", line="frontier",
           failing_check=None, ts="2026-07-07T00:00:00Z",
           d_ap=D_AP, d_hi=D_HI) -> LedgerEntry:
    return LedgerEntry(
        components=[
            Component("aperture", ap, d_ap),
            Component("hippo", hi, d_hi),
        ],
        suite_sha="deadbeef",
        fixture_version="1.0.0",
        result=result,
        line=line,
        failing_check=failing_check,
        timestamp=ts,
    )


# ---- model ------------------------------------------------------------------

def test_label_is_deterministic_regardless_of_component_order():
    a = LedgerEntry(
        components=[Component("hippo", "1.2.3", D_HI), Component("aperture", "1.4.2", D_AP)],
        suite_sha="s", fixture_version="1.0.0", result="pass", timestamp="t",
    )
    assert a.label == "aperture-1.4.2+hippo-1.2.3"
    assert a.tag == "certified/aperture-1.4.2+hippo-1.2.3"


def test_pass_entry_validates_clean():
    assert _entry().validate() == []


def test_fail_entry_requires_failing_check():
    e = _entry(result="fail")
    assert any("failing_check" in p for p in e.validate())
    assert _entry(result="fail", failing_check="atomic-workflow").validate() == []


def test_pass_entry_rejects_failing_check():
    assert any("must not carry" in p for p in _entry(failing_check="x").validate())


def test_digest_is_required_not_just_version():
    e = _entry(d_ap="not-a-digest")
    assert any("content address" in p for p in e.validate())


def test_roundtrip_json():
    e = _entry()
    back = LedgerEntry.from_json(e.to_json())
    assert back.label == e.label
    assert back.to_dict() == e.to_dict()


# ---- certify / read ---------------------------------------------------------

def test_write_and_read_entry(repo: Path):
    tag = write_entry(_entry(), repo=repo)
    assert tag == "certified/aperture-1.4.2+hippo-1.2.3"
    entries = read_entries(repo)
    assert len(entries) == 1
    assert entries[0].passed


def test_write_is_append_only_no_recut(repo: Path):
    write_entry(_entry(), repo=repo)
    # same pair, even with a different digest, must not overwrite the tag
    with pytest.raises(Exception):
        write_entry(_entry(d_ap="sha256:" + "c" * 64), repo=repo)


def test_invalid_entry_refused(repo: Path):
    with pytest.raises(ValueError):
        write_entry(_entry(result="fail"), repo=repo)  # no failing_check


def test_read_skips_junk_tag(repo: Path):
    write_entry(_entry(), repo=repo)
    subprocess.run(
        ["git", "-C", str(repo), "tag", "-a", "certified/garbage", "-m", "not json"],
        check=True,
    )
    # junk under the namespace is skipped, real entry still read
    entries = read_entries(repo)
    assert [e.label for e in entries] == ["aperture-1.4.2+hippo-1.2.3"]


# ---- assemble ---------------------------------------------------------------

def test_assemble_counts_pass_and_fail(repo: Path):
    write_entry(_entry(), repo=repo)
    write_entry(_entry(hi="1.3.0", result="fail", failing_check="browse-filter"), repo=repo)
    doc = assemble(repo)
    assert doc["counts"] == {"total": 2, "passing": 1, "failing": 1}
    # only passing versions land in the certified_versions summary
    assert doc["certified_versions"]["hippo"] == ["1.2.3"]
    assert doc["certified_versions"]["aperture"] == ["1.4.2"]


# ---- query ------------------------------------------------------------------

def test_partners_for_line_globs_versions(repo: Path):
    write_entry(_entry(ap="1.4.2", hi="1.2.3"), repo=repo)
    write_entry(_entry(ap="1.4.2", hi="1.2.4"), repo=repo)
    write_entry(_entry(ap="1.6.0", hi="2.0.0"), repo=repo)
    # aperture LTS line 1.4.* — which hippos are certified with it?
    assert partners_for_line("aperture", "1.4.*", "hippo", repo=repo) == ["1.2.3", "1.2.4"]
    # bare X.Y is treated as X.Y.*
    assert partners_for_line("aperture", "1.4", "hippo", repo=repo) == ["1.2.3", "1.2.4"]
    # frontier line
    assert partners_for_line("aperture", "1.6.*", "hippo", repo=repo) == ["2.0.0"]


def test_partners_excludes_failing_by_default(repo: Path):
    write_entry(_entry(ap="1.4.2", hi="1.2.9", result="fail", failing_check="x"), repo=repo)
    assert partners_for_line("aperture", "1.4.*", "hippo", repo=repo) == []
    assert partners_for_line("aperture", "1.4.*", "hippo", repo=repo, passing_only=False) == ["1.2.9"]


def test_find_entry(repo: Path):
    write_entry(_entry(), repo=repo)
    assert find_entry("aperture-1.4.2+hippo-1.2.3", repo=repo) is not None
    assert find_entry("aperture-9.9.9+hippo-9.9.9", repo=repo) is None


# ---- gate -------------------------------------------------------------------

def test_gate_admits_certified_pair_with_matching_digests(repo: Path):
    write_entry(_entry(), repo=repo)
    req = [Component("aperture", "1.4.2", D_AP), Component("hippo", "1.2.3", D_HI)]
    assert is_certified(req, repo=repo)
    entry = check_pair(req, repo=repo)
    assert entry.passed


def test_gate_refuses_uncertified_pair(repo: Path):
    write_entry(_entry(), repo=repo)
    req = [Component("aperture", "9.9.9", D_AP), Component("hippo", "1.2.3", D_HI)]
    assert not is_certified(req, repo=repo)
    with pytest.raises(GateError, match="uncertified"):
        check_pair(req, repo=repo)


def test_gate_refuses_recut_digest_mismatch(repo: Path):
    write_entry(_entry(), repo=repo)
    # correct versions, but a re-cut artifact (different digest)
    req = [Component("aperture", "1.4.2", "sha256:" + "f" * 64), Component("hippo", "1.2.3", D_HI)]
    with pytest.raises(GateError, match="digest mismatch"):
        check_pair(req, repo=repo)


def test_gate_refuses_certified_failing_pair(repo: Path):
    write_entry(_entry(result="fail", failing_check="control-plane"), repo=repo)
    req = [Component("aperture", "1.4.2", D_AP), Component("hippo", "1.2.3", D_HI)]
    with pytest.raises(GateError, match="FAILING"):
        check_pair(req, repo=repo)
