import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cappella.exceptions import ReconciliationError


@dataclass
class ReconciliationFinding:
    finding_id: str
    check: str
    entity_type: str
    entity_id: str
    severity: str  # "error" | "warning" | "info"
    detail: str
    suggested_action: str
    source_a: str | None = None
    source_b: str | None = None


@dataclass
class ReconciliationRequest:
    entity_type: str
    checks: list[str] | None = None  # None means run all
    parameters: dict[str, Any] = field(default_factory=dict)


class MissingEntityCheck:
    """Check for entities referenced by external systems but missing in Hippo."""

    name = "missing_entity"

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        findings = []
        try:
            # Query for entities with a "missing" flag or check external references
            entities = hippo_client.query(request.entity_type, {"check": "missing"})
            for entity in entities:
                findings.append(
                    ReconciliationFinding(
                        finding_id=str(uuid.uuid4()),
                        check=self.name,
                        entity_type=request.entity_type,
                        entity_id=entity.get("id", "unknown"),
                        severity="error",
                        detail=f"Entity referenced but not found in Hippo",
                        suggested_action="Create entity in Hippo or remove external reference",
                    )
                )
        except Exception as e:
            findings.append(
                ReconciliationFinding(
                    finding_id=str(uuid.uuid4()),
                    check=self.name,
                    entity_type=request.entity_type,
                    entity_id="unknown",
                    severity="error",
                    detail=f"Check failed: {e}",
                    suggested_action="Investigate check error",
                )
            )
        return findings


class StaleEntityCheck:
    """Check for entities not updated within a staleness threshold."""

    name = "stale_entity"

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        findings = []
        threshold_days = request.parameters.get("threshold_days", 30)
        try:
            entities = hippo_client.query(request.entity_type, {})
            now = datetime.now(tz=timezone.utc)
            for entity in entities:
                updated_at_str = entity.get("updated_at") or entity.get("created_at")
                if updated_at_str:
                    try:
                        if isinstance(updated_at_str, str):
                            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        else:
                            updated_at = updated_at_str
                        age_days = (now - updated_at).days
                        if age_days > threshold_days:
                            findings.append(
                                ReconciliationFinding(
                                    finding_id=str(uuid.uuid4()),
                                    check=self.name,
                                    entity_type=request.entity_type,
                                    entity_id=entity.get("id", "unknown"),
                                    severity="warning",
                                    detail=f"Entity not updated for {age_days} days (threshold: {threshold_days})",
                                    suggested_action="Review and update entity data",
                                )
                            )
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            findings.append(
                ReconciliationFinding(
                    finding_id=str(uuid.uuid4()),
                    check=self.name,
                    entity_type=request.entity_type,
                    entity_id="unknown",
                    severity="error",
                    detail=f"Check failed: {e}",
                    suggested_action="Investigate check error",
                )
            )
        return findings


class FieldConflictCheck:
    """Check for field value conflicts across sources."""

    name = "field_conflict"

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        findings = []
        fields_to_check = request.parameters.get("fields", [])
        try:
            entities = hippo_client.query(request.entity_type, {})
            for entity in entities:
                conflicts = entity.get("_conflicts", {})
                for field_name, conflict_info in conflicts.items():
                    if not fields_to_check or field_name in fields_to_check:
                        findings.append(
                            ReconciliationFinding(
                                finding_id=str(uuid.uuid4()),
                                check=self.name,
                                entity_type=request.entity_type,
                                entity_id=entity.get("id", "unknown"),
                                severity="warning",
                                detail=f"Field '{field_name}' has conflicting values across sources",
                                suggested_action="Manually resolve conflict or adjust trust levels",
                                source_a=conflict_info.get("source_a"),
                                source_b=conflict_info.get("source_b"),
                            )
                        )
        except Exception as e:
            findings.append(
                ReconciliationFinding(
                    finding_id=str(uuid.uuid4()),
                    check=self.name,
                    entity_type=request.entity_type,
                    entity_id="unknown",
                    severity="error",
                    detail=f"Check failed: {e}",
                    suggested_action="Investigate check error",
                )
            )
        return findings


