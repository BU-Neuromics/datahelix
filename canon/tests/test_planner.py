"""Tests for RecursivePlanner."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from canon.resolver.planner import RecursivePlanner, PlanNode
from canon.rules.models import ProductionRule, ProducesSpec, ExecuteSpec
from canon.rules.registry import RuleRegistry
from canon.types import Entity, Spec
from canon.executors.base import CWLRunResult
from canon.exceptions import CanonCycleError, CanonNoRuleError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(entity_type="AlignedReads", eid="ent-uuid", uri="/data/test.bam"):
    return Entity(id=eid, entity_type=entity_type, data={"uri": uri}, uri=uri)


def _make_rule(name="r1", entity_type="AlignedReads", match=None):
    return ProductionRule(
        name=name,
        description="",
        produces=ProducesSpec(entity_type=entity_type, match=match or {"sample": "{sample}"}),
        requires=[],
        execute=ExecuteSpec(workflow="w.cwl", inputs={}),
    )


def _make_planner(hippo=None, registry=None, ref_resolver=None, executor=None, work_dir=None):
    hippo = hippo or MagicMock()
    registry = registry if registry is not None else RuleRegistry([])
    ref_resolver = ref_resolver or MagicMock()
    ref_resolver.resolve.return_value = _make_entity()
    return RecursivePlanner(
        hippo_client=hippo,
        rule_registry=registry,
        entity_ref_resolver=ref_resolver,
        executor=executor,
        work_dir_base=work_dir or "/tmp/canon-test-work",
    )


# ---------------------------------------------------------------------------
# REUSE path
# ---------------------------------------------------------------------------

def test_reuse_path_returns_uri():
    hippo = MagicMock()
    entity = _make_entity(uri="/data/test.bam")
    hippo.find_entity.return_value = entity

    planner = _make_planner(hippo=hippo)
    uri = planner.resolve("AlignedReads", {"sample": "S001"})
    assert uri == "/data/test.bam"
    hippo.find_entity.assert_called_once()


def test_reuse_path_no_rule_lookup_needed():
    """When entity exists in Hippo, registry.find_rule should NOT be called."""
    hippo = MagicMock()
    hippo.find_entity.return_value = _make_entity()
    registry = MagicMock()

    planner = _make_planner(hippo=hippo, registry=registry)
    planner.resolve("AlignedReads", {"sample": "S001"})
    registry.find_rule.assert_not_called()


# ---------------------------------------------------------------------------
# BUILD path
# ---------------------------------------------------------------------------

def test_build_path_calls_executor(tmp_path):
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])

    executor = MagicMock()
    executor.run.return_value = CWLRunResult(exit_code=0, stdout="{}", stderr="", outputs={})

    output_entity = _make_entity()
    hippo.ingest_entity.return_value = output_entity

    planner = _make_planner(
        hippo=hippo,
        registry=registry,
        executor=executor,
        work_dir=str(tmp_path),
    )
    uri = planner.resolve("AlignedReads", {"sample": "S001"})
    executor.run.assert_called_once()
    assert uri == "/data/test.bam"


def test_build_path_inputs_resolved_from_rule(tmp_path):
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity()

    rule = _make_rule()
    registry = RuleRegistry([rule])

    executor = MagicMock()
    executor.run.return_value = CWLRunResult(exit_code=0, stdout="{}", stderr="", outputs={})

    planner = _make_planner(
        hippo=hippo,
        registry=registry,
        executor=executor,
        work_dir=str(tmp_path),
    )
    planner.resolve("AlignedReads", {"sample": "S001"})
    # executor.run called with (workflow, inputs, work_dir)
    call_args = executor.run.call_args
    assert call_args[0][0] == "w.cwl"


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_cycle_detection_raises():
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)

    # Simulate the spec already being in progress
    spec = Spec(entity_type="AlignedReads", params={"sample": "S001"})
    planner._in_progress.add(spec.as_key())

    with pytest.raises(CanonCycleError):
        planner._resolve_internal("AlignedReads", {"sample": "S001"}, bindings={})


# ---------------------------------------------------------------------------
# CanonNoRuleError
# ---------------------------------------------------------------------------

def test_no_rule_raises_canon_no_rule_error():
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    registry = RuleRegistry([])  # no rules

    planner = _make_planner(hippo=hippo, registry=registry)
    with pytest.raises(CanonNoRuleError) as exc_info:
        planner.resolve("AlignedReads", {"sample": "S001"})
    assert exc_info.value.entity_type == "AlignedReads"


# ---------------------------------------------------------------------------
# plan() dry run
# ---------------------------------------------------------------------------

def test_plan_returns_reuse_node():
    hippo = MagicMock()
    entity = _make_entity(eid="ent-uuid", uri="/data/test.bam")
    hippo.find_entity.return_value = entity

    planner = _make_planner(hippo=hippo)
    node = planner.plan("AlignedReads", {"sample": "S001"})
    assert isinstance(node, PlanNode)
    assert node.decision == "REUSE"
    assert node.entity_id == "ent-uuid"
    assert node.uri == "/data/test.bam"
    assert node.entity_type == "AlignedReads"


def test_plan_returns_build_node_with_rule_name():
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule(name="r1")
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)
    node = planner.plan("AlignedReads", {"sample": "S001"})
    assert node.decision == "BUILD"
    assert node.rule_name == "r1"
    assert node.children == []


def test_plan_does_not_call_executor():
    """plan() must never invoke the executor."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule()
    registry = RuleRegistry([rule])
    executor = MagicMock()

    planner = _make_planner(hippo=hippo, registry=registry, executor=executor)
    planner.plan("AlignedReads", {"sample": "S001"})
    executor.run.assert_not_called()


