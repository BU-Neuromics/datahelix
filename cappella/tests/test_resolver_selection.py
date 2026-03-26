"""Tests for collection resolver selection strategies."""
import pytest

from cappella.exceptions import MultipleDatasetError
from cappella.resolver.selection import (
    ExplicitStrategy,
    HighestQualityStrategy,
    MostRecentStrategy,
    SingleOnlyStrategy,
    get_strategy,
)


CANDIDATES = [
    {"id": "d1", "created_at": "2024-01-01", "quality_score": 80, "status": "pass"},
    {"id": "d2", "created_at": "2024-06-01", "quality_score": 95, "status": "pass"},
    {"id": "d3", "created_at": "2024-03-01", "quality_score": 60, "status": "fail"},
]


class TestMostRecentStrategy:
    def test_returns_most_recent(self):
        strategy = MostRecentStrategy()
        result = strategy.select(CANDIDATES)
        assert result["id"] == "d2"

    def test_empty_returns_none(self):
        strategy = MostRecentStrategy()
        assert strategy.select([]) is None

    def test_filter_by_status(self):
        strategy = MostRecentStrategy()
        result = strategy.select(CANDIDATES, filters={"status": "fail"})
        assert result["id"] == "d3"

    def test_filter_no_match_returns_none(self):
        strategy = MostRecentStrategy()
        result = strategy.select(CANDIDATES, filters={"status": "pending"})
        assert result is None

    def test_single_candidate(self):
        strategy = MostRecentStrategy()
        result = strategy.select([{"id": "x", "created_at": "2024-01-01"}])
        assert result["id"] == "x"

    def test_missing_created_at_handled(self):
        strategy = MostRecentStrategy()
        candidates = [{"id": "a"}, {"id": "b", "created_at": "2024-01-01"}]
        result = strategy.select(candidates)
        assert result is not None  # doesn't crash


class TestHighestQualityStrategy:
    def test_returns_highest_quality(self):
        strategy = HighestQualityStrategy()
        result = strategy.select(CANDIDATES)
        assert result["id"] == "d2"

    def test_empty_returns_none(self):
        strategy = HighestQualityStrategy()
        assert strategy.select([]) is None

    def test_custom_quality_field(self):
        strategy = HighestQualityStrategy(quality_field="score")
        candidates = [{"id": "a", "score": 10}, {"id": "b", "score": 99}]
        result = strategy.select(candidates)
        assert result["id"] == "b"

    def test_filter_applied(self):
        strategy = HighestQualityStrategy()
        result = strategy.select(CANDIDATES, filters={"status": "pass"})
        assert result["id"] == "d2"

    def test_filter_no_match_returns_none(self):
        strategy = HighestQualityStrategy()
        result = strategy.select(CANDIDATES, filters={"status": "pending"})
        assert result is None

    def test_non_numeric_quality_defaults_to_zero(self):
        strategy = HighestQualityStrategy()
        candidates = [{"id": "a", "quality_score": "bad"}, {"id": "b", "quality_score": 5}]
        result = strategy.select(candidates)
        assert result["id"] == "b"

    def test_missing_quality_field_defaults_to_zero(self):
        strategy = HighestQualityStrategy()
        candidates = [{"id": "a"}, {"id": "b", "quality_score": 10}]
        result = strategy.select(candidates)
        assert result["id"] == "b"


class TestExplicitStrategy:
    def test_override_selects_target(self):
        strategy = ExplicitStrategy(overrides={"d1": "d2"})
        result = strategy.select(CANDIDATES)
        assert result["id"] == "d2"

    def test_no_override_falls_back_to_most_recent(self):
        strategy = ExplicitStrategy(overrides={})
        result = strategy.select(CANDIDATES)
        assert result["id"] == "d2"

    def test_empty_returns_none(self):
        strategy = ExplicitStrategy()
        assert strategy.select([]) is None

    def test_override_target_not_found_falls_back(self):
        strategy = ExplicitStrategy(overrides={"d1": "d999"})
        result = strategy.select(CANDIDATES)
        # Falls back to most recent since d999 not in candidates
        assert result is not None


class TestSingleOnlyStrategy:
    def test_single_candidate_returned(self):
        strategy = SingleOnlyStrategy()
        result = strategy.select([{"id": "x"}])
        assert result["id"] == "x"

    def test_multiple_candidates_raises(self):
        strategy = SingleOnlyStrategy()
        with pytest.raises(MultipleDatasetError, match="expected 1"):
            strategy.select(CANDIDATES)

    def test_empty_returns_none(self):
        strategy = SingleOnlyStrategy()
        assert strategy.select([]) is None

    def test_error_contains_count(self):
        strategy = SingleOnlyStrategy()
        with pytest.raises(MultipleDatasetError) as exc_info:
            strategy.select(CANDIDATES)
        assert exc_info.value.context["count"] == 3


class TestGetStrategy:
    def test_most_recent(self):
        s = get_strategy("most_recent")
        assert isinstance(s, MostRecentStrategy)

    def test_highest_quality(self):
        s = get_strategy("highest_quality")
        assert isinstance(s, HighestQualityStrategy)

    def test_highest_quality_with_field(self):
        s = get_strategy("highest_quality", quality_field="score")
        assert s.quality_field == "score"

    def test_explicit(self):
        s = get_strategy("explicit", overrides={"a": "b"})
        assert isinstance(s, ExplicitStrategy)

    def test_single_only(self):
        s = get_strategy("single_only")
        assert isinstance(s, SingleOnlyStrategy)

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown selection strategy"):
            get_strategy("no_such_strategy")
