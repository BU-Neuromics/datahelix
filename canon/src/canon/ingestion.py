"""Output ingestion pipeline and provenance recorder for Canon."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from canon.exceptions import CanonIngestionError
from canon.hippo_client import HippoClient
from canon.plan import CanonTask

logger = logging.getLogger(__name__)


class OutputIngestionPipeline:
    """Reads a workflow's .canon_outputs.json and ingests entities into Hippo."""

    def __init__(self, hippo_client: HippoClient) -> None:
        self._hippo = hippo_client

    def ingest(self, work_dir: Path) -> list[str]:
        outputs_file = work_dir / '.canon_outputs.json'
        try:
            raw = json.loads(outputs_file.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CanonIngestionError(f"Failed to read outputs file {outputs_file}: {exc}") from exc

        if not isinstance(raw, dict) or 'entities' not in raw:
            raise CanonIngestionError(
                f"Outputs file {outputs_file} must contain a JSON object with an 'entities' list"
            )

        entities = raw['entities']
        if not isinstance(entities, list):
            raise CanonIngestionError(
                f"'entities' in {outputs_file} must be a list"
            )

        for i, entity in enumerate(entities):
            if not isinstance(entity.get('entity_type'), str):
                raise CanonIngestionError(
                    f"Entity at index {i} is missing a string 'entity_type' field"
                )
            if not isinstance(entity.get('data'), dict):
                raise CanonIngestionError(
                    f"Entity at index {i} is missing a dict 'data' field"
                )

        return self._hippo.ingest_entities(entities)


class ProvenanceRecorder:
    """Records WorkflowRun provenance entities in Hippo (best-effort)."""

    def __init__(self, hippo_client: HippoClient) -> None:
        self._hippo = hippo_client

    def record(
        self,
        task: CanonTask,
        input_entity_ids: list[str],
        output_entity_ids: list[str],
        executor_type: str,
        work_dir: Path,
        started_at: datetime,
        finished_at: datetime,
        status: str,
    ) -> str:
        entity = {
            'entity_type': 'WorkflowRun',
            'data': {
                'rule_name': task.rule_name,
                'input_entity_ids': json.dumps(input_entity_ids),
                'output_entity_ids': json.dumps(output_entity_ids),
                'executor_type': executor_type,
                'work_dir': str(work_dir),
                'started_at': started_at.isoformat(),
                'finished_at': finished_at.isoformat(),
                'status': status,
            },
        }
        try:
            ids = self._hippo.ingest_entities([entity])
            return ids[0] if ids else ''
        except Exception as exc:
            logger.warning("Failed to record provenance for rule %r: %s", task.rule_name, exc)
            return ''