# ---------------------------------------------------------------------------
# FETCH path — helpers and tests
# ---------------------------------------------------------------------------

from canon.rules.models import FetchRule
from canon.rules.models import ProducesSpec as FetchProducesSpec


def _make_fetch_rule(name="fetch-genome", entity_type="GenomeBuild", match=None, checksum=None):
    return FetchRule(
        name=name,
        produces=ProducesSpec(
            entity_type=entity_type,
            match=match or {"name": "GRCh38"},
        ),
        source_uri="https://example.com/genome.fa.gz",
        checksum_sha256=checksum,
    )


def _make_planner_with_fetch(
    hippo=None,
    registry=None,
    storage_adapter=None,
    https_adapter=None,
    executor=None,
    work_dir="/tmp/canon-test-work",
):
    hippo = hippo or MagicMock()
    registry = registry if registry is not None else RuleRegistry([])
    ref_resolver = MagicMock()
    ref_resolver.resolve.return_value = _make_entity()
    storage_adapter = storage_adapter or MagicMock()
    https_adapter = https_adapter or MagicMock()
    return RecursivePlanner(
        hippo_client=hippo,
        rule_registry=registry,
        entity_ref_resolver=ref_resolver,
        executor=executor,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir_base=work_dir,
    )


def test_reuse_wins_when_uri_accessible():
    """REUSE when entity exists with uri AND storage_adapter.exists(uri) is True."""
    hippo = MagicMock()
    entity = _make_entity(uri="file:///data/genome.fa.gz")
    hippo.find_entity.return_value = entity

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = True

    planner = _make_planner_with_fetch(hippo=hippo, registry=registry, storage_adapter=storage_adapter)
    node = planner.plan("GenomeBuild", {"name": "GRCh38"})
    assert node.decision == "REUSE"


def test_fetch_triggered_when_entity_uri_absent():
    """FETCH when entity exists but uri is None and fetch rule matches."""
    hippo = MagicMock()
    entity = Entity(id="ent-1", entity_type="GenomeBuild", data={}, uri=None)
    hippo.find_entity.return_value = entity

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False  # dest not cached
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()
    https_adapter.get.return_value = MagicMock()  # local path

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
    )
    node = planner.plan("GenomeBuild", {"name": "GRCh38"})
    assert node.decision == "FETCH"


def test_fetch_triggered_when_entity_uri_inaccessible():
    """FETCH when entity exists with uri but storage_adapter.exists(uri) returns False."""
    hippo = MagicMock()
    entity = _make_entity(entity_type="GenomeBuild", uri="file:///old/path/genome.fa.gz")
    hippo.find_entity.return_value = entity

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    # First call (checking entity uri): False; second call (checking dest_uri): False
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry, storage_adapter=storage_adapter
    )
    node = planner.plan("GenomeBuild", {"name": "GRCh38"})
    assert node.decision == "FETCH"


