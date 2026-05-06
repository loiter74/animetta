"""Application configuration - service-driven configuration loading"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, PrivateAttr, TypeAdapter
from dotenv import load_dotenv
from loguru import logger

from .core.base import BaseConfig
from .system import SystemConfig
from .providers.asr import ASRConfig
from .providers.tts import TTSConfig
from .providers.vad import VADConfig
from .providers.llm import LLMConfig
from .agent import AgentConfig
from .persona import PersonaConfig

# Create TypeAdapter for validating Discriminated Union types
_asr_adapter = TypeAdapter(ASRConfig)
_tts_adapter = TypeAdapter(TTSConfig)
_llm_adapter = TypeAdapter(LLMConfig)
_vad_adapter = TypeAdapter(VADConfig)

# Lazy import AgentConfig's TypeAdapter (avoid circular imports)
_agent_adapter = None

def _get_agent_adapter():
    """Lazily get the TypeAdapter for AgentConfig"""
    global _agent_adapter
    if _agent_adapter is None:
        from .agent import AgentConfig
        _agent_adapter = TypeAdapter(AgentConfig)
    return _agent_adapter


def expand_env_vars(value):
    """Recursively expand environment variables in strings"""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'

        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            env_value = os.getenv(var_name, "")

            # Only log API key status on first load
            if var_name == "GLM_API_KEY":
                if env_value and not hasattr(replace_var, '_logged'):
                    logger.debug(f"[expand_env_vars] GLM_API_KEY loaded: {env_value[:20]}...")
                    replace_var._logged = True
                elif not env_value and not hasattr(replace_var, '_error_logged'):
                    logger.error(f"[expand_env_vars] GLM_API_KEY not set!")
                    replace_var._error_logged = True

            return env_value

        return re.sub(pattern, replace_var, value)
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def _load_env_file() -> None:
    """
    Load .env file into environment variables

    Search by priority:
    1. Project root .env (config/../)
    2. Current working directory .env
    3. Path specified by ANIMA_ENV_FILE environment variable

    Ensures ${VAR} syntax is correctly expanded in YAML configuration.
    """
    # Avoid duplicate loading
    if hasattr(_load_env_file, '_loaded'):
        return
    _load_env_file._loaded = True

    # Search paths (by priority)
    search_paths = [
        Path.cwd() / ".env",                         # Current working directory
        CONFIG_DIR.parent / ".env",                   # Project root directory
        Path(__file__).parent.parent.parent.parent / ".env",  # Project root (absolute path)
    ]

    env_path_env = os.getenv("ANIMA_ENV_FILE")
    if env_path_env:
        search_paths.insert(0, Path(env_path_env))

    loaded_path = None
    for p in search_paths:
        if p.exists():
            load_dotenv(dotenv_path=str(p), override=False)
            loaded_path = p
            logger.debug(f"[_load_env_file] Loaded .env file: {p}")
            break

    if loaded_path is None:
        logger.warning("[_load_env_file] No .env file found, environment variables may be empty")


CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
SERVICES_DIR = CONFIG_DIR / "services"

# Config cache (avoid duplicate loading and logging)
_services_yaml_cache = None
_services_config_logged = set()


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load YAML file"""
    try:
        import yaml
    except ImportError:
        raise ImportError("Please install PyYAML: pip install pyyaml")
    
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}


# Cache loaded service configs to avoid duplicate logs
_services_yaml_cache: Optional[Dict[str, Any]] = None
_services_config_logged: set = set()


def _load_service_config(service_type: str, service_name: str) -> Dict[str, Any]:
    """
    Load configuration for a single service

    Args:
        service_type: Service type (asr/tts/llm/vad)
        service_name: Service name (openai/glm/ollama/mock, etc.)

    Returns:
        Dict: Service configuration
    """
    global _services_yaml_cache

    cache_key = f"{service_type}/{service_name}"

    # Try loading from unified services.yaml (using cache)
    unified_services_path = CONFIG_DIR / "services.yaml"
    if unified_services_path.exists():
        if _services_yaml_cache is None:
            _services_yaml_cache = _load_yaml_file(unified_services_path)

        if service_type in _services_yaml_cache and service_name in _services_yaml_cache[service_type]:
            # Only log once
            if cache_key not in _services_config_logged:
                logger.debug(f"Loading service config: {cache_key}")
                _services_config_logged.add(cache_key)
            return _services_yaml_cache[service_type][service_name]

    # Fallback to old separate config files (backward compatible)
    service_path = SERVICES_DIR / service_type / f"{service_name}.yaml"
    if not service_path.exists():
        raise FileNotFoundError(f"Service configuration not found: {service_path}")
    if cache_key not in _services_config_logged:
        logger.debug(f"Loading service config: {cache_key}")
        _services_config_logged.add(cache_key)
    return _load_yaml_file(service_path)


