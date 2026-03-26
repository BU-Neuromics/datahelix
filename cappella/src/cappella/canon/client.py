from dataclasses import dataclass
from typing import Any, Callable, Protocol

from cappella.exceptions import CanonNoRuleError, CanonResolveError, CanonTimeoutError


@dataclass
class CanonDecision:
    decision: str  # REUSE | FETCH | BUILD | FAIL
    uri: str | None


class CanonClient:
    """Client for the Canon entity resolution service."""

    def __init__(self, config: Any = None, stub: Callable | None = None) -> None:
        self._stub = stub
        self._config = config
        self._timeout = 30.0
        self._url = "http://localhost:8002"
        self._mode = "http"

        if config is not None:
            if hasattr(config, "canon_timeout_seconds"):
                self._timeout = config.canon_timeout_seconds
            if hasattr(config, "url"):
                self._url = config.url
            if hasattr(config, "mode"):
                self._mode = config.mode
            # Support CappellaConfig-style config
            if hasattr(config, "canon"):
                canon_cfg = config.canon
                self._url = getattr(canon_cfg, "url", self._url)
                self._mode = getattr(canon_cfg, "mode", self._mode)
            if hasattr(config, "resolution"):
                res = config.resolution
                self._timeout = getattr(res, "canon_timeout_seconds", self._timeout)

    def resolve(self, entity_type: str, params: dict) -> CanonDecision:
        """Resolve an entity via the canon service."""
        if self._stub is not None:
            result = self._stub(entity_type=entity_type, params=params)
            if isinstance(result, CanonDecision):
                return result
            if isinstance(result, dict):
                return CanonDecision(decision=result["decision"], uri=result.get("uri"))
            raise CanonResolveError(f"Stub returned unexpected type: {type(result)}")

        if self._mode == "in_process":
            return self._resolve_in_process(entity_type, params)
        else:
            return self._resolve_http(entity_type, params)

    def _resolve_http(self, entity_type: str, params: dict) -> CanonDecision:
        import httpx

        try:
            response = httpx.post(
                f"{self._url}/resolve",
                json={"entity_type": entity_type, "params": params},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as e:
            raise CanonTimeoutError(f"Canon HTTP timeout: {e}")
        except Exception as e:
            raise CanonResolveError(f"Canon HTTP error: {e}")

        if response.status_code == 404:
            raise CanonNoRuleError(f"No canon rule for entity_type '{entity_type}'")
        if response.status_code != 200:
            raise CanonResolveError(f"Canon HTTP {response.status_code}: {response.text}")

        try:
            data = response.json()
            return CanonDecision(decision=data["decision"], uri=data.get("uri"))
        except Exception as e:
            raise CanonResolveError(f"Canon response parse error: {e}")

    def _resolve_in_process(self, entity_type: str, params: dict) -> CanonDecision:
        try:
            import canon  # type: ignore
            result = canon.resolve(entity_type=entity_type, params=params)
            return CanonDecision(decision=result["decision"], uri=result.get("uri"))
        except ImportError:
            raise CanonResolveError("canon package not available for in_process mode")
        except KeyError as e:
            raise CanonNoRuleError(f"No canon rule for entity_type '{entity_type}': {e}")
        except Exception as e:
            raise CanonResolveError(f"Canon in_process error: {e}")
