import importlib.metadata
import json
import sys

from scripts import runtime_lifecycle
from scripts import qwen_preflight
from tooling.execution_feedback import IterationPlanStore, ResourceOwnership, lifecycle

assert qwen_preflight and lifecycle and IterationPlanStore and ResourceOwnership

assert runtime_lifecycle._host_requirements("production") == ("tts",)
environment = runtime_lifecycle._compose_environment(profile="production")
assert environment["ANIMETTA_EARTH_ENABLED"] == "false"
assert environment["ANIMETTA_MEDIA_ENABLED"] == "false"
forbidden = {"torch", "transformers", "chromadb", "langgraph", "openai"} & sys.modules.keys()
assert not forbidden, forbidden
packages = {p.metadata["Name"]: p.version for p in importlib.metadata.distributions()}
print(json.dumps({"status": "passed", "python": sys.version, "packages": packages,
    "package_count": len(packages), "host_requirements": ["tts"],
    "optional_build_flags": {n: environment[n] for n in ("ANIMETTA_EARTH_ENABLED", "ANIMETTA_MEDIA_ENABLED")},
    "forbidden_modules": sorted(forbidden), "service_actions_performed": False}))
