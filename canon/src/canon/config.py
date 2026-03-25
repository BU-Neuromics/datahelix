"""CanonConfig: load and validate canon.yaml."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

from canon.exceptions import CanonConfigError

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with environment variable values."""

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        val = os.environ.get(var_name)
        if val is None:
            raise CanonConfigError(
                f"canon.yaml: environment variable {var_name} is not set"
            )
        return val

    return _ENV_VAR_RE.sub(_replace, value)


def _substitute_in_obj(obj: Any) -> Any:
    """Recursively substitute env vars in strings within a nested structure."""
    if isinstance(obj, str):
        return _substitute_env_vars(obj)
    if isinstance(obj, dict):
        return {k: _substitute_in_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_in_obj(item) for item in obj]
    return obj


class OutputStorageConfig(BaseModel):
    """Configuration for output file storage.

    ``type`` must match a registered ``canon.storage_adapters`` entry point name.
    Extra fields are passed through to the adapter constructor.
    """

    model_config = {"extra": "allow"}

    type: str
    base_path: str | None = None  # used by local adapter

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v:
            raise ValueError("canon.yaml: output_storage.type is required")
        return v

    @model_validator(mode="after")
    def validate_storage_fields(self) -> "OutputStorageConfig":
        if self.type == "local" and not self.base_path:
            raise ValueError(
                "canon.yaml: output_storage.base_path is required for type: local"
            )
        return self


class CanonConfig(BaseModel):
    """Canon configuration loaded from canon.yaml."""

    hippo_url: str
    hippo_token: str
    executor: str
    rules_file: str = "canon_rules.yaml"
    work_dir: str = ".canon/work"
    output_storage: OutputStorageConfig
    cwltool_options: list[str] = []
    log_level: str = "INFO"

    # Internal: config file directory (not in yaml, set after load)
    _config_dir: Path | None = None

    @field_validator("hippo_url")
    @classmethod
    def validate_hippo_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("canon.yaml: hippo_url must be an http or https URI")
        return v.rstrip("/")

    @field_validator("hippo_token")
    @classmethod
    def validate_hippo_token(cls, v: str) -> str:
        if not v:
            raise ValueError("canon.yaml: hippo_token is required")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        v = v.upper()
        valid = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if v not in valid:
            raise ValueError(
                f"canon.yaml: log_level must be one of: DEBUG, INFO, WARNING, ERROR"
            )
        return v

    @field_validator("cwltool_options", mode="before")
    @classmethod
    def validate_cwltool_options(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("canon.yaml: cwltool_options must be a list of strings")
        return v

    def resolve_rules_file(self, config_dir: Path) -> Path:
        """Resolve rules_file path relative to config directory."""
        p = Path(self.rules_file)
        if p.is_absolute():
            return p
        return config_dir / p

    def resolve_work_dir(self, config_dir: Path) -> Path:
        """Resolve work_dir path relative to config directory."""
        p = Path(self.work_dir)
        if p.is_absolute():
            return p
        return config_dir / p

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> "CanonConfig":
        """
        Load CanonConfig from a canon.yaml file.

        Args:
            config_path: Path to canon.yaml. Defaults to canon.yaml in cwd.

        Returns:
            Validated CanonConfig instance.

        Raises:
            CanonConfigError: if the file is missing, unparseable, or invalid.
        """
        if config_path is None:
            config_path = Path.cwd() / "canon.yaml"
        config_path = Path(config_path)

        if not config_path.exists():
            raise CanonConfigError(
                f"canon.yaml not found at {config_path}. "
                f"Create a canon.yaml in your project directory."
            )

        try:
            raw = yaml.safe_load(config_path.read_text())
        except yaml.YAMLError as e:
            raise CanonConfigError(f"canon.yaml: YAML parse error: {e}") from e

        if not isinstance(raw, dict):
            raise CanonConfigError("canon.yaml: must be a YAML mapping")

        # Validate required fields before env var substitution to give better errors
        for required in ("hippo_url", "hippo_token", "executor", "output_storage"):
            if required not in raw:
                raise CanonConfigError(f"canon.yaml: {required} is required")

        # Substitute env vars throughout
        try:
            raw = _substitute_in_obj(raw)
        except CanonConfigError:
            raise

        try:
            config = cls.model_validate(raw)
        except Exception as e:
            # Extract useful message from pydantic validation errors
            raise CanonConfigError(str(e)) from e

        config._config_dir = config_path.parent
        return config
