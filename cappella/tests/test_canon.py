"""Tests for CanonClient."""
import pytest

from cappella.canon.client import CanonClient, CanonDecision
from cappella.exceptions import CanonNoRuleError, CanonResolveError


def _make_stub_client(decision="REUSE", uri="uri://sample/1"):
    def stub(entity_type, params):
        return CanonDecision(decision=decision, uri=uri)
    return CanonClient(stub=stub)


class TestCanonDecision:
    def test_fields(self):
        cd = CanonDecision(decision="REUSE", uri="uri://foo/1")
        assert cd.decision == "REUSE"
        assert cd.uri == "uri://foo/1"

    def test_uri_can_be_none(self):
        cd = CanonDecision(decision="FAIL", uri=None)
        assert cd.uri is None


class TestCanonClientWithStub:
    def test_resolve_returns_decision(self):
        client = _make_stub_client(decision="REUSE", uri="uri://s/1")
        result = client.resolve("sample", {"sample_id": "S1"})
        assert isinstance(result, CanonDecision)

    def test_stub_decision_passed_through(self):
        client = _make_stub_client(decision="BUILD", uri=None)
        result = client.resolve("sample", {})
        assert result.decision == "BUILD"
        assert result.uri is None

    def test_stub_returning_dict_converted(self):
        def dict_stub(entity_type, params):
            return {"decision": "FETCH", "uri": "uri://x/2"}
        client = CanonClient(stub=dict_stub)
        result = client.resolve("sample", {})
        assert result.decision == "FETCH"
        assert result.uri == "uri://x/2"

    def test_stub_returning_bad_type_raises(self):
        def bad_stub(entity_type, params):
            return 42
        client = CanonClient(stub=bad_stub)
        with pytest.raises(CanonResolveError, match="unexpected type"):
            client.resolve("sample", {})

    @pytest.mark.parametrize("decision", ["REUSE", "FETCH", "BUILD", "FAIL"])
    def test_all_valid_decisions(self, decision):
        client = _make_stub_client(decision=decision)
        result = client.resolve("sample", {})
        assert result.decision == decision


class TestCanonClientConfig:
    def test_default_values_without_config(self):
        client = CanonClient()
        assert client._url == "http://localhost:8002"
        assert client._timeout == 30.0
        assert client._mode == "http"

    def test_cappella_config_applied(self):
        from cappella.config import CappellaConfig
        cfg = CappellaConfig()
        cfg.canon.url = "http://mycanon:9000"
        cfg.resolution.canon_timeout_seconds = 10.0
        client = CanonClient(config=cfg)
        assert client._url == "http://mycanon:9000"
        assert client._timeout == 10.0
