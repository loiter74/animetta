from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest

from tooling.quality.architecture_boundaries import (
    audit_frontend_source,
    audit_python_source,
    audit_repository,
)


def _codes(violations: object) -> set[str]:
    return {item.code for item in violations}  # type: ignore[attr-defined]


def test_backend_domain_must_not_import_composition_or_orchestration() -> None:
    violations = audit_python_source(
        PurePosixPath("src/animetta/services/dialogue/service.py"),
        "from animetta.core.readiness import Status\n"
        "from animetta.orchestration.graph.state import AgentState\n",
    )

    assert _codes(violations) == {"BACKEND_FORBIDDEN_IMPORT"}


def test_backend_composition_root_may_import_application_and_domains() -> None:
    violations = audit_python_source(
        PurePosixPath("src/animetta/core/application.py"),
        "from animetta.orchestration.server.app import create_app\n"
        "from animetta.services.llm import LLMInterface\n",
    )

    assert violations == ()


def test_declared_one_release_compatibility_facade_is_terminal() -> None:
    violations = audit_python_source(
        PurePosixPath("src/animetta/config/runtime_reload.py"),
        "from animetta.services.runtime_config import RuntimePrompt\n",
    )

    assert violations == ()


def test_frontend_rejects_legacy_cycles_and_live_dashboard_dependencies() -> None:
    store = audit_frontend_source(
        PurePosixPath("frontend/src/stores/chat.ts"),
        "import { useSocket } from '@/composables/useSocket'\n",
    )
    contract = audit_frontend_source(
        PurePosixPath("frontend/src/types/socket-events.ts"),
        "export type { Plan } from '@/components/live2d/contract'\n",
    )
    live = audit_frontend_source(
        PurePosixPath("frontend/src/live/audio.ts"),
        "import { play } from '@/components/live2d/useAudioPlayback'\n",
    )

    assert _codes(store + contract + live) == {
        "FRONTEND_LIVE_DASHBOARD_IMPORT",
        "FRONTEND_STORE_COMPOSABLE_IMPORT",
        "FRONTEND_TYPE_UI_IMPORT",
    }


def test_frontend_shared_may_not_import_features() -> None:
    violations = audit_frontend_source(
        PurePosixPath("frontend/src/shared/transport/socket.ts"),
        "import { useChat } from '@/features/conversation'\n",
    )

    assert _codes(violations) == {"FRONTEND_SHARED_UPWARD_IMPORT"}


def test_repository_audit_reports_cross_package_cycles(tmp_path: Path) -> None:
    services = tmp_path / "src" / "animetta" / "services"
    core = tmp_path / "src" / "animetta" / "core"
    services.mkdir(parents=True)
    core.mkdir(parents=True)
    (services / "feature.py").write_text(
        "from animetta.core.application import app\n", encoding="utf-8"
    )
    (core / "application.py").write_text(
        "from animetta.services.feature import feature\n", encoding="utf-8"
    )
    (tmp_path / "frontend" / "src").mkdir(parents=True)

    violations = audit_repository(tmp_path)

    assert {item.code for item in violations} == {
        "BACKEND_DEPENDENCY_CYCLE",
        "BACKEND_FORBIDDEN_IMPORT",
    }