class BrokenReferenceCheck:
    """Check for broken entity references (dangling foreign keys)."""

    name = "broken_reference"

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        findings = []
        try:
            entities = hippo_client.query(request.entity_type, {})
            for entity in entities:
                broken_refs = entity.get("_broken_refs", [])
                for ref in broken_refs:
                    findings.append(
                        ReconciliationFinding(
                            finding_id=str(uuid.uuid4()),
                            check=self.name,
                            entity_type=request.entity_type,
                            entity_id=entity.get("id", "unknown"),
                            severity="error",
                            detail=f"Broken reference to '{ref}'",
                            suggested_action="Fix or remove the broken reference",
                        )
                    )
        except Exception as e:
            findings.append(
                ReconciliationFinding(
                    finding_id=str(uuid.uuid4()),
                    check=self.name,
                    entity_type=request.entity_type,
                    entity_id="unknown",
                    severity="error",
                    detail=f"Check failed: {e}",
                    suggested_action="Investigate check error",
                )
            )
        return findings


class MissingArtifactCheck:
    """Check for entities missing expected artifacts (files, reports, etc.)."""

    name = "missing_artifact"

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        findings = []
        required_artifacts = request.parameters.get("required_artifacts", [])
        try:
            entities = hippo_client.query(request.entity_type, {})
            for entity in entities:
                entity_artifacts = set(entity.get("artifacts", []))
                for artifact in required_artifacts:
                    if artifact not in entity_artifacts:
                        findings.append(
                            ReconciliationFinding(
                                finding_id=str(uuid.uuid4()),
                                check=self.name,
                                entity_type=request.entity_type,
                                entity_id=entity.get("id", "unknown"),
                                severity="warning",
                                detail=f"Missing required artifact: '{artifact}'",
                                suggested_action=f"Generate or upload artifact '{artifact}'",
                            )
                        )
        except Exception as e:
            findings.append(
                ReconciliationFinding(
                    finding_id=str(uuid.uuid4()),
                    check=self.name,
                    entity_type=request.entity_type,
                    entity_id="unknown",
                    severity="error",
                    detail=f"Check failed: {e}",
                    suggested_action="Investigate check error",
                )
            )
        return findings


_ALL_CHECKS: dict[str, Any] = {
    "missing_entity": MissingEntityCheck,
    "stale_entity": StaleEntityCheck,
    "field_conflict": FieldConflictCheck,
    "broken_reference": BrokenReferenceCheck,
    "missing_artifact": MissingArtifactCheck,
}


class ReconciliationEngine:
    """Runs reconciliation checks and returns findings."""

    def __init__(self) -> None:
        self._checks = {name: cls() for name, cls in _ALL_CHECKS.items()}

    def run(
        self,
        request: ReconciliationRequest,
        hippo_client: Any,
    ) -> list[ReconciliationFinding]:
        """Run selected checks. Never aborts on partial failure."""
        checks_to_run = request.checks or list(self._checks.keys())
        all_findings: list[ReconciliationFinding] = []

        for check_name in checks_to_run:
            check = self._checks.get(check_name)
            if check is None:
                all_findings.append(
                    ReconciliationFinding(
                        finding_id=str(uuid.uuid4()),
                        check=check_name,
                        entity_type=request.entity_type,
                        entity_id="unknown",
                        severity="error",
                        detail=f"Unknown check: '{check_name}'",
                        suggested_action="Use a valid check name",
                    )
                )
                continue

            try:
                findings = check.run(request, hippo_client)
                all_findings.extend(findings)
            except Exception as e:
                all_findings.append(
                    ReconciliationFinding(
                        finding_id=str(uuid.uuid4()),
                        check=check_name,
                        entity_type=request.entity_type,
                        entity_id="unknown",
                        severity="error",
                        detail=f"Check '{check_name}' raised an error: {e}",
                        suggested_action="Investigate the check error",
                    )
                )

        return all_findings


class FindingsStore:
    """In-memory store for reconciliation findings."""

    def __init__(self) -> None:
        self._findings: list[ReconciliationFinding] = []

    def store(self, finding: ReconciliationFinding) -> None:
        self._findings.append(finding)

    def store_many(self, findings: list[ReconciliationFinding]) -> None:
        self._findings.extend(findings)

    def query(
        self,
        entity_type: str | None = None,
        check: str | None = None,
        severity: str | None = None,
    ) -> list[ReconciliationFinding]:
        results = self._findings
        if entity_type is not None:
            results = [f for f in results if f.entity_type == entity_type]
        if check is not None:
            results = [f for f in results if f.check == check]
        if severity is not None:
            results = [f for f in results if f.severity == severity]
        return results

    def clear(self) -> None:
        self._findings = []

    def count(self) -> int:
        return len(self._findings)
