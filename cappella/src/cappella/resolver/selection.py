from typing import Any

from cappella.exceptions import MultipleDatasetError
from cappella.types import SelectionStrategy


class MostRecentStrategy(SelectionStrategy):
    """Select the most recently created dataset, with optional QC filters."""

    def select(self, candidates: list[dict], filters: dict | None = None) -> dict | None:
        if not candidates:
            return None

        filtered = self._apply_filters(candidates, filters or {})
        if not filtered:
            return None

        # Sort by created_at descending
        def sort_key(item: dict) -> str:
            return str(item.get("created_at", ""))

        sorted_items = sorted(filtered, key=sort_key, reverse=True)
        return sorted_items[0]

    def _apply_filters(self, candidates: list[dict], filters: dict) -> list[dict]:
        if not filters:
            return candidates

        result = []
        for candidate in candidates:
            match = True
            for key, expected in filters.items():
                if candidate.get(key) != expected:
                    match = False
                    break
            if match:
                result.append(candidate)
        return result


class HighestQualityStrategy(SelectionStrategy):
    """Select the dataset with the highest quality score."""

    def __init__(self, quality_field: str = "quality_score") -> None:
        self.quality_field = quality_field

    def select(self, candidates: list[dict], filters: dict | None = None) -> dict | None:
        if not candidates:
            return None

        filtered = candidates
        if filters:
            filtered = [
                c for c in candidates
                if all(c.get(k) == v for k, v in filters.items())
            ]

        if not filtered:
            return None

        def quality_key(item: dict) -> Any:
            val = item.get(self.quality_field, 0)
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        return max(filtered, key=quality_key)


class ExplicitStrategy(SelectionStrategy):
    """Use explicit overrides map; fall back to most_recent."""

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self.overrides = overrides or {}
        self._fallback = MostRecentStrategy()

    def select(self, candidates: list[dict], filters: dict | None = None) -> dict | None:
        if not candidates:
            return None

        # Check overrides by sample_id or id
        for candidate in candidates:
            cid = candidate.get("id") or candidate.get("sample_id", "")
            if str(cid) in self.overrides:
                override_id = self.overrides[str(cid)]
                for c in candidates:
                    if c.get("id") == override_id or c.get("dataset_id") == override_id:
                        return c

        return self._fallback.select(candidates, filters)


class SingleOnlyStrategy(SelectionStrategy):
    """Require exactly one candidate; raise MultipleDatasetError if more."""

    def select(self, candidates: list[dict], filters: dict | None = None) -> dict | None:
        if not candidates:
            return None

        if len(candidates) > 1:
            raise MultipleDatasetError(
                f"SingleOnlyStrategy: expected 1 candidate, got {len(candidates)}",
                {"count": len(candidates)},
            )

        return candidates[0]


def get_strategy(name: str, **kwargs: Any) -> SelectionStrategy:
    """Factory function for selection strategies."""
    strategies: dict[str, type] = {
        "most_recent": MostRecentStrategy,
        "highest_quality": HighestQualityStrategy,
        "explicit": ExplicitStrategy,
        "single_only": SingleOnlyStrategy,
    }
    if name not in strategies:
        raise ValueError(f"Unknown selection strategy: '{name}'")
    return strategies[name](**kwargs)
