#!/usr/bin/env python3
"""scripts/check_deps.py — CI 中运行，检测违规跨层导入"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

LAYERS: dict[int, set[str]] = {
    0: {"utils", "config", "tracing", "persistence"},
    1: {"memory", "avatar", "tools", "notifier", "services"},
    2: {"orchestration.graph"},
    3: {"orchestration.server", "core"},
}


def get_layer(module: str) -> int:
    for layer_num, modules in LAYERS.items():
        for m in modules:
            if module.startswith(m):
                return layer_num
    return -1


def check_file(filepath: Path) -> list[str]:
    violations: list[str] = []
    try:
        rel = filepath.relative_to(Path("src/anima"))
    except ValueError:
        return violations

    current_module = str(rel.parent).replace("/", ".").replace("\\", ".")
    current_layer = get_layer(current_module)

    if current_layer == -1:
        return violations

    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("anima."):
                    target = node.module.removeprefix("anima.")
                    target_layer = get_layer(target)
                    if target_layer > current_layer:
                        violations.append(
                            f"{filepath}:{node.lineno} "
                            f"Layer {current_layer} ({current_module}) "
                            f"imports Layer {target_layer} ({target})"
                        )
    return violations


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    anima_src = project_root / "src" / "anima"
    
    if not anima_src.exists():
        print(f"ERROR: src/anima not found at {anima_src}")
        sys.exit(2)

    all_violations: list[str] = []
    for py_file in anima_src.rglob("*.py"):
        all_violations.extend(check_file(py_file))

    if all_violations:
        print(f"Found {len(all_violations)} layer violations:")
        for v in all_violations:
            print(f"  ! {v}")
        sys.exit(1)
    else:
        print("No layer violations found")
