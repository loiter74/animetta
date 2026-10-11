"""Optional capabilities must not become core configuration prerequisites."""

from copy import deepcopy

import pytest

from animetta.config.manifest import (
    RuntimeConfigError,
    load_build_capabilities,
    load_effective_config,
    load_host_service_requirements,
)
from animetta.config.runtime_reloader import classify_effective_config_diff


@pytest.mark.parametrize(
    ("capability", "earth", "media"),
    [
        (None, "false", "false"),
        ("earth", "true", "true"),
        ("singing", "false", "true"),
        ("voice_input", "false", "true"),
        ("minecraft", "false", "false"),
    ],
)
def test_image_capabilities_follow_the_profile_without_resolving_secrets(
    manifest_data, write_manifest, manifest_secrets, capability, earth, media
):
    data = deepcopy(manifest_data)
    data["profiles"]["production"]["runtime"]["capabilities"] = (
        {capability: True} if capability else {}
    )
    manifest_secrets.delenv("MIMO_API_KEY")
    assert load_build_capabilities(write_manifest(data), profile="production") == {
        "ANIMETTA_EARTH_ENABLED": earth,
        "ANIMETTA_MEDIA_ENABLED": media,
    }


def test_memory_retrieval_mode_is_explicit_and_requires_restart(
    manifest_data, write_manifest, manifest_secrets
):
    current = load_effective_config(write_manifest(manifest_data), profile="production")
    assert current.system.memory_retrieval_mode == "fts"
    data = deepcopy(manifest_data)
    data["profiles"]["production"]["runtime"]["memory_retrieval_mode"] = "semantic"
    candidate = load_effective_config(write_manifest(data), profile="production")
    assert candidate.semantic_hash != current.semantic_hash
    refreshed, restart = classify_effective_config_diff(current, candidate)
    assert "runtime.memory_retrieval_mode" in restart
    assert "ui" not in refreshed


def test_disabled_voice_input_needs_no_secret_and_does_not_change_hash(
    manifest_data, write_manifest, manifest_secrets
):
    data = deepcopy(manifest_data)
    data["profiles"]["production"]["runtime"]["capabilities"] = {}
    manifest_secrets.delenv("MIMO_API_KEY")
    current = load_effective_config(write_manifest(data), profile="production")
    assert set(current.providers) == {"llm", "tts"}
    assert current.to_public_dict()["capabilities"]["voice_input"] is False
    data["profiles"]["production"]["services"]["asr"] = "unused-provider"
    data["providers"]["vad"]["mimo-vad"]["model"] = "unused-model"
    changed = load_effective_config(write_manifest(data), profile="production")
    assert current.effective_hash == changed.effective_hash


def test_selected_voice_input_still_requires_its_real_provider_secret(
    manifest_data, write_manifest, manifest_secrets
):
    manifest_secrets.delenv("MIMO_API_KEY")
    with pytest.raises(RuntimeConfigError, match="MIMO_API_KEY"):
        load_effective_config(write_manifest(manifest_data), profile="production")


def test_core_tts_failure_is_not_hidden_by_disabled_capabilities(
    manifest_data, write_manifest, manifest_secrets
):
    data = deepcopy(manifest_data)
    data["profiles"]["production"]["runtime"]["capabilities"] = {}
    manifest_secrets.delenv("QWEN_TTS_API_KEY")
    with pytest.raises(RuntimeConfigError, match="QWEN_TTS_API_KEY"):
        load_effective_config(write_manifest(data), profile="production")


def test_host_workers_follow_selected_tts_and_singing_without_api_secrets(
    manifest_data, write_manifest, isolated_manifest_env
):
    data = deepcopy(manifest_data)
    path = write_manifest(data)
    assert load_host_service_requirements(path, profile="production") == ("tts",)
    assert load_host_service_requirements(path, profile="test") == ()
    data["profiles"]["production"]["runtime"]["capabilities"]["singing"] = True
    assert load_host_service_requirements(write_manifest(data), profile="production") == (
        "tts",
        "rvc",
    )