def test_fetch_triggered_when_no_entity():
    """FETCH when no entity in Hippo but fetch rule matches."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry, storage_adapter=storage_adapter
    )
    node = planner.plan("GenomeBuild", {"name": "GRCh38"})
    assert node.decision == "FETCH"


def test_build_triggered_when_no_entity_no_fetch_rule():
    """BUILD when no entity, no fetch rule, but production rule exists."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule(entity_type="AlignedReads")
    registry = RuleRegistry([rule])

    storage_adapter = MagicMock()
    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry, storage_adapter=storage_adapter
    )
    node = planner.plan("AlignedReads", {"sample": "S001"})
    assert node.decision == "BUILD"


def test_fail_when_no_entity_no_rule():
    """FAIL when no entity and no applicable rule."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    registry = RuleRegistry([])

    planner = _make_planner_with_fetch(hippo=hippo, registry=registry)
    with pytest.raises(CanonNoRuleError):
        planner.plan("GenomeBuild", {"name": "GRCh38"})


def test_plan_returns_fetch_node_with_source_uri():
    """plan() returns PlanNode with decision='FETCH' and source_uri in metadata."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry, storage_adapter=storage_adapter
    )
    node = planner.plan("GenomeBuild", {"name": "GRCh38"})
    assert node.decision == "FETCH"
    assert node.metadata.get("source_uri") == "https://example.com/genome.fa.gz"


def test_skip_download_when_dest_exists(tmp_path):
    """When dest_uri already exists, get() is NOT called."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = True
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"
    storage_adapter.put.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    planner.resolve("GenomeBuild", {"name": "GRCh38"})
    https_adapter.get.assert_not_called()


def test_download_when_dest_absent(tmp_path):
    """When dest_uri absent, get() and put() are called."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")
    hippo.update_entity.return_value = None

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    local_file = tmp_path / "genome.fa.gz"
    local_file.write_bytes(b"GENOME_DATA")

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"
    storage_adapter.put.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()
    https_adapter.get.return_value = local_file

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    planner.resolve("GenomeBuild", {"name": "GRCh38"})
    https_adapter.get.assert_called_once()
    storage_adapter.put.assert_called_once()


def test_checksum_match_proceeds(tmp_path):
    """Checksum match → download and put proceed normally."""
    import hashlib

    data = b"GENOME_DATA"
    checksum = hashlib.sha256(data).hexdigest()

    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")
    hippo.update_entity.return_value = None

    fetch_rule = _make_fetch_rule(checksum=checksum)
    registry = RuleRegistry([fetch_rule])

    local_file = tmp_path / "genome.fa.gz"
    local_file.write_bytes(data)

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"
    storage_adapter.put.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()
    https_adapter.get.return_value = local_file

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    planner.resolve("GenomeBuild", {"name": "GRCh38"})
    storage_adapter.put.assert_called_once()


def test_checksum_mismatch_raises(tmp_path):
    """Checksum mismatch → CanonStorageError raised, entity not updated."""
    from canon.exceptions import CanonStorageError

    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")

    fetch_rule = _make_fetch_rule(checksum="wrong_checksum_expected")
    registry = RuleRegistry([fetch_rule])

    local_file = tmp_path / "genome.fa.gz"
    local_file.write_bytes(b"ACTUAL_DATA")

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()
    https_adapter.get.return_value = local_file

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    with pytest.raises(CanonStorageError, match="checksum"):
        planner.resolve("GenomeBuild", {"name": "GRCh38"})
    hippo.update_entity.assert_not_called()
    storage_adapter.put.assert_not_called()


