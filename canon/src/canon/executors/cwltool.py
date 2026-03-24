"""CwltoolAdapter: CWL executor using the cwltool reference implementation."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from canon.config import CanonConfig
from canon.exceptions import CanonConfigError
from canon.executors.base import CWLExecutorAdapter, CWLRunResult

logger = logging.getLogger(__name__)

_CWLTOOL_BINARY = "cwltool"


class CwltoolAdapter(CWLExecutorAdapter):
    """
    Runs CWL workflows via cwltool subprocess.

    Writes inputs.json to work_dir, invokes:
        cwltool [options] <cwl_path> inputs.json
    Parses stdout as JSON for output objects.
    """

    def __init__(self, config: CanonConfig) -> None:
        self._options: list[str] = list(config.cwltool_options)

    def validate_available(self) -> None:
        """Raise CanonConfigError if cwltool is not on PATH."""
        if shutil.which(_CWLTOOL_BINARY) is None:
            raise CanonConfigError(
                f"cwltool not found on PATH. Install it with: pip install cwltool"
            )

    def version(self) -> str:
        """Return cwltool version string."""
        try:
            result = subprocess.run(
                [_CWLTOOL_BINARY, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise CanonConfigError(f"Cannot get cwltool version: {e}") from e

    def run(self, cwl_path: str, inputs: dict[str, Any], work_dir: str) -> CWLRunResult:
        """
        Execute a CWL workflow with cwltool.

        Writes inputs to <work_dir>/inputs.json, runs cwltool, parses stdout as JSON.
        """
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)

        inputs_file = work / "inputs.json"
        inputs_file.write_text(json.dumps(inputs, indent=2))

        cmd = [_CWLTOOL_BINARY] + self._options + [cwl_path, str(inputs_file)]
        logger.info("Running: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as e:
            raise CanonConfigError(
                f"cwltool not found. Install it with: pip install cwltool"
            ) from e

        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr

        logger.debug("cwltool exit=%d stdout=%d bytes stderr=%d bytes",
                     exit_code, len(stdout), len(stderr))

        outputs: dict[str, Any] = {}
        if stdout.strip():
            try:
                outputs = json.loads(stdout)
                if not isinstance(outputs, dict):
                    outputs = {}
            except json.JSONDecodeError:
                logger.debug("cwltool stdout is not JSON; treating as plain output")
                outputs = {}

        return CWLRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            outputs=outputs,
        )
