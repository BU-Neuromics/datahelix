"""Canon runtime configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, model_validator

from canon.exceptions import CanonValidationError


class CanonConfig(BaseModel):
    """Runtime configuration for the Canon orchestrator."""

    hippo_url: str
    hippo_token: str = ''
    executor: Literal['local', 'container']
    rules_file: str = 'canon_rules.yaml'
    work_dir: str = '.canon/work'
    executor_settings: Optional[dict] = {}

    @model_validator(mode='before')
    @classmethod
    def _check_required(cls, values: dict) -> dict:
        missing = [f for f in ('hippo_url', 'executor') if not values.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return values

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'CanonConfig':
        """Load config from a YAML file.

        Raises CanonValidationError on missing required fields or invalid executor.
        """
        p = Path(path)
        if not p.exists():
            raise CanonValidationError(f"Config file not found: {path}")
        try:
            raw = yaml.safe_load(p.read_text())
        except yaml.YAMLError as exc:
            raise CanonValidationError(f"Invalid YAML in config file {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise CanonValidationError(f"Config file {path} must contain a YAML mapping")
        try:
            return cls.model_validate(raw)
        except Exception as exc:
            raise CanonValidationError(str(exc)) from exc
