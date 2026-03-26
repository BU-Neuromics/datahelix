"""Tests for reconciliation engine, checks, and findings store."""
from datetime import datetime, timedelta, timezone

import pytest

from cappella.reconciliation.engine import (
    BrokenReferenceCheck,
    FieldConflictCheck,
    FindingsStore,
    MissingArtifactCheck,
    MissingEntityCheck,
    ReconciliationEngine,
    ReconciliationFinding,
    ReconciliationRequest,
    StaleEntityCheck,
)


def _make_request(entity_type="sample", checks=None, **params):
    return ReconciliationRequest(entity_type=entity_type, checks=checks, parameters=params)


class MockHippo:
    """Minimal mock for reconciliation tests."""

    def __init__(self, entities=None):
        self._entities = entities or []

    def query(self, entity_type, filters):
        if filters.get("check") == "missing":
            return [e for e in self._entities if e.get("_missing")]
        return list(self._entities)


class TestReconciliationFinding:
    def test_fields(self):
        f = ReconciliationFinding(
            finding_id="uuid-1",
            check="missing_entity",
            entity_type="sample",
            entity_id="s1",
            severity="error",
            detail="Not found",
            suggested_action="Create it",
        )
        assert f.finding_id == "uuid-1"
        assert f.severity == "error"
        assert f.source_a is None
        assert f.source_b is None


class TestMissingEntityCheck:
    def test_flags_missing_entities(self):
        hippo = MockHippo([{"id": "e1", "_missing": True}])
        check = MissingEntityCheck()
        req = _make_request()
        findings = check.run(req, hippo)
        assert len(findings) == 1
        assert findings[0].check == "missing_entity"
        assert findings[0].severity == "error"

    def test_no_missing_entities(self):
        hippo = MockHippo([{"id": "e1"}])
        check = MissingEntityCheck()
        findings = check.run(_make_request(), hippo)
        assert findings == []

    def test_hippo_failure_returns_error_finding(self):
        class BrokenHippo:
            def query(self, *a, **k):
                raise RuntimeError("DB down")
        check = MissingEntityCheck()
        findings = check.run(_make_request(), BrokenHippo())
        assert len(findings) == 1
        assert "Check failed" in findings[0].detail


class TestStaleEntityCheck:
    def _old_entity(self, days=60):
        old_date = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        return {"id": "e1", "updated_at": old_date}

    def _fresh_entity(self):
        fresh_date = datetime.now(tz=timezone.utc).isoformat()
        return {"id": "e2", "updated_at": fresh_date}

    def test_stale_entity_flagged(self):
        hippo = MockHippo([self._old_entity(days=60)])
        check = StaleEntityCheck()
        req = _make_request(threshold_days=30)
        findings = check.run(req, hippo)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_fresh_entity_not_flagged(self):
        hippo = MockHippo([self._fresh_entity()])
        check = StaleEntityCheck()
        req = _make_request(threshold_days=30)
        findings = check.run(req, hippo)
        assert findings == []

    def test_missing_date_skipped(self):
        hippo = MockHippo([{"id": "e1"}])
        check = StaleEntityCheck()
        findings = check.run(_make_request(threshold_days=30), hippo)
        assert findings == []


class TestFieldConflictCheck:
    def test_conflict_flagged(self):
        entity = {
            "id": "e1",
            "_conflicts": {
                "species": {"source_a": "lims", "source_b": "redcap"}
            },
        }
        hippo = MockHippo([entity])
        check = FieldConflictCheck()
        findings = check.run(_make_request(), hippo)
        assert len(findings) == 1
        assert findings[0].source_a == "lims"
        assert findings[0].source_b == "redcap"

    def test_no_conflicts(self):
        hippo = MockHippo([{"id": "e1"}])
        check = FieldConflictCheck()
        findings = check.run(_make_request(), hippo)
        assert findings == []

    def test_field_filter_applied(self):
        entity = {
            "id": "e1",
            "_conflicts": {
                "name": {"source_a": "a", "source_b": "b"},
                "status": {"source_a": "c", "source_b": "d"},
            },
        }
        hippo = MockHippo([entity])
        check = FieldConflictCheck()
        req = _make_request(fields=["name"])
        findings = check.run(req, hippo)
        assert len(findings) == 1
        assert "name" in findings[0].detail


