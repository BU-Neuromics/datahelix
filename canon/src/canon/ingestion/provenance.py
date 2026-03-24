"""WorkflowRunBuilder: records WorkflowRun provenance entities in Hippo."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from canon.types import Entity

logger = logging.getLogger(__name__)

_ENTITY_TYPE = "WorkflowRun"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowRunBuilder:
    """
    Constructs and writes WorkflowRun entities to Hippo.

    WorkflowRun records the provenance of every CWL execution: inputs,
    workflow path, timing, status, and the output entity produced.
    """

    def __init__(self, hippo_client: Any) -> None:
        self._hippo = hippo_client

    def write_running(
        self,
        rule_name: str,
        cwl_workflow: str,
        cwl_inputs: dict[str, Any],
        target_entity_type: str,
        params: dict[str, Any],
    ) -> Entity:
        """
        Create a WorkflowRun entity with status='running'.

        Args:
            rule_name: Name of the Canon production rule.
            cwl_workflow: Path to the .cwl workflow file.
            cwl_inputs: CWL input parameters dict.
            target_entity_type: The entity type being produced.
            params: Identity parameters for the target entity.

        Returns:
            Created WorkflowRun Entity.
        """
        data: dict[str, Any] = {
            "rule_name": rule_name,
            "cwl_workflow": cwl_workflow,
            "cwl_runner": "cwltool",
            "cwl_inputs": json.dumps(cwl_inputs),
            "target_entity_type": target_entity_type,
            "target_params": json.dumps(params),
            "status": "running",
            "started_at": _now_iso(),
            "completed_at": None,
            "exit_code": None,
            "output_entity_id": None,
            "error_message": None,
        }
        entity = self._hippo.ingest_entity(_ENTITY_TYPE, data)
        logger.info("WorkflowRun %s created (status=running)", entity.id)
        return entity

    def write_completed(
        self,
        run_entity_id: str,
        output_entity_id: str,
        exit_code: int,
    ) -> Entity:
        """
        Update a WorkflowRun to status='completed'.

        Args:
            run_entity_id: ID of the existing WorkflowRun entity.
            output_entity_id: ID of the produced output entity.
            exit_code: CWL process exit code.

        Returns:
            Updated WorkflowRun Entity.
        """
        data: dict[str, Any] = {
            "status": "completed",
            "completed_at": _now_iso(),
            "exit_code": exit_code,
            "output_entity_id": output_entity_id,
            "error_message": None,
        }
        entity = self._hippo.update_entity(run_entity_id, data)
        logger.info("WorkflowRun %s completed → output %s", run_entity_id, output_entity_id)
        return entity

    def write_failed(
        self,
        run_entity_id: str,
        error_message: str,
        exit_code: int,
    ) -> Entity:
        """
        Update a WorkflowRun to status='failed'.

        Args:
            run_entity_id: ID of the existing WorkflowRun entity.
            error_message: Human-readable error description.
            exit_code: CWL process exit code.

        Returns:
            Updated WorkflowRun Entity.
        """
        data: dict[str, Any] = {
            "status": "failed",
            "completed_at": _now_iso(),
            "exit_code": exit_code,
            "error_message": error_message,
            "output_entity_id": None,
        }
        entity = self._hippo.update_entity(run_entity_id, data)
        logger.warning("WorkflowRun %s failed: %s", run_entity_id, error_message)
        return entity
