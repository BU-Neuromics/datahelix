"""OutputIngestionPipeline: post-CWL output parsing and Hippo entity ingestion."""

from __future__ import annotations

import logging
import shutil
import uuid
import warnings
from datetime import date
from pathlib import Path
from typing import Any

from canon.config import CanonConfig
from canon.exceptions import CanonIngestionError
from canon.executors.base import CWLRunResult
from canon.ingestion.sidecar import evaluate_hippo_fields, load_sidecar
from canon.types import Entity

logger = logging.getLogger(__name__)


class OutputIngestionPipeline:
    """
    Ingests CWL outputs into Hippo after a successful workflow run.

    For each sidecar output definition:
      1. Evaluate hippo_fields expressions against CWL outputs + inputs
      2. Optionally relocate output files to managed storage
      3. POST entity to Hippo
    """

    def __init__(self, hippo_client: Any, config: CanonConfig) -> None:
        self._hippo = hippo_client
        self._config = config

    def relocate_output(
        self,
        cwl_output_path: str,
        entity_type: str,
        run_id: str,
    ) -> str:
        """
        Move a CWL output file to managed storage.

        For type=local: copies to <base_path>/<entity_type>/<date>/<run_id>/<filename>
        For type=s3: returns original URI with a warning (not implemented in v0.1).

        Args:
            cwl_output_path: Current file path (local URI or path).
            entity_type: Hippo entity type (used in destination path).
            run_id: Run UUID (used in destination path).

        Returns:
            New URI or path string.
        """
        storage = self._config.output_storage

        if storage.type == "s3":
            warnings.warn(
                f"S3 output relocation is not implemented in v0.1. "
                f"Returning original URI: {cwl_output_path}",
                stacklevel=2,
            )
            return cwl_output_path

        # Local storage
        base = Path(storage.base_path)  # type: ignore[arg-type]
        today = date.today().isoformat()
        src = Path(cwl_output_path.removeprefix("file://"))
        dest_dir = base / entity_type / today / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        try:
            shutil.copy2(src, dest)
            logger.info("Relocated %s → %s", src, dest)
        except OSError as e:
            raise CanonIngestionError(
                f"Failed to relocate output {src} to {dest}: {e}"
            ) from e

        return str(dest)

    def ingest(
        self,
        cwl_result: CWLRunResult,
        sidecar_path: str,
        cwl_inputs: dict[str, Any],
        rule_name: str,
        bindings: dict[str, Any],
        work_dir: str,
    ) -> dict[str, Entity]:
        """
        Parse CWL outputs, load sidecar, evaluate field expressions, POST to Hippo.

        Args:
            cwl_result: Result of the CWL execution.
            sidecar_path: Path to the .canon.yaml sidecar file.
            cwl_inputs: CWL inputs that were passed to the workflow.
            rule_name: Name of the Canon rule (for logging).
            bindings: Wildcard bindings for this invocation.
            work_dir: Working directory of the run.

        Returns:
            Dict of output_name → ingested Entity.
        """
        run_id = Path(work_dir).name  # use work_dir leaf as run ID

        sidecar = load_sidecar(sidecar_path)
        cwl_outputs = cwl_result.outputs

        ingested: dict[str, Entity] = {}

        for output_name, sidecar_output in sidecar.outputs.items():
            logger.info("Ingesting sidecar output '%s' as %s", output_name, sidecar_output.entity_type)

            try:
                hippo_fields = evaluate_hippo_fields(
                    sidecar_output,
                    cwl_outputs=cwl_outputs,
                    cwl_inputs=cwl_inputs,
                    run_id=run_id,
                )
            except Exception as e:
                raise CanonIngestionError(
                    f"Rule {rule_name}: failed to evaluate hippo_fields for "
                    f"output '{output_name}': {e}"
                ) from e

            # Relocate file outputs if present
            uri_field = hippo_fields.get("uri") or hippo_fields.get("location")
            if uri_field and isinstance(uri_field, str):
                try:
                    new_uri = self.relocate_output(uri_field, sidecar_output.entity_type, run_id)
                    if "uri" in hippo_fields:
                        hippo_fields["uri"] = new_uri
                    elif "location" in hippo_fields:
                        hippo_fields["location"] = new_uri
                except CanonIngestionError:
                    logger.warning("Could not relocate %s, using original", uri_field)

            try:
                entity = self._hippo.ingest_entity(sidecar_output.entity_type, hippo_fields)
                ingested[output_name] = entity
                # Also index by entity_type for planner lookup
                ingested[sidecar_output.entity_type] = entity
                logger.info(
                    "Ingested %s entity %s", sidecar_output.entity_type, entity.id
                )
            except Exception as e:
                raise CanonIngestionError(
                    f"Rule {rule_name}: failed to ingest output '{output_name}' "
                    f"as {sidecar_output.entity_type}: {e}"
                ) from e

        return ingested