class TestBrokenReferenceCheck:
    def test_broken_ref_flagged(self):
        entity = {"id": "e1", "_broken_refs": ["dataset/999"]}
        hippo = MockHippo([entity])
        check = BrokenReferenceCheck()
        findings = check.run(_make_request(), hippo)
        assert len(findings) == 1
        assert "dataset/999" in findings[0].detail
        assert findings[0].severity == "error"

    def test_no_broken_refs(self):
        hippo = MockHippo([{"id": "e1", "_broken_refs": []}])
        check = BrokenReferenceCheck()
        findings = check.run(_make_request(), hippo)
        assert findings == []


class TestMissingArtifactCheck:
    def test_missing_artifact_flagged(self):
        entity = {"id": "e1", "artifacts": ["qc_report"]}
        hippo = MockHippo([entity])
        check = MissingArtifactCheck()
        req = _make_request(required_artifacts=["qc_report", "alignment_bam"])
        findings = check.run(req, hippo)
        assert len(findings) == 1
        assert "alignment_bam" in findings[0].detail

    def test_all_artifacts_present(self):
        entity = {"id": "e1", "artifacts": ["qc_report", "alignment_bam"]}
        hippo = MockHippo([entity])
        check = MissingArtifactCheck()
        req = _make_request(required_artifacts=["qc_report", "alignment_bam"])
        findings = check.run(req, hippo)
        assert findings == []

    def test_no_required_artifacts(self):
        hippo = MockHippo([{"id": "e1"}])
        check = MissingArtifactCheck()
        req = _make_request(required_artifacts=[])
        findings = check.run(req, hippo)
        assert findings == []


class TestReconciliationEngine:
    def test_run_all_checks_by_default(self):
        hippo = MockHippo([{"id": "e1"}])
        engine = ReconciliationEngine()
        req = ReconciliationRequest(entity_type="sample")
        findings = engine.run(req, hippo)
        assert isinstance(findings, list)

    def test_run_specific_check(self):
        hippo = MockHippo([{"id": "e1", "_missing": True}])
        engine = ReconciliationEngine()
        req = ReconciliationRequest(entity_type="sample", checks=["missing_entity"])
        findings = engine.run(req, hippo)
        assert any(f.check == "missing_entity" for f in findings)

    def test_unknown_check_returns_error_finding(self):
        engine = ReconciliationEngine()
        req = ReconciliationRequest(entity_type="sample", checks=["no_such_check"])
        findings = engine.run(req, MockHippo())
        assert len(findings) == 1
        assert "Unknown check" in findings[0].detail

    def test_never_aborts_on_partial_failure(self):
        class BrokenHippo:
            def query(self, *a, **k):
                raise RuntimeError("exploded")

        engine = ReconciliationEngine()
        # Running multiple checks, all fail — should still return error findings, not raise
        req = ReconciliationRequest(entity_type="sample", checks=["missing_entity", "stale_entity"])
        findings = engine.run(req, BrokenHippo())
        assert len(findings) >= 1  # at least error findings


class TestFindingsStore:
    def _make_finding(self, check="missing_entity", entity_type="sample", severity="error"):
        return ReconciliationFinding(
            finding_id="f1",
            check=check,
            entity_type=entity_type,
            entity_id="e1",
            severity=severity,
            detail="test",
            suggested_action="fix it",
        )

    def test_store_and_count(self):
        store = FindingsStore()
        store.store(self._make_finding())
        assert store.count() == 1

    def test_store_many(self):
        store = FindingsStore()
        store.store_many([self._make_finding(), self._make_finding()])
        assert store.count() == 2

    def test_query_by_entity_type(self):
        store = FindingsStore()
        store.store(self._make_finding(entity_type="sample"))
        store.store(self._make_finding(entity_type="dataset"))
        results = store.query(entity_type="sample")
        assert all(f.entity_type == "sample" for f in results)
        assert len(results) == 1

    def test_query_by_check(self):
        store = FindingsStore()
        store.store(self._make_finding(check="missing_entity"))
        store.store(self._make_finding(check="stale_entity"))
        results = store.query(check="missing_entity")
        assert len(results) == 1

    def test_query_by_severity(self):
        store = FindingsStore()
        store.store(self._make_finding(severity="error"))
        store.store(self._make_finding(severity="warning"))
        results = store.query(severity="warning")
        assert len(results) == 1
        assert results[0].severity == "warning"

    def test_clear(self):
        store = FindingsStore()
        store.store(self._make_finding())
        store.clear()
        assert store.count() == 0

    def test_empty_query_returns_all(self):
        store = FindingsStore()
        store.store(self._make_finding())
        store.store(self._make_finding())
        results = store.query()
        assert len(results) == 2
