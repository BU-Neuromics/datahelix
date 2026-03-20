"""HTTP client for the Hippo entity store."""

from __future__ import annotations

import httpx

from canon.config import CanonConfig
from canon.exceptions import CanonExecutorError, CanonIngestionError, CanonValidationError


class HippoClient:
    """Thin synchronous HTTP client for the Hippo metadata API."""

    def __init__(self, hippo_url: str, auth_token: str = '') -> None:
        self._base = hippo_url.rstrip('/')
        self._token = auth_token

    @classmethod
    def from_config(cls, config: CanonConfig) -> 'HippoClient':
        return cls(config.hippo_url, config.hippo_token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        if self._token:
            return {'Authorization': f'Bearer {self._token}'}
        return {}

    def _raise_for_status(self, response: httpx.Response, context: str) -> None:
        if response.status_code == 404:
            raise CanonValidationError(f"Not found: {context}")
        if response.is_error:
            raise CanonExecutorError(
                f"Hippo returned {response.status_code} for {context}: {response.text}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_entities(
        self,
        entity_type: str,
        metadata_filter: dict[str, str] | None = None,
    ) -> list[dict]:
        """Return entities of *entity_type* that match all *metadata_filter* pairs."""
        params = {'entity_type': entity_type, 'limit': 1000}
        with httpx.Client() as client:
            response = client.get(
                f'{self._base}/entities',
                params=params,
                headers=self._headers(),
            )
        self._raise_for_status(response, f'query_entities({entity_type})')
        entities: list[dict] = response.json()
        if metadata_filter:
            entities = [
                e for e in entities
                if all(e.get(k) == v for k, v in metadata_filter.items())
            ]
        return entities

    def get_entity(self, entity_id: str) -> dict:
        """Fetch a single entity by ID."""
        with httpx.Client() as client:
            response = client.get(
                f'{self._base}/entities/{entity_id}',
                headers=self._headers(),
            )
        if response.status_code == 404:
            raise CanonValidationError(f"Entity not found: {entity_id}")
        if response.is_error:
            raise CanonExecutorError(
                f"Hippo returned {response.status_code} for get_entity({entity_id}): {response.text}"
            )
        return response.json()

    def ingest_entities(self, entities: list[dict]) -> list[str]:
        """Batch-ingest entities; return list of created IDs."""
        with httpx.Client() as client:
            response = client.post(
                f'{self._base}/entities/batch',
                json={'entities': entities},
                headers=self._headers(),
            )
        if response.is_error:
            raise CanonIngestionError(
                f"Hippo batch ingest failed ({response.status_code}): {response.text}"
            )
        return response.json()

    def create_entity(self, entity_type: str, data: dict) -> str:
        """Create a single entity; return its ID."""
        with httpx.Client() as client:
            response = client.post(
                f'{self._base}/entities',
                json={'entity_type': entity_type, 'data': data},
                headers=self._headers(),
            )
        if response.is_error:
            raise CanonIngestionError(
                f"Hippo entity creation failed ({response.status_code}): {response.text}"
            )
        return response.json()
