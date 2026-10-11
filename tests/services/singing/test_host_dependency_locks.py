"""Validate host dependency closure and identity without importing native engines."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PureWindowsPath

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[3]


def _lock_pins(path: Path) -> dict[str, str]:
    text = "\n".join(path.read_text(encoding="utf-8").splitlines()).replace("\\\n", " ")
    pins = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        requirement = Requirement(fields[0])
        assert requirement.url is None and requirement.marker is None and not requirement.extras
        specifiers = list(requirement.specifier)
        assert len(specifiers) == 1 and specifiers[0].operator == "=="
        name = canonicalize_name(requirement.name)
        assert name not in pins, f"Duplicate pin: {name}"
        hashes = fields[1:]
        assert hashes and all(re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", h) for h in hashes)
        assert len(hashes) == len(set(hashes))
        pins[name] = specifiers[0].version
    return pins


def _closure_errors(pins, packages, marker_environment) -> list[str]:
    extras = {p["name"]: set(p.get("selected_extras", [])) for p in packages}
    changed = True
    while changed:
        changed = False
        for package in packages:
            for text in package["requires_dist"]:
                req = Requirement(text)
                if req.marker and not any(
                    req.marker.evaluate({**marker_environment, "extra": extra})
                    for extra in [""] + sorted(extras[package["name"]])
                ):
                    continue
                name = canonicalize_name(req.name)
                if name in extras and not req.extras.issubset(extras[name]):
                    extras[name].update(req.extras)
                    changed = True
    errors = []
    for package in packages:
        python_spec = package.get("requires_python")
        if python_spec and not SpecifierSet(python_spec).contains(
            marker_environment["python_full_version"], prereleases=True
        ):
            errors.append(f"{package['name']}: Python {python_spec}")
        for text in package["requires_dist"]:
            req = Requirement(text)
            if req.marker and not any(
                req.marker.evaluate({**marker_environment, "extra": extra})
                for extra in [""] + sorted(extras[package["name"]])
            ):
                continue
            name = canonicalize_name(req.name)
            if name not in pins:
                errors.append(f"{package['name']}: missing {name}")
            elif not req.specifier.contains(pins[name], prereleases=True):
                errors.append(f"{package['name']}: incompatible {name} {pins[name]}")
    return errors


def _provenance(service: str):
    folder = ROOT / "services" / f"{service}-host"
    filename = "dependency-provenance.json" if service == "rvc" else "native-provenance.json"
    return folder, json.loads((folder / filename).read_bytes())


@pytest.mark.parametrize("service,count", [("rvc", 72), ("qwen", 35)])
def test_host_locks_have_hashed_exact_pins_and_complete_native_windows_closure(service, count):
    folder, proof = _provenance(service)
    lock = folder / "requirements.lock"
    assert hashlib.sha256(lock.read_bytes()).hexdigest() == proof["lock"]["sha256"]
    pins = _lock_pins(lock)
    assert len(pins) == count == proof["lock"]["package_count"]
    assert pins == {p["name"]: p["version"] for p in proof["packages"]}
    target = proof["target"]["marker_environment"]
    assert target["python_version"] == "3.13"
    assert target["platform_system"] == "Windows"
    assert target["platform_machine"] == "AMD64"
    assert _closure_errors(pins, proof["packages"], target) == []
    assert proof["isolated_installation"]["status"] == "passed"
    assert proof["isolated_installation"]["isolation_verified"] is True
    assert proof["effective_isolation"]["site_enabled"] is False
    assert proof["effective_isolation"]["model_modules_loaded"] == []
    stages = proof["isolated_installation"]["stages"]
    assert {s["stage"] for s in stages} >= {"dry-run", "sync", "pip-check", "metadata"}
    assert all(s["exit_code"] == 0 for s in stages)
    sync = next(s for s in stages if s["stage"] == "sync")
    assert "--require-hashes" in sync["argv"]
    assert "--strict" in sync["argv"]


@pytest.mark.parametrize("mutation", ["missing_transitive", "incompatible_numpy"])
def test_host_closure_validation_detects_real_dependency_breakage(mutation):
    folder, proof = _provenance("rvc")
    pins = _lock_pins(folder / "requirements.lock")
    if mutation == "missing_transitive":
        pins.pop("safetensors")
        expected = "transformers: missing safetensors"
    else:
        pins["numpy"] = "3.0.0"
        expected = "numba: incompatible numpy 3.0.0"
    assert expected in _closure_errors(
        pins, proof["packages"], proof["target"]["marker_environment"]
    )


def test_rvc_uses_one_permanent_isolated_interpreter_and_preserves_voice_assets():
    _folder, proof = _provenance("rvc")
    contract = yaml.safe_load((ROOT / "config/host-rvc.yaml").read_text(encoding="utf-8"))
    expected = PureWindowsPath(contract["runtime"]["root"]) / ".venv-animetta/Scripts/python.exe"
    assert PureWindowsPath(contract["runtime"]["python"]) == expected
    assert PureWindowsPath(contract["separation"]["python"]) == expected
    assert proof["isolated_installation"]["permanent"] is True
    assert proof["contract_before"]["identity"] == contract["identity"]
    for field in [
        "model_sha256",
        "index_path",
        "index_sha256",
        "hubert_model_dir",
        "hubert_sha256",
        "hubert_repo",
        "hubert_revision",
        "rmvpe_sha256",
        "device",
        "is_half",
    ]:
        assert proof["contract_before"]["runtime"][field] == contract["runtime"][field]
    assert proof["contract_before"]["separation"]["model"] == contract["separation"]["model"]
    assert proof["contract_before"]["runtime"]["python"] != contract["runtime"]["python"]
    assert proof["contract_before"]["separation"]["python"] != contract["separation"]["python"]
    pins = _lock_pins(ROOT / "services/rvc-host/requirements.lock")
    assert {"funasr", "kokoro", "zhipuai", "fairseq", "gradio"}.isdisjoint(pins)
    assert pins["torch"] == pins["torchaudio"] == "2.11.0+cu128"


def test_qwen_native_archive_and_voice_identity_remain_pinned():
    _folder, proof = _provenance("qwen")
    native = proof["native_runtime"]
    contract = yaml.safe_load((ROOT / "config/host-tts.yaml").read_text(encoding="utf-8"))
    assert native["actual_git_commit"] == native["expected_contract_commit"]
    assert native["actual_git_commit"] == contract["identity"]["runtime_commit"]
    assert native["live_identity"]["voice"] == contract["identity"]["voice"]
    dlls = native["native_dll_sha256"]
    assert len(dlls) == 30
    assert all(row["matches_existing_archive"] for row in dlls)
    assert all(row["sha256"] == row["existing_archive_entry_sha256"] for row in dlls)
    assert all(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in dlls)
    assert proof["current_host"] == {
        "reinstalled": False,
        "restarted": False,
        "voice_changed": False,
        "model_files_changed": False,
    }
