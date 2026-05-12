"""Tests for ProviderRegistry (config/core/registry.py)"""

import sys
from pathlib import Path
from typing import Literal, Optional, Type
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field

# Ensure src/ is on the Python path
_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from anima.config.core.base import ProviderConfig
from anima.config.core.registry import ProviderRegistry


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def registry():
    """Fixture providing a clean ProviderRegistry state for each test.

    Saves and restores the original class-level dicts so tests never leak state.
    """
    saved = {
        "_configs": ProviderRegistry._configs,
        "_services": ProviderRegistry._services,
        "_providers": ProviderRegistry._providers,
    }
    ProviderRegistry._configs = {"llm": {}, "asr": {}, "tts": {}, "vad": {}}
    ProviderRegistry._services = {"llm": {}, "asr": {}, "tts": {}, "vad": {}}
    ProviderRegistry._providers = ProviderRegistry._configs
    yield ProviderRegistry
    ProviderRegistry._configs = saved["_configs"]
    ProviderRegistry._services = saved["_services"]
    ProviderRegistry._providers = saved["_providers"]


# ═══════════════════════════════════════════════════════════════
# Mock classes for testing
# ═══════════════════════════════════════════════════════════════

class MockOpenAIConfig(ProviderConfig):
    """Mock OpenAI LLM config for testing"""
    type: Literal["openai"] = "openai"
    api_key: str = "test_key"


class MockGLMConfig(ProviderConfig):
    """Mock GLM config for testing"""
    type: Literal["glm"] = "glm"
    api_key: str = "test_key"


class MockWhisperConfig(ProviderConfig):
    """Mock Whisper ASR config for testing"""
    type: Literal["whisper"] = "whisper"
    model: str = "base"


