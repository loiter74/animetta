"""Portable image identities, shared by packaging and the local lifecycle."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .fingerprint import is_safe_fingerprint_pattern
from .hashing import canonical_json_hash
from .models import DockerImageInputs
from .path_matching import matches_repository_path


def image_fingerprint(root: Path, inputs: DockerImageInputs) -> tuple[str, int]:
    """Hash actual COPY bytes, including untracked inputs, excluding runtime state."""
    root = root.resolve()
    paths: set[Path] = set()
    for pattern in inputs.paths:
        for candidate in root.glob(pattern + "/*" if pattern.endswith("/**") else pattern):
            if candidate.is_file() or candidate.is_symlink():
                paths.add(candidate)
    entries = []
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if not is_safe_fingerprint_pattern(relative):
            continue
        if any(matches_repository_path(relative, pattern) for pattern in inputs.exclude_paths):
            continue
        if path.is_symlink():
            # Docker cannot safely build a target outside this source tree.
            path.resolve().relative_to(root)
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        entries.append((relative, digest))
    return canonical_json_hash(
        {
            "schema": 2,
            "target": inputs.target,
            "platform": "linux/amd64",
            "inputs": inputs.model_dump(mode="json"),
            "files": entries,
        }
    ), len(entries)