def test_report_cli_runs_from_repository_root() -> None:
    root = Path(__file__).resolve().parents[3]

    completed = subprocess.run(
        [sys.executable, "scripts/check_architecture_boundaries.py", "--report"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("Architecture boundary audit:")


@pytest.mark.parametrize("requested", ["cesium", "@cesium/engine", "socket.io-client", "pixi.js"])
def test_earth_sdk_imports_require_adapter(requested: str) -> None:
    source = f"import SDK from '{requested}'\n"
    assert _codes(
        audit_frontend_source(
            PurePosixPath("frontend/src/features/earth/EarthWorkspace.vue"),
            source,
        )
    ) == {"EARTH_SDK_OUTSIDE_ADAPTER"}
    assert (
        audit_frontend_source(
            PurePosixPath("frontend/src/features/earth/adapters/vendor.ts"),
            source,
        )
        == ()
    )


@pytest.mark.parametrize(
    "requested",
    [
        "vue",
        "@vue/runtime-core",
        "pinia",
        "socket.io-client",
        "cesium",
        "@cesium/engine",
        "./adapters/cesium",
        "./EarthWorkspace.vue",
        "./mount",
        "@/shared/transport/liveSocket",
    ],
)
def test_earth_controller_has_no_framework_or_execution_dependencies(requested: str) -> None:
    assert _codes(
        audit_frontend_source(
            PurePosixPath("frontend/src/features/earth/controller.ts"),
            f"const module = import(\n '{requested}'\n)\n",
        )
    ) == {"EARTH_CORE_OUTWARD_IMPORT"}


def test_earth_core_contract_import_and_shared_rendering_sdk_are_allowed() -> None:
    assert (
        audit_frontend_source(
            PurePosixPath("frontend/src/features/earth/controller.ts"),
            "import type { EarthMap } from './contracts'\n",
        )
        == ()
    )
    assert (
        audit_frontend_source(
            PurePosixPath("frontend/src/shared/live2d/renderer.ts"),
            "import * as PIXI from 'pixi.js'\n",
        )
        == ()
    )


@pytest.mark.parametrize(
    "requested", ["@/review/live2d-stage", "../../review/live2d-stage", "@/features/earth"]
)
def test_shared_renderer_rejects_upward_imports(requested: str) -> None:
    assert _codes(
        audit_frontend_source(
            PurePosixPath("frontend/src/shared/live2d/renderer.ts"),
            f"export {{ renderer }} from '{requested}'\n",
        )
    ) == {"FRONTEND_SHARED_UPWARD_IMPORT"}


@pytest.mark.parametrize(
    "requested", ["../conversation/internal", "@/features/conversation/internal"]
)
def test_earth_cannot_import_other_feature_internals(requested: str) -> None:
    assert _codes(
        audit_frontend_source(
            PurePosixPath("frontend/src/features/earth/controller.ts"),
            f"import {{ value }} from '{requested}'\n",
        )
    ) == {"EARTH_CORE_OUTWARD_IMPORT", "FRONTEND_CROSS_FEATURE_DEEP_IMPORT"}


@pytest.mark.parametrize(
    "source",
    [
        "from animetta.orchestration.graph import state",
        "from animetta import tools",
        "from . import photon",
        "from .providers import imagery",
        "from ..llm import factory",
        "import httpx",
        "from openai import OpenAI",
        "from langgraph.graph import StateGraph",
    ],
)
def test_earth_domain_rejects_outer_services_including_relative_imports(source: str) -> None:
    assert "EARTH_DOMAIN_OUTWARD_IMPORT" in _codes(
        audit_python_source(
            PurePosixPath("src/animetta/services/earth/domain.py"),
            source,
        )
    )


def test_earth_domain_allows_values_and_contracts() -> None:
    assert (
        audit_python_source(
            PurePosixPath("src/animetta/services/earth/domain.py"),
            "from dataclasses import dataclass\nfrom .contracts import GeoPoint\n",
        )
        == ()
    )


def test_earth_audit_detects_internal_cycles_with_existing_detector(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend/src/features/earth"
    backend = tmp_path / "src/animetta/services/earth"
    frontend.mkdir(parents=True)
    backend.mkdir(parents=True)
    (frontend / "controller.ts").write_text("import { b } from './contracts'", encoding="utf-8")
    (frontend / "contracts.ts").write_text("export { a } from './controller'", encoding="utf-8")
    (backend / "domain.py").write_text("from .contracts import Point", encoding="utf-8")
    (backend / "contracts.py").write_text("from .domain import State", encoding="utf-8")
    violations = audit_repository(tmp_path)
    assert len(violations) == 2
    assert _codes(violations) == {"EARTH_DEPENDENCY_CYCLE"}