def test_fetch_completed_event_recorded(tmp_path):
    """FetchCompleted event is recorded on entity after download."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")
    hippo.update_entity.return_value = None

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    local_file = tmp_path / "genome.fa.gz"
    local_file.write_bytes(b"GENOME_DATA")

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = False
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"
    storage_adapter.put.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()
    https_adapter.get.return_value = local_file

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    planner.resolve("GenomeBuild", {"name": "GRCh38"})

    hippo.update_entity.assert_called_once()
    call_kwargs = hippo.update_entity.call_args
    update_data = call_kwargs[0][1] if call_kwargs[0] else call_kwargs[1].get("data", {})
    # Accept both positional and keyword call patterns
    all_args = list(call_kwargs[0]) + list(call_kwargs[1].values())
    update_dict = next((a for a in all_args if isinstance(a, dict)), {})
    assert update_dict.get("fetch_status") == "FetchCompleted"


# ---------------------------------------------------------------------------
# Glob wildcard "*" partial specification matching
# ---------------------------------------------------------------------------

def _make_rule_with_glob(
    name="r-glob",
    entity_type="AlignmentFile",
    match=None,
):
    return ProductionRule(
        name=name,
        description="",
        produces=ProducesSpec(
            entity_type=entity_type,
            match=match or {"sample_id": "{sample_id}", "genome": "{genome}", "tool_version": "*"},
        ),
        requires=[],
        execute=ExecuteSpec(workflow="w.cwl", inputs={}),
    )


def test_plan_build_with_glob_wildcard_field_absent():
    """plan() resolves BUILD when rule has '*' and caller omits that field."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule_with_glob()
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)

    # tool_version NOT supplied — glob wildcard allows it
    node = planner.plan("AlignmentFile", {"sample_id": "S001", "genome": "GRCh38"})
    assert node.decision == "BUILD"
    assert node.rule_name == "r-glob"


def test_plan_build_with_glob_wildcard_field_present():
    """plan() resolves BUILD when rule has '*' and caller provides the field."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule_with_glob()
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)

    node = planner.plan(
        "AlignmentFile",
        {"sample_id": "S001", "genome": "GRCh38", "tool_version": "2.7.10a"},
    )
    assert node.decision == "BUILD"
    assert node.rule_name == "r-glob"


def test_resolve_build_with_glob_wildcard(tmp_path):
    """resolve() executes successfully when rule uses '*' and field is absent from request."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="AlignmentFile")

    rule = _make_rule_with_glob()
    registry = RuleRegistry([rule])

    executor = MagicMock()
    executor.run.return_value = CWLRunResult(exit_code=0, stdout="{}", stderr="", outputs={})

    planner = _make_planner(
        hippo=hippo, registry=registry, executor=executor, work_dir=str(tmp_path)
    )
    uri = planner.resolve("AlignmentFile", {"sample_id": "S001", "genome": "GRCh38"})
    assert uri == "/data/test.bam"
    executor.run.assert_called_once()


def test_glob_wildcard_does_not_create_binding():
    """'*' wildcards produce no named binding — named wildcards from the same rule still bind."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None

    rule = _make_rule_with_glob()
    registry = RuleRegistry([rule])
    planner = _make_planner(hippo=hippo, registry=registry)

    bindings = planner._bind_wildcards(
        rule,
        resolved_params={"sample_id": "S001", "genome": "GRCh38"},
        parent_bindings={},
    )
    # Named wildcards are bound
    assert bindings["sample_id"] == "S001"
    assert bindings["genome"] == "GRCh38"
    # No binding created for the glob field
    assert "tool_version" not in bindings


def test_fetch_skipped_event_recorded(tmp_path):
    """FetchSkipped event is recorded on entity when dest already exists."""
    hippo = MagicMock()
    hippo.find_entity.return_value = None
    hippo.ingest_entity.return_value = _make_entity(entity_type="GenomeBuild")
    hippo.update_entity.return_value = None

    fetch_rule = _make_fetch_rule()
    registry = RuleRegistry([fetch_rule])

    storage_adapter = MagicMock()
    storage_adapter.exists.return_value = True
    storage_adapter.build_dest_uri.return_value = "file:///storage/genome.fa.gz"

    https_adapter = MagicMock()

    planner = _make_planner_with_fetch(
        hippo=hippo, registry=registry,
        storage_adapter=storage_adapter,
        https_adapter=https_adapter,
        work_dir=str(tmp_path),
    )
    planner.resolve("GenomeBuild", {"name": "GRCh38"})

    hippo.update_entity.assert_called_once()
    call_kwargs = hippo.update_entity.call_args
    all_args = list(call_kwargs[0]) + list(call_kwargs[1].values())
    update_dict = next((a for a in all_args if isinstance(a, dict)), {})
    assert update_dict.get("fetch_status") == "FetchSkipped"
