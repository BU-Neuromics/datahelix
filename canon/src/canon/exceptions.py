"""Canon exception hierarchy."""


class CanonError(Exception):
    """Base class for all Canon errors."""


class CanonPlanningError(CanonError):
    """Raised when the planner cannot build a valid execution plan."""


class CanonCycleError(CanonPlanningError):
    """Raised when a dependency cycle is detected during planning."""

    def __init__(self, message: str, cycle_path: list[str] | None = None) -> None:
        super().__init__(message)
        self.cycle_path: list[str] = cycle_path or []


class CanonValidationError(CanonError):
    """Raised when configuration or rule validation fails."""


class CanonExecutorError(CanonError):
    """Raised when a workflow executor encounters an error."""


class CanonIngestionError(CanonError):
    """Raised when entity ingestion into Hippo fails."""
