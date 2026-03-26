from typing import Any, Protocol, runtime_checkable

from cappella.types import UnresolvedItem


@runtime_checkable
class HippoClientProtocol(Protocol):
    def schema_references(self, entity_type: str) -> list[str]:
        ...

    def query(self, entity_type: str, filters: dict) -> list[dict]:
        ...

    def get_by_external_id(self, system: str, external_id: str) -> dict | None:
        ...

    def create(self, entity_type: str, data: dict, context: dict) -> dict:
        ...

    def update(self, entity_id: str, data: dict, context: dict) -> dict:
        ...


class EntityTraversal:
    """Schema-driven traversal of entity relationships via Hippo."""

    def __init__(self, hippo_client: HippoClientProtocol) -> None:
        self.hippo_client = hippo_client

    def traverse(
        self,
        entity_type: str,
        criteria: dict[str, Any],
    ) -> tuple[list[dict], list[UnresolvedItem]]:
        """
        Traverse entity relationships starting from entity_type with given criteria.

        Returns (datasets, unresolved) where:
        - datasets: list of dataset dicts found at the end of the traversal
        - unresolved: list of UnresolvedItem for samples with no datasets
        """
        # Get all entities matching top-level criteria
        try:
            entities = self.hippo_client.query(entity_type, criteria)
        except Exception as e:
            return [], [
                UnresolvedItem(
                    sample_id="unknown",
                    reason="traversal_error",
                    detail=str(e),
                )
            ]

        if not entities:
            return [], []

        # Get schema references to traverse
        try:
            refs = self.hippo_client.schema_references(entity_type)
        except Exception:
            refs = []

        if not refs:
            # This entity_type IS the dataset level
            return entities, []

        # Traverse to child entity types
        datasets: list[dict] = []
        unresolved: list[UnresolvedItem] = []

        for entity in entities:
            entity_id = entity.get("id", entity.get("_id", ""))
            sample_id = entity.get("sample_id", entity_id)

            found_datasets = False
            for ref_type in refs:
                try:
                    child_entities = self.hippo_client.query(
                        ref_type,
                        {"parent_id": entity_id},
                    )
                    if child_entities:
                        datasets.extend(child_entities)
                        found_datasets = True
                except Exception as e:
                    unresolved.append(
                        UnresolvedItem(
                            sample_id=str(sample_id),
                            reason="traversal_error",
                            detail=f"Failed to query {ref_type}: {e}",
                        )
                    )

            if not found_datasets and not any(u.sample_id == str(sample_id) for u in unresolved):
                unresolved.append(
                    UnresolvedItem(
                        sample_id=str(sample_id),
                        reason="no_datasets_found",
                        detail=f"No {refs} found for entity {entity_id}",
                    )
                )

        return datasets, unresolved
