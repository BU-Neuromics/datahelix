"""Tests for the exception hierarchy."""
import pytest

from cappella.exceptions import (
    AdapterError,
    AdapterFetchError,
    AdapterTransformError,
    CanonError,
    CanonNoRuleError,
    CanonResolveError,
    CanonTimeoutError,
    CappellaError,
    ConfigError,
    MultipleDatasetError,
    ReconciliationError,
    TriggerError,
)


class TestExceptionHierarchy:
    def test_cappella_error_is_exception(self):
        assert issubclass(CappellaError, Exception)

    def test_config_error_inherits_cappella(self):
        assert issubclass(ConfigError, CappellaError)

    def test_adapter_error_inherits_cappella(self):
        assert issubclass(AdapterError, CappellaError)

    def test_adapter_fetch_error_inherits_adapter(self):
        assert issubclass(AdapterFetchError, AdapterError)

    def test_adapter_transform_error_inherits_adapter(self):
        assert issubclass(AdapterTransformError, AdapterError)

    def test_canon_error_inherits_cappella(self):
        assert issubclass(CanonError, CappellaError)

    def test_canon_no_rule_error_inherits_canon(self):
        assert issubclass(CanonNoRuleError, CanonError)

    def test_canon_resolve_error_inherits_canon(self):
        assert issubclass(CanonResolveError, CanonError)

    def test_canon_timeout_error_inherits_canon(self):
        assert issubclass(CanonTimeoutError, CanonError)

    def test_trigger_error_inherits_cappella(self):
        assert issubclass(TriggerError, CappellaError)

    def test_reconciliation_error_inherits_cappella(self):
        assert issubclass(ReconciliationError, CappellaError)

    def test_multiple_dataset_error_inherits_cappella(self):
        assert issubclass(MultipleDatasetError, CappellaError)


class TestCappellaErrorContext:
    def test_message_stored(self):
        err = CappellaError("something went wrong")
        assert str(err) == "something went wrong"

    def test_context_defaults_to_empty_dict(self):
        err = CappellaError("oops")
        assert err.context == {}

    def test_context_stored_when_provided(self):
        err = CappellaError("oops", {"key": "value"})
        assert err.context == {"key": "value"}

    def test_subclass_inherits_context(self):
        err = AdapterFetchError("fetch failed", {"adapter": "csv"})
        assert err.context["adapter"] == "csv"
        assert isinstance(err, CappellaError)

    def test_caught_as_cappella_error(self):
        with pytest.raises(CappellaError):
            raise ConfigError("bad config")

    def test_caught_as_adapter_error(self):
        with pytest.raises(AdapterError):
            raise AdapterFetchError("fetch broke")

    def test_caught_as_canon_error(self):
        with pytest.raises(CanonError):
            raise CanonTimeoutError("timed out")