class ServicesConfig(BaseConfig):
    """Service composition configuration"""
    asr: str = Field(default="mock", description="ASR service name")
    tts: str = Field(default="mock", description="TTS service name")
    agent: str = Field(default="mock", description="Agent service name (base LLM)")
    local_llm: Optional[str] = Field(default=None, description="Local LLM service name (optional, skipped if not set)")
    vad: str = Field(default="mock", description="VAD service name")


class AppConfig(BaseConfig):
    """
    Application configuration

    Services are specified via the services field, with config files at config/services/{type}/{name}.yaml
    """
    # Persona
    persona: str = Field(default="default", description="Persona name")
    
    # Service composition
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    
    # System configuration
    system: SystemConfig = Field(default_factory=SystemConfig)
    
    # AI service configuration (loaded from service config files)
    asr: Optional[ASRConfig] = Field(default=None)
    tts: Optional[TTSConfig] = Field(default=None)
    agent: Optional[AgentConfig] = Field(default=None)
    local_llm: Optional[LLMConfig] = Field(default=None, description="Local LLM config (no persona)")
    vad: Optional[VADConfig] = Field(default=None)
    
    # Private fields
    _persona: Optional[PersonaConfig] = PrivateAttr(default=None)

    def get_persona(self) -> PersonaConfig:
        """Get persona configuration (lazy loaded)"""
        if self._persona is None:
            self._persona = PersonaConfig.load(self.persona)
        return self._persona

    def get_system_prompt(self, live2d_prompt: Optional[str] = None) -> str:
        """
        Get the complete system prompt

        Args:
            live2d_prompt: Live2D expression prompt (optional)
        """
        return self.get_persona().build_system_prompt(live2d_prompt=live2d_prompt)

    @classmethod
    def from_yaml(cls, path: str) -> "AppConfig":
        """
        Load configuration from YAML file

        Loading process:
        1. Load .env file (prefer project root)
        2. Read main configuration file
        3. Load each service from services/{type}/{name}.yaml
        4. Expand environment variables ${VAR}
        5. Apply environment variable overrides
        """
        # Load .env file into environment variables (so ${VAR} syntax works)
        _load_env_file()
        
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        main_config = _load_yaml_file(path)
        config = cls._load_services_mode(main_config)
        
        # Expand environment variables
        config._apply_env_expansion()
        
        # Apply environment variable overrides
        config._apply_env_overrides()
        
        logger.debug(f"Configuration loaded: persona={config.persona}")
        return config

    @classmethod
    def _load_services_mode(cls, main_config: Dict[str, Any]) -> "AppConfig":
        """Services mode loading"""
        services_config = main_config.get("services", {})

        # Load each service configuration
        asr_name = services_config.get("asr", "mock")
        tts_name = services_config.get("tts", "mock")
        agent_name = services_config.get("agent", "mock")
        local_llm_name = services_config.get("local_llm")  # None if not specified
        vad_name = services_config.get("vad", "mock")

        asr_data = _load_service_config("asr", asr_name)
        tts_data = _load_service_config("tts", tts_name)
        agent_data = _load_service_config("llm", agent_name)

        # Only load local_llm when specified
        local_llm_data = None
        if local_llm_name:
            local_llm_full = _load_service_config("llm", local_llm_name)
            # local_llm config includes llm_config nesting, needs extraction
            local_llm_data = local_llm_full.get("llm_config", local_llm_full)

        vad_data = _load_service_config("vad", vad_name)

        # Build complete configuration
        merged = {
            **main_config,
            "asr": asr_data,
            "tts": tts_data,
            "agent": agent_data,
            "local_llm": local_llm_data,
            "vad": vad_data,
        }

        return cls(**merged)

    def _apply_env_expansion(self) -> None:
        """Recursively expand environment variables in all configs"""
        # Expand environment variables in service configs
        # Since ASRConfig/TTSConfig is a Discriminated Union,
        # TypeAdapter is needed for validation
        if self.asr:
            asr_dict = self.asr.model_dump()
            asr_dict = expand_env_vars(asr_dict)
            self.asr = _asr_adapter.validate_python(asr_dict)
            logger.debug(f"ASR config after expansion: type={self.asr.type}")
        
        if self.tts:
            tts_dict = self.tts.model_dump()
            tts_dict = expand_env_vars(tts_dict)
            self.tts = _tts_adapter.validate_python(tts_dict)
            logger.debug(f"TTS config after expansion: type={self.tts.type}")
        
        if self.agent:
            agent_dict = self.agent.model_dump()
            logger.debug(f"Agent config before expansion: {agent_dict}")
            agent_dict = expand_env_vars(agent_dict)
            logger.debug(f"Agent config after expansion: {agent_dict}")
            self.agent = AgentConfig.model_validate(agent_dict)
            # Validate llm_config type and API Key
            if self.agent.llm_config:
                logger.debug(f"Agent LLM type: {self.agent.llm_config.type}")
                logger.debug(f"Agent LLM Config class: {type(self.agent.llm_config).__name__}")

                # Only check LLM types that need API Key
                # Local models (local_lora, ollama, mock) don't need API Key
                needs_api_key = self.agent.llm_config.type not in ["local_lora", "ollama", "mock"]

                if needs_api_key and hasattr(self.agent.llm_config, 'api_key'):
                    api_key = self.agent.llm_config.api_key
                    if api_key:
                        logger.debug(f"[AppConfig] Agent LLM API Key set: {api_key[:20]}... (length: {len(api_key)})")
                    else:
                        logger.error(f"[AppConfig] Agent LLM API Key is empty! LLM type: {self.agent.llm_config.type} requires API Key")
                elif not needs_api_key:
                    logger.debug(f"[AppConfig] Using local LLM: {self.agent.llm_config.type}")

        # Handle local_llm config
        if self.local_llm:
            local_llm_dict = self.local_llm.model_dump()
            logger.debug(f"Local LLM config before expansion: {local_llm_dict}")
            local_llm_dict = expand_env_vars(local_llm_dict)
            logger.debug(f"Local LLM config after expansion: {local_llm_dict}")
            self.local_llm = _llm_adapter.validate_python(local_llm_dict)

            # Validate API Key (local models don't need API Key, but check just in case)
            if hasattr(self.local_llm, 'api_key'):
                api_key = self.local_llm.api_key
                if api_key:
                    logger.debug(f"[AppConfig] Local LLM API Key set: {api_key[:20]}... (length: {len(api_key)})")
                else:
                    logger.debug(f"[AppConfig] Local LLM does not need API Key (local model)")

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""
        # LLM configuration
        if self.agent and self.agent.llm_config:
            if os.getenv("LLM_API_KEY"):
                self.agent.llm_config.api_key = os.getenv("LLM_API_KEY")
            if os.getenv("LLM_MODEL") and hasattr(self.agent.llm_config, 'model'):
                self.agent.llm_config.model = os.getenv("LLM_MODEL")
        
        # ASR configuration
        if self.asr and hasattr(self.asr, 'api_key') and os.getenv("ASR_API_KEY"):
            self.asr.api_key = os.getenv("ASR_API_KEY")
        
        # TTS configuration
        if self.tts and hasattr(self.tts, 'api_key') and os.getenv("TTS_API_KEY"):
            self.tts.api_key = os.getenv("TTS_API_KEY")
        
        # System configuration
        if os.getenv("ANIMA_HOST"):
            self.system.host = os.getenv("ANIMA_HOST")
        if os.getenv("ANIMA_PORT"):
            try:
                self.system.port = int(os.getenv("ANIMA_PORT"))
            except ValueError:
                pass

    def validate(self) -> None:
        """Validate configuration — verify required providers are available."""
        from anima.config.core.registry import ProviderRegistry

        warnings = []

        # Check LLM provider
        if self.services.agent:
            services = ProviderRegistry.list_services("llm")
            if self.services.agent not in services:
                warnings.append(f"LLM provider '{self.services.agent}' not registered")

        # Check ASR provider
        if self.services.asr:
            services = ProviderRegistry.list_services("asr")
            if self.services.asr not in services:
                warnings.append(f"ASR provider '{self.services.asr}' not registered")

        # Check TTS provider
        if self.services.tts:
            services = ProviderRegistry.list_services("tts")
            if self.services.tts not in services:
                warnings.append(f"TTS provider '{self.services.tts}' not registered")

        if warnings:
            for w in warnings:
                logger.warning(f"[Config] {w}")

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """
        Smart config loading

        Priority:
        1. Specified config file path
        2. ANIMA_CONFIG environment variable
        3. Default path ./config/config.yaml
        """
        if config_path:
            path = config_path
        elif os.getenv("ANIMA_CONFIG"):
            path = os.getenv("ANIMA_CONFIG")
        else:
            default_paths = [
                Path("config/config.yaml"),
                Path("config.yaml"),
                Path(__file__).parent.parent.parent.parent / "config" / "config.yaml",
            ]
            path = None
            for p in default_paths:
                if p.exists():
                    path = str(p)
                    break
        
        if path and Path(path).exists():
            logger.debug(f"Loading config from file: {path}")
            return cls.from_yaml(path)
        
        raise FileNotFoundError(
            "Configuration file not found. Please create config/config.yaml or set the ANIMA_CONFIG environment variable"
        )