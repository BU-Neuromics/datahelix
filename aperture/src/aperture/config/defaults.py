"""Default configuration values for Aperture."""

from __future__ import annotations

from pathlib import Path

DEFAULT_CONFIG: dict = {
    "hippo": {
        "mode": "sdk",
        "config": "./hippo.yaml",
        "url": "http://localhost:8000",
    },
    "output": {
        "format": "table",
        "pager": "auto",
        "color": "auto",
    },
    "logging": {
        "level": "WARNING",
    },
}

USER_CONFIG_DIR = Path.home() / ".bass"
USER_CONFIG_FILE = USER_CONFIG_DIR / "aperture.yaml"
PROJECT_CONFIG_FILE = Path(".bass") / "aperture.yaml"
