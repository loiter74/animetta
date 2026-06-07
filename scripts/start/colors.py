"""Backward-compat shim — re-exports from animetta.utils.terminal."""

import sys
from pathlib import Path

# Ensure src/ is importable when this module is loaded directly from scripts/
_project_root = Path(__file__).resolve().parent.parent.parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from animetta.utils.terminal import Colors, error, info, success, warn  # noqa: E402, F401
