import sys
from pathlib import Path

# Make the in-repo `datahelix` package importable without requiring the
# metapackage to be pip-installed first (keeps `pytest tests/` fast and
# dependency-free, consistent with decision 1.10 - stdlib only).
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
