"""The dependency contract rejects drift without modifying input files."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from scripts.check_python_lock import export_requirements


@pytest.fixture
def project(tmp_path):
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text(
        '[project]\nname="lock-contract"\nversion="0.0.0"\nrequires-python=">=3.13"\n'
        "[dependency-groups]\ndev=[]\n",
        encoding="utf-8",
    )
    subprocess.run([shutil.which("uv"), "lock", "--offline"], cwd=tmp_path, check=True)
    export_requirements(tmp_path, write=True)
    return tmp_path


def test_exports_match_and_manual_changes_are_rejected(project):
    export_requirements(project)
    requirements = project / "requirements.txt"
    requirements.write_text("unexpected-package==1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="requirements.txt differs"):
        export_requirements(project)
    assert requirements.read_text(encoding="utf-8") == "unexpected-package==1\n"


def test_stale_lock_is_rejected_without_rewriting_it(project):
    lock = project / "uv.lock"
    before = lock.read_bytes()
    manifest = project / "pyproject.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace('version="0.0.0"', 'version="0.0.1"'),
        encoding="utf-8",
    )
    with pytest.raises(subprocess.CalledProcessError):
        export_requirements(project)
    assert lock.read_bytes() == before
