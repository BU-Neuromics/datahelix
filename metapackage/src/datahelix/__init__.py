"""DataHelix platform metapackage.

This package is intentionally thin: it owns the platform's version-compatibility
matrix and a small umbrella CLI (``datahelix info`` / ``datahelix doctor``). No
entity, storage, or transform logic lives here — see platform ADR-0002.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("datahelix")
except PackageNotFoundError:  # pragma: no cover - not installed as a distribution
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