class MockServiceWithFromConfig:
    """Mock service class that has from_config classmethod"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @classmethod
    def from_config(cls, config: ProviderConfig, **extra_kwargs) -> "MockServiceWithFromConfig":
        return cls(config=config, **extra_kwargs)


class MockServiceNoFromConfig:
    """Mock service class that is MISSING from_config"""
    pass


# ═══════════════════════════════════════════════════════════════
# Test cases
# ═══════════════════════════════════════════════════════════════

class TestRegisterConfig:
    """Tests for ProviderRegistry.register_config"""

    def test_register_config_stores_with_category_and_type(self, registry):
        """register_config decorator stores class in _configs dict with correct category/type"""
        @registry.register_config("llm", "openai")
        class TestConfig(ProviderConfig):
            type: Literal["test"] = "test"

        assert "openai" in registry._configs["llm"]
        assert registry._configs["llm"]["openai"] is TestConfig

    def test_register_config_multiple_categories(self, registry):
        """register_config works across different categories"""
        @registry.register_config("llm", "openai")
        class LLMConfig(ProviderConfig):
            type: Literal["openai"] = "openai"

        @registry.register_config("asr", "whisper")
        class ASRConfig(ProviderConfig):
            type: Literal["whisper"] = "whisper"

        assert registry._configs["llm"]["openai"] is LLMConfig
        assert registry._configs["asr"]["whisper"] is ASRConfig
        # Verify isolation across categories
        assert "whisper" not in registry._configs["llm"]

    def test_register_config_returns_the_class(self, registry):
        """register_config decorator returns the same class (does not wrap it)"""
        class MyConfig(ProviderConfig):
            type: Literal["my"] = "my"

        result = registry.register_config("llm", "my")(MyConfig)
        assert result is MyConfig


class TestRegisterAlias:
    """Tests for ProviderRegistry.register (backward compat alias)"""

    def test_register_is_alias_for_register_config(self, registry):
        """register() should behave identically to register_config()"""
        @registry.register("llm", "test_model")
        class TestConfig(ProviderConfig):
            type: Literal["test_model"] = "test_model"

        assert registry._configs["llm"]["test_model"] is TestConfig

    def test_register_and_register_config_same_dict(self, registry):
        """register and register_config write to the same dict"""
        @registry.register("llm", "from_register")
        class A(ProviderConfig):
            type: Literal["a"] = "a"

        @registry.register_config("llm", "from_config")
        class B(ProviderConfig):
            type: Literal["b"] = "b"

        assert "from_register" in registry._configs["llm"]
        assert "from_config" in registry._configs["llm"]


class TestRegisterService:
    """Tests for ProviderRegistry.register_service"""

    def test_register_service_stores_class(self, registry):
        """register_service stores class in _services dict"""
        @registry.register_service("llm", "openai")
        class OpenAIService:
            pass

        assert "openai" in registry._services["llm"]
        assert registry._services["llm"]["openai"] is OpenAIService

    def test_register_service_multiple_categories(self, registry):
        """register_service works across different categories"""
        @registry.register_service("llm", "openai")
        class LLMService:
            pass

        @registry.register_service("tts", "edge")
        class TTSService:
            pass

        assert registry._services["llm"]["openai"] is LLMService
        assert registry._services["tts"]["edge"] is TTSService

    def test_register_service_returns_the_class(self, registry):
        """register_service decorator returns the same class"""
        class MyService:
            pass

        result = registry.register_service("llm", "my")(MyService)
        assert result is MyService


class TestGetServiceClass:
    """Tests for ProviderRegistry.get_service_class"""

    def test_returns_correct_class(self, registry):
        """get_service_class returns the registered service class"""
        @registry.register_service("llm", "openai")
        class OpenAIService:
            pass

        result = registry.get_service_class("llm", "openai")
        assert result is OpenAIService

    def test_returns_none_for_unknown_category(self, registry):
        """get_service_class returns None for non-existent category"""
        result = registry.get_service_class("nonexistent", "anything")
        assert result is None

    def test_returns_none_for_unknown_type(self, registry):
        """get_service_class returns None for non-existent provider type"""
        @registry.register_service("llm", "openai")
        class OpenAIService:
            pass

        result = registry.get_service_class("llm", "unknown")
        assert result is None


class TestCreateService:
    """Tests for ProviderRegistry.create_service"""

    def test_calls_from_config_with_kwargs(self, registry):
        """create_service calls from_config with config and extra kwargs"""
        registry._services["llm"]["openai"] = MockServiceWithFromConfig
        config = MockOpenAIConfig(api_key="test123")

        instance = registry.create_service("llm", config, extra_param="hello")

        assert isinstance(instance, MockServiceWithFromConfig)
        assert instance.kwargs["config"] is config
        assert instance.kwargs["extra_param"] == "hello"

    def test_raises_value_error_for_unknown_type(self, registry):
        """create_service raises ValueError when no service registered for type"""
        config = MockOpenAIConfig(api_key="test")
        with pytest.raises(ValueError, match="Service implementation not found"):
            registry.create_service("llm", config)

    def test_raises_value_error_when_missing_from_config(self, registry):
        """create_service raises ValueError when service class lacks from_config"""
        registry._services["llm"]["openai"] = MockServiceNoFromConfig
        config = MockOpenAIConfig(api_key="test")

        with pytest.raises(ValueError, match="missing the from_config class method"):
            registry.create_service("llm", config)

    def test_raises_value_error_for_unknown_category(self, registry):
        """create_service raises ValueError for unknown category"""
        config = MockOpenAIConfig(api_key="test")
        with pytest.raises(ValueError):
            registry.create_service("nonexistent", config)


class TestListServices:
    """Tests for ProviderRegistry.list_services"""

    def test_list_services_returns_registered_names(self, registry):
        """list_services returns names of all registered services"""
        @registry.register_service("llm", "svc_a")
        class ServiceA:
            pass

        @registry.register_service("llm", "svc_b")
        class ServiceB:
            pass

        names = registry.list_services("llm")
        assert sorted(names) == ["svc_a", "svc_b"]

    def test_list_services_empty(self, registry):
        """list_services returns empty list when no services registered"""
        assert registry.list_services("llm") == []

    def test_list_services_unknown_category(self, registry):
        """list_services returns empty list for unknown category"""
        assert registry.list_services("unknown_cat") == []


class TestGet:
    """Tests for ProviderRegistry.get"""

    def test_returns_config_class(self, registry):
        """get returns the registered config class"""
        @registry.register_config("llm", "openai")
        class ConfigClass(ProviderConfig):
            type: Literal["openai"] = "openai"

        result = registry.get("llm", "openai")
        assert result is ConfigClass

    def test_returns_none_for_unknown(self, registry):
        """get returns None when provider not found"""
        result = registry.get("llm", "nonexistent")
        assert result is None

    def test_uses_providers_alias(self, registry):
        """get reads from _providers (alias of _configs)"""
        @registry.register_config("tts", "edge")
        class EdgeConfig(ProviderConfig):
            type: Literal["edge"] = "edge"

        # Should work since _providers is aliased to _configs
        result = registry.get("tts", "edge")
        assert result is EdgeConfig


class TestListProviders:
    """Tests for ProviderRegistry.list_providers"""

    def test_list_providers_returns_names(self, registry):
        """list_providers returns registered provider names"""
        registry._providers["llm"]["p1"] = MockOpenAIConfig
        registry._providers["llm"]["p2"] = MockGLMConfig

        names = registry.list_providers("llm")
        assert sorted(names) == ["p1", "p2"]

    def test_list_providers_empty(self, registry):
        """list_providers returns empty list for empty category"""
        assert registry.list_providers("vad") == []


class TestGetAllProviders:
    """Tests for ProviderRegistry.get_all_providers"""

    def test_get_all_providers_returns_copy(self, registry):
        """get_all_providers returns all providers as a nested dict"""
        registry._providers["llm"]["openai"] = MockOpenAIConfig
        registry._providers["llm"]["glm"] = MockGLMConfig
        registry._providers["asr"]["whisper"] = MockWhisperConfig

        all_providers = registry.get_all_providers()

        assert "llm" in all_providers
        assert "asr" in all_providers
        assert "tts" in all_providers
        assert "vad" in all_providers
        assert all_providers["llm"]["openai"] is MockOpenAIConfig
        assert all_providers["asr"]["whisper"] is MockWhisperConfig

    def test_get_all_providers_is_top_level_copy(self, registry):
        """get_all_providers returns a top-level copy (inner dicts are shared references)"""
        registry._providers["llm"]["openai"] = MockOpenAIConfig
        all_providers = registry.get_all_providers()

        # Modifying the top-level dict should not affect the original
        all_providers["new_cat"] = {}
        assert "new_cat" not in registry._providers

    def test_get_all_providers_empty_categories(self, registry):
        """get_all_providers returns all category keys even when empty"""
        all_providers = registry.get_all_providers()
        assert set(all_providers.keys()) == {"llm", "asr", "tts", "vad"}
        assert all_providers["llm"] == {}


class TestCreateUnionType:
    """Tests for ProviderRegistry.create_union_type"""

    def test_creates_annotated_union(self, registry):
        """create_union_type returns Annotated[Union[...], Field(discriminator='type')]"""
        import typing

        registry._providers["llm"]["openai"] = MockOpenAIConfig
        registry._providers["llm"]["glm"] = MockGLMConfig

        result = registry.create_union_type("llm")

        # Verify it's an Annotated type
        origin = typing.get_origin(result)
        assert origin is typing.Annotated

        # The first arg should be a Union containing our config classes
        args = typing.get_args(result)
        union_type = args[0]
        assert typing.get_origin(union_type) is typing.Union

        union_args = typing.get_args(union_type)
        assert MockOpenAIConfig in union_args
        assert MockGLMConfig in union_args

    def test_raises_value_error_when_no_providers(self, registry):
        """create_union_type raises ValueError when no providers registered"""
        with pytest.raises(ValueError, match="No registered"):
            registry.create_union_type("llm")

    def test_creates_single_element_union(self, registry):
        """create_union_type works with a single provider"""
        import typing

        registry._providers["tts"]["edge"] = MockWhisperConfig

        result = registry.create_union_type("tts")

        # Union[X] is unwrapped to X at runtime, so check origin differently
        origin = typing.get_origin(result)
        assert origin is typing.Annotated

        # First arg - in single-provider case it's the class itself (Union unwrapped)
        args = typing.get_args(result)
        assert args[0] is MockWhisperConfig


class TestClear:
    """Tests for ProviderRegistry.clear"""

    def test_clear_specific_category(self, registry):
        """clear(category) clears only the specified category"""
        registry._providers["llm"]["openai"] = MockOpenAIConfig
        registry._providers["asr"]["whisper"] = MockWhisperConfig

        registry.clear("llm")

        assert registry._providers["llm"] == {}
        assert "whisper" in registry._providers["asr"]

    def test_clear_all(self, registry):
        """clear() with no args clears all categories"""
        registry._providers["llm"]["openai"] = MockOpenAIConfig
        registry._providers["asr"]["whisper"] = MockWhisperConfig
        registry._providers["tts"]["edge"] = MockOpenAIConfig
        registry._providers["vad"]["silero"] = MockOpenAIConfig

        registry.clear()

        for cat in ("llm", "asr", "tts", "vad"):
            assert registry._providers[cat] == {}

    def test_clear_does_not_affect_services(self, registry):
        """clear should only affect provider configs, not service registrations"""
        registry._providers["llm"]["openai"] = MockOpenAIConfig
        registry._services["llm"]["openai"] = MockServiceWithFromConfig

        registry.clear()

        # Providers cleared
        assert registry._providers["llm"] == {}
        # Services untouched
        assert registry._services["llm"]["openai"] is MockServiceWithFromConfig
