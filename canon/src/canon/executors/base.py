"""Abstract base for Canon workflow executor adapters.

Entry point group: canon.executor_adapters
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

from canon.config import CanonConfig
from canon.plan import CanonTask


class RunStatus(str, Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'


@dataclasses.dataclass
class RunHandle:
    """Opaque reference to a submitted workflow run."""

    run_id: str
    executor_type: str
    meta: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ExecutorInputs:
    """Resolved inputs ready to hand off to a workflow executor."""

    workflow_path: str
    inputs: dict[str, str]


class WorkflowExecutorAdapter(ABC):
    """Abstract adapter that bridges Canon tasks to a concrete workflow engine.

    Entry point group: canon.executor_adapters
    """

    def __init__(self, config: CanonConfig) -> None:
        self.config = config

    @abstractmethod
    def render(self, task: CanonTask) -> ExecutorInputs:
        """Translate a CanonTask into concrete executor inputs."""

    @abstractmethod
    def submit(self, inputs: ExecutorInputs) -> RunHandle:
        """Submit a workflow for execution; return an opaque run handle."""

    @abstractmethod
    def poll(self, handle: RunHandle) -> RunStatus:
        """Check the current status of a submitted run."""

    @abstractmethod
    def collect_outputs(self, handle: RunHandle) -> Path:
        """Retrieve output artefacts once the run has SUCCEEDED."""
