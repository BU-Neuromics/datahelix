"""CWLExecutorAdapter ABC and CWLRunResult dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CWLRunResult:
    """Result of a CWL workflow execution."""

    exit_code: int
    stdout: str
    stderr: str
    outputs: dict[str, Any] = field(default_factory=dict)


class CWLExecutorAdapter(ABC):
    """Abstract base class for CWL executor adapters."""

    requires_local_staging: bool = True
    requires_output_relocation: bool = True

    @abstractmethod
    def run(self, cwl_path: str, inputs: dict[str, Any], work_dir: str) -> CWLRunResult:
        """
        Execute a CWL workflow.

        Args:
            cwl_path: Path to the .cwl workflow file.
            inputs: CWL input parameters dict.
            work_dir: Working directory for the execution.

        Returns:
            CWLRunResult with exit code, output streams, and parsed outputs.
        """

    @abstractmethod
    def version(self) -> str:
        """Return the executor version string."""

    @abstractmethod
    def validate_available(self) -> None:
        """
        Check that the executor binary is available on PATH.

        Raises:
            CanonConfigError: if the binary is not found or unusable.
        """
