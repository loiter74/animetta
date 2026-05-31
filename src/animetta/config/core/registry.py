"""Provider registry - the core for implementing plugin-based configuration and services"""

from typing import Annotated, Literal, Union

from loguru import logger
from pydantic import Field

from .base import ProviderConfig


class ProviderRegistry:
    """
    Provider registry (upgraded)

    Manages both configuration classes and service classes for true plugin support:
    - Configuration classes: Pydantic models for YAML deserialization
    - Service classes: Implementation classes that execute business logic

    Example:
        # Register config class
        @ProviderRegistry.register_config("llm", "openai")
        class OpenAILLMConfig(LLMBaseConfig):
            type: Literal["openai"] = "openai"

        # Register service class
        @ProviderRegistry.register_service("llm", "openai")
        class OpenAIAgent(AgentInterface):
            @classmethod
            def from_config(cls, config: OpenAILLMConfig) -> "OpenAIAgent":
                return cls(api_key=config.api_key, ...)
    """

    # Config class storage: {"llm": {"openai": OpenAILLMConfig, ...}, ...}
    _configs: dict[str, dict[str, type[ProviderConfig]]] = {
        "llm": {},
        "asr": {},
        "tts": {},
        "vad": {},
    }

    # Service class storage: {"llm": {"openai": OpenAIAgent, ...}, ...}
    _services: dict[str, dict[str, type]] = {
        "llm": {},
        "asr": {},
        "tts": {},
        "vad": {},
    }

    # Compatible with old API
    _providers = _configs  # Alias for backward compatibility

    # ==================== Config Class Registration ====================

    @classmethod
    def register_config(cls, category: Literal["llm", "asr", "tts", "vad"], provider_type: str):
        """
        Decorator: Register a provider configuration class (recommended name)

        Args:
            category: Provider category (llm/asr/tts)
            provider_type: Provider type identifier (e.g., openai, glm, ollama)

        Returns:
            Decorator function
        """
        def decorator(config_class: type[ProviderConfig]) -> type[ProviderConfig]:
            cls._configs[category][provider_type] = config_class
            logger.debug(f"Registered config class: {category}.{provider_type} -> {config_class.__name__}")
            return config_class
        return decorator

    @classmethod
    def register(cls, category: str, provider_type: str):
        """Register a provider config class (shorthand for register_config)."""
        return cls.register_config(category, provider_type)

    # ==================== Service Class Registration ====================

    @classmethod
    def register_service(cls, category: Literal["llm", "asr", "tts"], provider_type: str):
        """
        Decorator: Register a service implementation class

        Args:
            category: Provider category (llm/asr/tts)
            provider_type: Provider type identifier (must match config class)

        Returns:
            Decorator function

        Usage:
            @ProviderRegistry.register_service("llm", "openai")
            class OpenAIAgent(AgentInterface):
                @classmethod
                def from_config(cls, config: OpenAILLMConfig) -> "OpenAIAgent":
                    return cls(api_key=config.api_key, model=config.model)
        """
        def decorator(service_class: type) -> type:
            cls._services[category][provider_type] = service_class
            logger.debug(f"Registered service class: {category}.{provider_type} -> {service_class.__name__}")
            return service_class
        return decorator

    @classmethod
    def get_service_class(cls, category: str, provider_type: str) -> type | None:
        """
        Get the service implementation class

        Args:
            category: Provider category
            provider_type: Provider type identifier

        Returns:
            Service class, or None if not found
        """
        return cls._services.get(category, {}).get(provider_type)

    @classmethod
    def create_service(cls, category: str, config: ProviderConfig, **extra_kwargs):
        """
        Automatically create a service instance from configuration

        Args:
            category: Provider category (llm/asr/tts)
            config: Configuration object (contains type field)
            **extra_kwargs: Extra arguments (e.g., system_prompt)

        Returns:
            Service instance

        Raises:
            ValueError: If no matching service class is found

        Usage:
            config = OpenAILLMConfig(api_key="...", model="gpt-4")
            agent = ProviderRegistry.create_service("llm", config, system_prompt="...")
        """
        provider_type = config.type
        service_class = cls.get_service_class(category, provider_type)

        if service_class is None:
            raise ValueError(
                f"Service implementation not found: {category}.{provider_type}. "
                f"Available services: {list(cls._services.get(category, {}).keys())}"
            )

        # Call the service class's from_config method
        if hasattr(service_class, 'from_config'):
            return service_class.from_config(config, **extra_kwargs)
        else:
            raise ValueError(
                f"Service class {service_class.__name__} is missing the from_config class method"
            )

    @classmethod
    def list_services(cls, category: str) -> list[str]:
        """List all registered services under a category"""
        return list(cls._services.get(category, {}).keys())

    @classmethod
    def get(cls, category: str, provider_type: str) -> type[ProviderConfig] | None:
        """
        Get the specified provider configuration class

        Args:
            category: Provider category (llm/asr/tts)
            provider_type: Provider type identifier

        Returns:
            Configuration class, or None if not found
        """
        return cls._providers.get(category, {}).get(provider_type)

    @classmethod
    def list_providers(cls, category: str) -> list[str]:
        """
        List all registered providers under a category

        Args:
            category: Provider category (llm/asr/tts)

        Returns:
            List of provider type identifiers
        """
        return list(cls._providers.get(category, {}).keys())

    @classmethod
    def get_all_providers(cls) -> dict[str, dict[str, type[ProviderConfig]]]:
        """
        Get all registered providers

        Returns:
            Nested dictionary of all providers
        """
        return cls._providers.copy()

    @classmethod
    def create_union_type(cls, category: str):
        """
        Dynamically create a Discriminated Union type

        Args:
            category: Provider category (llm/asr/tts)

        Returns:
            Annotated[Union[...], Field(discriminator="type")] type

        Usage:
            LLMConfig = ProviderRegistry.create_union_type("llm")
        """
        classes = list(cls._providers[category].values())
        if not classes:
            raise ValueError(f"No registered {category} providers")

        # Create Union type
        union_type = Union[tuple(classes)]

        # Use discriminator for automatic type identification
        return Annotated[union_type, Field(discriminator="type")]

    @classmethod
    def clear(cls, category: str = None):
        """
        Clear registration info (mainly for testing)

        Args:
            category: Category to clear, if None clears all
        """
        if category:
            cls._providers[category] = {}
        else:
            for cat in cls._providers:
                cls._providers[cat] = {}
