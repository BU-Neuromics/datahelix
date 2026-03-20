"""Local subprocess executor adapter for Canon."""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from pathlib import Path

from canon.config import CanonConfig
from canon.exceptions import CanonExecutorError
from canon.executors.base import ExecutorInputs, RunHandle, RunStatus, WorkflowExecutorAdapter
from canon.plan import CanonTask
from canon.rule_registry import RulesEngine


def _resolve_inputs(template_dict: dict[str, str], substitutions: dict[str, str]) -> dict[str, str]:
    """Replace {key} placeholders in all values using *substitutions*."""
    resolved = {}
    for env_key, value in template_dict.items():
        def _sub(m: re.Match) -> str:
            return substitutions.get(m.group(1), m.group(0))
        resolved[env_key] = re.sub(r'\{(\w+)\}', _sub, value)
    return resolved


class LocalProcessExecutor(WorkflowExecutorAdapter):
    """Runs workflow scripts as local subprocesses."""

    def __init__(self, config: CanonConfig, rules_engine: RulesEngine | None = None) -> None:
        super().__init__(config)
        self._rules_engine = rules_engine
        self._runs: dict[str, dict] = {}

    def _get_rule(self, rule_name: str):
        if self._rules_engine is None:
            raise CanonExecutorError("LocalProcessExecutor requires a RulesEngine")
        for rule in self._rules_engine.rules:
            if rule.name == rule_name:
                return rule
        raise CanonExecutorError(f"Rule not found: {rule_name!r}")

    def render(self, task: CanonTask) -> ExecutorInputs:
        rule = self._get_rule(task.rule_name)
        rules_dir = Path(self.config.rules_file).parent
        workflow_path = str(rules_dir / (rule.execute.workflow + '.sh'))

        substitutions = dict(task.wildcard_bindings.as_dict())
        for bind_name, entity in task.input_entities.items():
            if 'uri' in entity:
                substitutions[bind_name] = entity['uri']

        resolved = _resolve_inputs(rule.execute.inputs, substitutions)
        return ExecutorInputs(workflow_path=workflow_path, inputs=resolved)

    def submit(self, inputs: ExecutorInputs) -> RunHandle:
        run_id = str(uuid.uuid4())
        work_dir = Path(self.config.work_dir) / run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(inputs.inputs)
        env['CANON_WORK_DIR'] = str(work_dir)

        proc = subprocess.Popen(
            ['/bin/bash', inputs.workflow_path],
            env=env,
        )
        self._runs[run_id] = {'proc': proc, 'work_dir': work_dir}
        return RunHandle(run_id=run_id, executor_type='local')

    def poll(self, handle: RunHandle) -> RunStatus:
        entry = self._runs.get(handle.run_id)
        if entry is None:
            raise CanonExecutorError(f"Unknown run_id: {handle.run_id}")
        ret = entry['proc'].poll()
        if ret is None:
            return RunStatus.RUNNING
        if ret == 0:
            return RunStatus.SUCCEEDED
        return RunStatus.FAILED

    def collect_outputs(self, handle: RunHandle) -> Path:
        entry = self._runs.get(handle.run_id)
        if entry is None:
            raise CanonExecutorError(f"Unknown run_id: {handle.run_id}")
        outputs_path = entry['work_dir'] / '.canon_outputs.json'
        if not outputs_path.exists():
            raise CanonExecutorError(
                f"Outputs file not found: {outputs_path}"
            )
        return outputs_path
