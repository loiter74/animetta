"""Runtime diagnostics remain part of the canonical strict health contract."""

import pytest
from pydantic import ValidationError

from animetta.tools.gamebot.contracts.v2 import RuntimeHealth


def test_runtime_health_accepts_the_real_presentation_failure_counter() -> None:
    payload = {
        "ready": True,
        "busy": False,
        "runtime_instance_id": "mc-real",
        "last_completed_action_sequence": 2,
        "action_phase_publish_failures_total": 4,
    }
    assert RuntimeHealth.model_validate(payload).action_phase_publish_failures_total == 4
    payload.pop("action_phase_publish_failures_total")
    assert RuntimeHealth.model_validate(payload).action_phase_publish_failures_total == 0
    with pytest.raises(ValidationError):
        RuntimeHealth.model_validate({**payload, "action_phase_publish_failures_total": -1})
    with pytest.raises(ValidationError):
        RuntimeHealth.model_validate({**payload, "unknown_diagnostic": 0})
