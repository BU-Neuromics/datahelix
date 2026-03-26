from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cappella.canon.client import CanonClient
from cappella.exceptions import (
    CanonNoRuleError,
    CanonResolveError,
    CanonTimeoutError,
    MultipleDatasetError,
)
from cappella.resolver.selection import get_strategy
from cappella.resolver.traversal import EntityTraversal, HippoClientProtocol
from cappella.types import HarmonizedCollection, ResolvedItem, SelectionStrategy, UnresolvedItem


@dataclass
class ResolutionRequest:
    entity_type: str
    criteria: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    selection: dict[str, Any] = field(default_factory=dict)


class CollectionResolver:
    """Resolves a collection of entities using traversal, selection, and canon."""

    def resolve(
        self,
        request: ResolutionRequest,
        hippo_client: HippoClientProtocol,
        canon_client: CanonClient | None = None,
    ) -> HarmonizedCollection:
        """
        Resolve entities for a request.

        Never aborts on partial failure — returns partial results.
        """
        traversal = EntityTraversal(hippo_client)

        # Traverse to get datasets
        datasets, traversal_unresolved = traversal.traverse(
            request.entity_type,
            request.criteria,
        )

        # Set up selection strategy
        selection_cfg = request.selection
        strategy_name = selection_cfg.get("strategy", "most_recent")
        strategy_kwargs: dict[str, Any] = {}
        if strategy_name == "explicit":
            strategy_kwargs["overrides"] = selection_cfg.get("overrides", {})
        elif strategy_name == "highest_quality":
            strategy_kwargs["quality_field"] = selection_cfg.get("quality_field", "quality_score")

        try:
            strategy = get_strategy(strategy_name, **strategy_kwargs)
        except ValueError as e:
            strategy = get_strategy("most_recent")

        filters = selection_cfg.get("filters", {})

        # Group datasets by sample_id (or treat each as individual)
        # For simplicity, select from all datasets as a pool
        resolved: list[ResolvedItem] = []
        unresolved: list[UnresolvedItem] = list(traversal_unresolved)

        if datasets:
            # Try to select a dataset
            try:
                selected = strategy.select(datasets, filters)
            except MultipleDatasetError as e:
                unresolved.append(
                    UnresolvedItem(
                        sample_id="collection",
                        reason="multiple_datasets",
                        detail=str(e),
                    )
                )
                selected = None
            except Exception as e:
                unresolved.append(
                    UnresolvedItem(
                        sample_id="collection",
                        reason="selection_error",
                        detail=str(e),
                    )
                )
                selected = None

            if selected is not None:
                # Canon resolution
                canon_decision = None
                if canon_client is not None:
                    try:
                        canon_decision = canon_client.resolve(
                            entity_type=request.entity_type,
                            params={**request.parameters, "dataset": selected},
                        )
                    except CanonNoRuleError:
                        canon_decision = None  # OK — no rule defined
                    except CanonTimeoutError as e:
                        unresolved.append(
                            UnresolvedItem(
                                sample_id=selected.get("id", "unknown"),
                                reason="canon_timeout",
                                detail=str(e),
                            )
                        )
                        selected = None
                    except (CanonResolveError, Exception) as e:
                        unresolved.append(
                            UnresolvedItem(
                                sample_id=selected.get("id", "unknown"),
                                reason="canon_error",
                                detail=str(e),
                            )
                        )
                        selected = None

                if selected is not None:
                    resolved.append(
                        ResolvedItem(
                            sample_id=selected.get("id", selected.get("sample_id", "unknown")),
                            entity=selected,
                            status="resolved",
                            canon_decision=canon_decision,
                        )
                    )
            elif not unresolved or all(u.sample_id == "collection" for u in unresolved):
                pass  # already tracked above

        return HarmonizedCollection(
            request={
                "entity_type": request.entity_type,
                "criteria": request.criteria,
                "parameters": request.parameters,
            },
            selection=selection_cfg,
            resolved=resolved,
            unresolved=unresolved,
            provenance={"resolved_at": datetime.utcnow().isoformat() + "Z"},
        )
