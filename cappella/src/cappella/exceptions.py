class CappellaError(Exception):
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}


class ConfigError(CappellaError):
    pass


class AdapterError(CappellaError):
    pass


class AdapterFetchError(AdapterError):
    pass


class AdapterTransformError(AdapterError):
    pass


class CanonError(CappellaError):
    pass


class CanonNoRuleError(CanonError):
    pass


class CanonResolveError(CanonError):
    pass


class CanonTimeoutError(CanonError):
    pass


class TriggerError(CappellaError):
    pass


class ReconciliationError(CappellaError):
    pass


class MultipleDatasetError(CappellaError):
    pass
