"""Tests for core data types."""
from datetime import datetime

import pytest

from cappella.canon.client import CanonDecision
from cappella.exceptions import MultipleDatasetError
from cappella.types import (
    HarmonizedCollection,
    RawRecord,
    ResolvedItem,
    SelectionStrategy,
    TransformedRecord,
    UnresolvedItem,
)


class TestRawRecord:
    def test_required_fields(self):
        r = RawRecord(source_system="lims", external_id="X1", data={"a": 1})
        assert r.source_system == "lims"
        assert r.external_id == "X1"
        assert r.data == {"a": 1}

    def test_fetched_at_defaults_to_now(self):
        before = datetime.utcnow()
        r = RawRecord(source_system="s", external_id="e", data={})
        after = datetime.utcnow()
        assert before <= r.fetched_at <= after

    def test_fetched_at_can_be_set(self):
        ts = datetime(2025, 1, 1, 12, 0, 0)
        r = RawRecord(source_system="s", external_id="e", data={}, fetched_at=ts)
        assert r.fetched_at == ts


class TestTransformedRecord:
    def test_required_fields(self):
        t = TransformedRecord(
            entity_type="sample",
            data={"name": "foo"},
            external_id="S1",
            source_system="lims",
        )
        assert t.entity_type == "sample"
        assert t.external_id == "S1"
        assert t.source_system == "lims"

    def test_trust_level_defaults_to_50(self):
        t = TransformedRecord(entity_type="sample", data={}, external_id="S1", source_system="s")
        assert t.trust_level == 50

    def test_trust_level_can_be_set(self):
        t = TransformedRecord(entity_type="sample", data={}, external_id="S1", source_system="s", trust_level=80)
        assert t.trust_level == 80


class TestResolvedItem:
    def test_basic(self):
        r = ResolvedItem(sample_id="s1", entity={"id": "e1"}, status="resolved")
        assert r.sample_id == "s1"
        assert r.status == "resolved"
        assert r.canon_decision is None

    def test_with_canon_decision(self):
        cd = CanonDecision(decision="REUSE", uri="uri://foo/1")
        r = ResolvedItem(sample_id="s1", entity={}, status="resolved", canon_decision=cd)
        assert r.canon_decision.decision == "REUSE"


class TestUnresolvedItem:
    def test_basic(self):
        u = UnresolvedItem(sample_id="s2", reason="not_found")
        assert u.sample_id == "s2"
        assert u.reason == "not_found"
        assert u.detail == ""

    def test_with_detail(self):
        u = UnresolvedItem(sample_id="s2", reason="not_found", detail="No entity matched")
        assert u.detail == "No entity matched"


class TestHarmonizedCollection:
    def _make(self, resolved=None, unresolved=None):
        return HarmonizedCollection(
            request={"entity_type": "sample"},
            selection={"strategy": "most_recent"},
            resolved=resolved or [],
            unresolved=unresolved or [],
        )

    def test_resolved_count(self):
        ri = ResolvedItem(sample_id="s1", entity={}, status="ok")
        hc = self._make(resolved=[ri, ri])
        assert hc.resolved_count == 2

    def test_unresolved_count(self):
        ui = UnresolvedItem(sample_id="s2", reason="missing")
        hc = self._make(unresolved=[ui])
        assert hc.unresolved_count == 1

    def test_to_dict_structure(self):
        ri = ResolvedItem(sample_id="s1", entity={"id": "e1"}, status="resolved")
        ui = UnresolvedItem(sample_id="s2", reason="no_match", detail="nope")
        hc = self._make(resolved=[ri], unresolved=[ui])
        d = hc.to_dict()
        assert d["resolved_count"] == 1
        assert d["unresolved_count"] == 1
        assert d["resolved"][0]["sample_id"] == "s1"
        assert d["unresolved"][0]["reason"] == "no_match"

    def test_to_dict_with_canon_decision(self):
        cd = CanonDecision(decision="FETCH", uri="uri://x/2")
        ri = ResolvedItem(sample_id="s1", entity={}, status="ok", canon_decision=cd)
        hc = self._make(resolved=[ri])
        d = hc.to_dict()
        assert d["resolved"][0]["canon_decision"]["decision"] == "FETCH"

    def test_to_dict_canon_decision_none(self):
        ri = ResolvedItem(sample_id="s1", entity={}, status="ok", canon_decision=None)
        hc = self._make(resolved=[ri])
        d = hc.to_dict()
        assert d["resolved"][0]["canon_decision"] is None

    def test_provenance_defaults_empty(self):
        hc = self._make()
        assert hc.provenance == {}

    def test_empty_collection(self):
        hc = self._make()
        assert hc.resolved_count == 0
        assert hc.unresolved_count == 0


class TestSelectionStrategyABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            SelectionStrategy()
