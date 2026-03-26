"""Tests for ConflictResolver."""
import pytest

from cappella.ingest.conflict import ConflictResolution, ConflictResolver


class TestConflictResolver:
    def setup_method(self):
        self.resolver = ConflictResolver()

    def _resolve(self, existing_trust, incoming_trust, existing_value="old", incoming_value="new"):
        return self.resolver.resolve(
            entity_id="e1",
            field="name",
            existing_value=existing_value,
            existing_source="lims",
            existing_trust=existing_trust,
            incoming_value=incoming_value,
            incoming_source="redcap",
            incoming_trust=incoming_trust,
        )

    def test_existing_wins_when_higher_trust(self):
        winning, resolution = self._resolve(existing_trust=80, incoming_trust=50)
        assert resolution == "existing_wins"
        assert winning == "old"

    def test_incoming_wins_when_higher_trust(self):
        winning, resolution = self._resolve(existing_trust=50, incoming_trust=80)
        assert resolution == "incoming_wins"
        assert winning == "new"

    def test_manual_review_when_equal_trust(self):
        winning, resolution = self._resolve(existing_trust=60, incoming_trust=60)
        assert resolution == "manual_review_required"
        assert winning == "old"  # defaults to existing

    def test_returns_tuple(self):
        result = self._resolve(80, 50)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_zero_trust_incoming_wins_over_zero(self):
        # Both zero → manual review
        winning, resolution = self._resolve(existing_trust=0, incoming_trust=0)
        assert resolution == "manual_review_required"

    def test_different_value_types(self):
        winning, resolution = self.resolver.resolve(
            entity_id="e1",
            field="count",
            existing_value=42,
            existing_source="s1",
            existing_trust=90,
            incoming_value=100,
            incoming_source="s2",
            incoming_trust=10,
        )
        assert winning == 42
        assert resolution == "existing_wins"
