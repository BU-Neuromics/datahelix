"""Canon exception hierarchy."""

from __future__ import annotations


class CanonError(Exception):
    """Base class for all Canon errors."""


class CanonConfigError(CanonError):
    """Raised at startup: bad config, missing schema, unavailable executor."""


class CanonRuleValidationError(CanonError):
    """Raised at startup: invalid rule syntax, missing CWL file, bad sidecar."""


class CanonResolutionError(CanonError):
    """Raised when a ref: expression matches zero or more than one entity."""


class CanonPlanningError(CanonError):
    """Raised when a wildcard is unbound or a required parameter is missing."""


class CanonNoRuleError(CanonError):
    """Raised when no rule exists to produce the requested entity."""

    def __init__(
        self,
        entity_type: str,
        params: dict,
        available: list | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.params = params
        self.available = available or []
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        available_str = ""
        if self.available:
            rule_lines = "\n  ".join(
                f"{r.name}  (produces {r.produces.entity_type})" for r in self.available
            )
            available_str = f"\n\nInstalled rules for {entity_type}:\n  {rule_lines}"
        super().__init__(
            f"No rule found to produce {entity_type} with parameters:\n  {param_str}"
            + available_str
        )


class CanonCycleError(CanonError):
    """Raised when a circular rule dependency is detected."""

    def __init__(self, message: str, cycle_path: list | None = None) -> None:
        self.cycle_path = cycle_path or []
        super().__init__(message)


class CanonExecutorError(CanonError):
    """Raised when CWL execution fails or a duplicate execution is in progress."""


class CanonIngestionError(CanonError):
    """Raised when output ingestion to Hippo fails."""


class CanonStorageError(CanonError):
    """Raised when a storage adapter operation fails (put, get, exists)."""
