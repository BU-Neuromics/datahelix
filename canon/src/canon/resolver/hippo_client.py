"""MosaicQueryClient: Canon's HTTP client for the Mosaic entity registry."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from canon.config import CanonConfig
from canon.exceptions import CanonConfigError, CanonIngestionError, CanonResolutionError
from canon.types import Entity

logger = logging.getLogger(__name__)


def _entity_from_response(data: dict) -> Entity:
    """Construct an Entity from a Mosaic API response dict."""
    entity_id = data.get("id") or data.get("uuid") or data.get("entity_id", "")
    entity_type = data.get("entity_type", "")
    entity_data = data.get("data") or data.get("fields") or data
    uri = entity_data.get("uri") if isinstance(entity_data, dict) else None
    return Entity(id=str(entity_id), entity_type=entity_type, data=entity_data, uri=uri)


class MosaicQueryClient:
    """
    Thin HTTP client for Canon's interactions with the Mosaic entity registry.

    All calls are synchronous (httpx sync). Canon does not require async in v0.1.
    """

    def __init__(self, config: CanonConfig) -> None:
        self._base_url = config.mosaic_url.rstrip("/")
        self._token = config.mosaic_token
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "MosaicQueryClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> Any:
        """Execute a GET request and return the parsed JSON."""
        logger.debug("GET %s params=%s", path, params)
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CanonResolutionError(
                f"Mosaic API error {e.response.status_code} for GET {path}: "
                f"{e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise CanonConfigError(
                f"Cannot reach Mosaic at {self._base_url}: {e}"
            ) from e

    def _post(self, path: str, body: dict) -> Any:
        """Execute a POST request and return the parsed JSON."""
        logger.debug("POST %s body=%s", path, body)
        try:
            response = self._client.post(path, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CanonIngestionError(
                f"Mosaic API error {e.response.status_code} for POST {path}: "
                f"{e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise CanonConfigError(
                f"Cannot reach Mosaic at {self._base_url}: {e}"
            ) from e

    def _put(self, path: str, body: dict) -> Any:
        """Execute a PUT request and return the parsed JSON."""
        logger.debug("PUT %s body=%s", path, body)
        try:
            response = self._client.put(path, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CanonIngestionError(
                f"Mosaic API error {e.response.status_code} for PUT {path}: "
                f"{e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise CanonConfigError(
                f"Cannot reach Mosaic at {self._base_url}: {e}"
            ) from e

    def find_entity(
        self,
        entity_type: str,
        filters: dict[str, Any],
    ) -> Entity | None:
        """
        Query Mosaic for exactly one entity matching all filters.

        Returns None if no match. Raises CanonResolutionError if multiple match.

        GET /entities?entity_type=X&field=val&...
        """
        params = {"entity_type": entity_type, **{str(k): str(v) for k, v in filters.items()}}
        results = self._get("/entities", params=params)

        if isinstance(results, dict) and "results" in results:
            items = results["results"]
        elif isinstance(results, list):
            items = results
        else:
            items = []

        logger.debug(
            "find_entity %s filters=%s → %d result(s)", entity_type, filters, len(items)
        )

        if len(items) == 0:
            return None
        if len(items) > 1:
            raise CanonResolutionError(
                f"Ambiguous entity lookup: {len(items)} {entity_type} entities match "
                f"{filters}. Provide additional fields to disambiguate."
            )
        return _entity_from_response(items[0])

    def find_entities(
        self,
        entity_type: str,
        filters: dict[str, Any],
    ) -> list[Entity]:
        """
        Query Mosaic for all entities matching filters.

        Used by EntityRefResolver for ref: expressions.

        GET /entities?entity_type=X&field=val&...&limit=10
        """
        params = {
            "entity_type": entity_type,
            **{str(k): str(v) for k, v in filters.items()},
            "limit": "10",
        }
        results = self._get("/entities", params=params)

        if isinstance(results, dict) and "results" in results:
            items = results["results"]
        elif isinstance(results, list):
            items = results
        else:
            items = []

        logger.debug(
            "find_entities %s filters=%s → %d result(s)", entity_type, filters, len(items)
        )
        return [_entity_from_response(item) for item in items]

    def get_entity(self, entity_id: str) -> Entity:
        """
        Fetch a single entity by UUID.

        GET /entities/{entity_id}
        """
        result = self._get(f"/entities/{entity_id}")
        return _entity_from_response(result)

    def ingest_entity(
        self,
        entity_type: str,
        data: dict[str, Any],
    ) -> Entity:
        """
        Create a new entity in Mosaic.

        POST /ingest  body: {"entity_type": X, "data": {...}}
        Returns the created entity with its assigned UUID.
        """
        body = {"entity_type": entity_type, "data": data}
        result = self._post("/ingest", body)
        return _entity_from_response(result)

    def update_entity(self, entity_id: str, data: dict[str, Any]) -> Entity:
        """
        Update fields on an existing entity.

        PUT /entities/{entity_id}
        """
        result = self._put(f"/entities/{entity_id}", data)
        return _entity_from_response(result)

    def find_workflow_run(
        self,
        entity_type: str,
        params: dict[str, Any],
        status: str,
    ) -> Entity | None:
        """
        Check for an existing WorkflowRun for this artifact spec with the given status.

        Used to detect in-progress or failed runs and prevent duplicate execution.
        """
        # Build a filter that looks for WorkflowRun matching rule output params + status
        filters: dict[str, Any] = {
            "target_entity_type": entity_type,
            "status": status,
        }
        # Include a subset of params as filters (stringified)
        for k, v in params.items():
            filters[f"param_{k}"] = str(v)

        try:
            result = self._get("/entities", params={"entity_type": "WorkflowRun", **filters})
        except (CanonResolutionError, CanonConfigError):
            # If querying for WorkflowRun fails (e.g. type not in schema yet), return None
            return None

        if isinstance(result, dict) and "results" in result:
            items = result["results"]
        elif isinstance(result, list):
            items = result
        else:
            items = []

        if not items:
            return None
        return _entity_from_response(items[0])

    def check_health(self) -> dict:
        """
        GET /health — verify Mosaic is reachable and return version info.

        Raises CanonConfigError if unreachable.
        """
        try:
            return self._get("/health")
        except CanonResolutionError as e:
            raise CanonConfigError(
                f"canon.yaml: cannot reach Mosaic at {self._base_url}/health — {e}"
            ) from e
