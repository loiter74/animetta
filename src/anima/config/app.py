"""应用总配置 - 服务驱动的配置加载"""

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

# 创建 TypeAdapter 用于验证 Discriminated Union 类型
_asr_adapter = TypeAdapter(ASRConfig)
_tts_adapter = TypeAdapter(TTSConfig)
_llm_adapter = TypeAdapter(LLMConfig)
_vad_adapter = TypeAdapter(VADConfig)

# 延迟导入 AgentConfig 的 TypeAdapter（避免循环导入）
_agent_adapter = None

def _get_agent_adapter():
    """延迟获取 AgentConfig 的 TypeAdapter"""
    global _agent_adapter
    if _agent_adapter is None:
        from .agent import AgentConfig
        _agent_adapter = TypeAdapter(AgentConfig)
    return _agent_adapter


def expand_env_vars(value):
    """递归展开字符串中的环境变量"""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'

        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            env_value = os.getenv(var_name, "")

            # 只在首次加载时记录 API Key 状态
            if var_name == "GLM_API_KEY":
                if env_value and not hasattr(replace_var, '_logged'):
                    logger.debug(f"[expand_env_vars] GLM_API_KEY 已加载: {env_value[:20]}...")
                    replace_var._logged = True
                elif not env_value and not hasattr(replace_var, '_error_logged'):
                    logger.error(f"[expand_env_vars] ⚠️ GLM_API_KEY 未设置！")
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
    加载 .env 文件到环境变量

    按优先级搜索:
    1. 项目根目录的 .env（config/../）
    2. 当前工作目录的 .env
    3. 环境变量 ANIMA_ENV_FILE 指定的路径

    确保 ${VAR} 语法在 YAML 配置中能正确展开。
    """
    # 避免重复加载
    if hasattr(_load_env_file, '_loaded'):
        return
    _load_env_file._loaded = True

    # 搜索路径（按优先级）
    search_paths = [
        Path.cwd() / ".env",                         # 当前工作目录
        CONFIG_DIR.parent / ".env",                   # 项目根目录
        Path(__file__).parent.parent.parent.parent / ".env",  # 项目根目录（绝对路径）
    ]

    env_path_env = os.getenv("ANIMA_ENV_FILE")
    if env_path_env:
        search_paths.insert(0, Path(env_path_env))

    loaded_path = None
    for p in search_paths:
        if p.exists():
            load_dotenv(dotenv_path=str(p), override=False)
            loaded_path = p
            logger.debug(f"[_load_env_file] 已加载 .env 文件: {p}")
            break

    if loaded_path is None:
        logger.warning("[_load_env_file] 未找到 .env 文件，环境变量可能为空")


CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
SERVICES_DIR = CONFIG_DIR / "services"

# 配置缓存（避免重复加载和日志）
_services_yaml_cache = None
_services_config_logged = set()


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """加载 YAML 文件"""
    try:
        import yaml
    except ImportError:
        raise ImportError("请安装 PyYAML: pip install pyyaml")
    
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}


# 缓存已加载的服务配置，避免重复日志
_services_yaml_cache: Optional[Dict[str, Any]] = None
_services_config_logged: set = set()


def _load_service_config(service_type: str, service_name: str) -> Dict[str, Any]:
    """
    加载单个服务的配置

    Args:
        service_type: 服务类型 (asr/tts/llm/vad)
        service_name: 服务名称 (openai/glm/ollama/mock 等)

    Returns:
        Dict: 服务配置
    """
    global _services_yaml_cache

    cache_key = f"{service_type}/{service_name}"

    # 尝试从统一的 services.yaml 加载（使用缓存）
    unified_services_path = CONFIG_DIR / "services.yaml"
    if unified_services_path.exists():
        if _services_yaml_cache is None:
            _services_yaml_cache = _load_yaml_file(unified_services_path)

        if service_type in _services_yaml_cache and service_name in _services_yaml_cache[service_type]:
            # 只打印一次日志
            if cache_key not in _services_config_logged:
                logger.debug(f"加载服务配置: {cache_key}")
                _services_config_logged.add(cache_key)
            return _services_yaml_cache[service_type][service_name]

    # 回退到旧的分散配置文件（向后兼容）
    service_path = SERVICES_DIR / service_type / f"{service_name}.yaml"
    if not service_path.exists():
        raise FileNotFoundError(f"服务配置不存在: {service_path}")
    if cache_key not in _services_config_logged:
        logger.debug(f"加载服务配置: {cache_key}")
        _services_config_logged.add(cache_key)
    return _load_yaml_file(service_path)


class ServicesConfig(BaseConfig):
    """服务组合配置"""
    asr: str = Field(default="mock", description="ASR 服务名称")
    tts: str = Field(default="mock", description="TTS 服务名称")
    agent: str = Field(default="mock", description="Agent 服务名称（底座LLM）")
    local_llm: Optional[str] = Field(default=None, description="本地LLM服务名称（可选，不设置则不加载）")
    vad: str = Field(default="mock", description="VAD 服务名称")


class AppConfig(BaseConfig):
    """
    应用总配置
    
    通过 services 字段指定各服务，配置文件位于 config/services/{type}/{name}.yaml
    """
    # 人设
    persona: str = Field(default="default", description="人设名称")
    
    # 服务组合
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    
    # 系统配置
    system: SystemConfig = Field(default_factory=SystemConfig)
    
    # AI 服务配置（从服务配置文件加载）
    asr: Optional[ASRConfig] = Field(default=None)
    tts: Optional[TTSConfig] = Field(default=None)
    agent: Optional[AgentConfig] = Field(default=None)
    local_llm: Optional[LLMConfig] = Field(default=None, description="本地LLM配置（无persona）")
    vad: Optional[VADConfig] = Field(default=None)
    
    # 私有字段
    _persona: Optional[PersonaConfig] = PrivateAttr(default=None)

    def get_persona(self) -> PersonaConfig:
        """获取人设配置（延迟加载）"""
        if self._persona is None:
            self._persona = PersonaConfig.load(self.persona)
        return self._persona

    def get_system_prompt(self, live2d_prompt: Optional[str] = None) -> str:
        """
        获取完整的系统提示词

        Args:
            live2d_prompt: Live2D 表情提示词（可选）
        """
        return self.get_persona().build_system_prompt(live2d_prompt=live2d_prompt)

    @classmethod
    def from_yaml(cls, path: str) -> "AppConfig":
        """
        从 YAML 文件加载配置
        
        加载流程:
        1. 加载 .env 文件（优先从项目根目录）
        2. 读取主配置文件
        3. 从 services/{type}/{name}.yaml 分别加载各服务
        4. 展开环境变量 ${VAR}
        5. 应用环境变量覆盖
        """
        # 🆕 加载 .env 文件到环境变量（使 ${VAR} 语法生效）
        _load_env_file()
        
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        main_config = _load_yaml_file(path)
        config = cls._load_services_mode(main_config)
        
        # 展开环境变量
        config._apply_env_expansion()
        
        # 应用环境变量覆盖
        config._apply_env_overrides()
        
        logger.debug(f"配置加载完成: persona={config.persona}")
        return config

    @classmethod
    def _load_services_mode(cls, main_config: Dict[str, Any]) -> "AppConfig":
        """Services 模式加载"""
        services_config = main_config.get("services", {})

        # 加载各个服务配置
        asr_name = services_config.get("asr", "mock")
        tts_name = services_config.get("tts", "mock")
        agent_name = services_config.get("agent", "mock")
        local_llm_name = services_config.get("local_llm")  # None if not specified
        vad_name = services_config.get("vad", "mock")

        asr_data = _load_service_config("asr", asr_name)
        tts_data = _load_service_config("tts", tts_name)
        agent_data = _load_service_config("llm", agent_name)

        # 只在指定时加载 local_llm
        local_llm_data = None
        if local_llm_name:
            local_llm_full = _load_service_config("llm", local_llm_name)
            # local_llm配置文件包含llm_config嵌套，需要提取
            local_llm_data = local_llm_full.get("llm_config", local_llm_full)

        vad_data = _load_service_config("vad", vad_name)

        # 构建完整配置
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
        """递归展开所有配置中的环境变量"""
        # 展开各服务配置中的环境变量
        # 由于 ASRConfig/TTSConfig 是 Discriminated Union，
        # 需要使用 TypeAdapter 来验证
        if self.asr:
            asr_dict = self.asr.model_dump()
            asr_dict = expand_env_vars(asr_dict)
            self.asr = _asr_adapter.validate_python(asr_dict)
            logger.debug(f"ASR 配置展开后: type={self.asr.type}")
        
        if self.tts:
            tts_dict = self.tts.model_dump()
            tts_dict = expand_env_vars(tts_dict)
            self.tts = _tts_adapter.validate_python(tts_dict)
            logger.debug(f"TTS 配置展开后: type={self.tts.type}")
        
        if self.agent:
            agent_dict = self.agent.model_dump()
            logger.debug(f"Agent 配置展开前: {agent_dict}")
            agent_dict = expand_env_vars(agent_dict)
            logger.debug(f"Agent 配置展开后: {agent_dict}")
            self.agent = AgentConfig.model_validate(agent_dict)
            # 验证 llm_config 的类型和 API Key
            if self.agent.llm_config:
                logger.debug(f"Agent LLM 类型: {self.agent.llm_config.type}")
                logger.debug(f"Agent LLM Config 类: {type(self.agent.llm_config).__name__}")

                # 只对需要 API Key 的 LLM 类型进行检查
                # 本地模型（local_lora、ollama、mock）不需要 API Key
                needs_api_key = self.agent.llm_config.type not in ["local_lora", "ollama", "mock"]

                if needs_api_key and hasattr(self.agent.llm_config, 'api_key'):
                    api_key = self.agent.llm_config.api_key
                    if api_key:
                        logger.debug(f"[AppConfig] Agent LLM API Key 已设置: {api_key[:20]}... (长度: {len(api_key)})")
                    else:
                        logger.error(f"[AppConfig] ⚠️ Agent LLM API Key 为空！LLM 类型: {self.agent.llm_config.type} 需要 API Key")
                elif not needs_api_key:
                    logger.debug(f"[AppConfig] 使用本地 LLM: {self.agent.llm_config.type}")

        # 处理 local_llm 配置
        if self.local_llm:
            local_llm_dict = self.local_llm.model_dump()
            logger.debug(f"Local LLM 配置展开前: {local_llm_dict}")
            local_llm_dict = expand_env_vars(local_llm_dict)
            logger.debug(f"Local LLM 配置展开后: {local_llm_dict}")
            self.local_llm = _llm_adapter.validate_python(local_llm_dict)

            # 验证 API Key（本地模型不需要API Key，但检查一下以防万一）
            if hasattr(self.local_llm, 'api_key'):
                api_key = self.local_llm.api_key
                if api_key:
                    logger.debug(f"[AppConfig] Local LLM API Key 已设置: {api_key[:20]}... (长度: {len(api_key)})")
                else:
                    logger.debug(f"[AppConfig] Local LLM 无需 API Key（本地模型）")

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # LLM 配置
        if self.agent and self.agent.llm_config:
            if os.getenv("LLM_API_KEY"):
                self.agent.llm_config.api_key = os.getenv("LLM_API_KEY")
            if os.getenv("LLM_MODEL") and hasattr(self.agent.llm_config, 'model'):
                self.agent.llm_config.model = os.getenv("LLM_MODEL")
        
        # ASR 配置
        if self.asr and hasattr(self.asr, 'api_key') and os.getenv("ASR_API_KEY"):
            self.asr.api_key = os.getenv("ASR_API_KEY")
        
        # TTS 配置
        if self.tts and hasattr(self.tts, 'api_key') and os.getenv("TTS_API_KEY"):
            self.tts.api_key = os.getenv("TTS_API_KEY")
        
        # 系统配置
        if os.getenv("ANIMA_HOST"):
            self.system.host = os.getenv("ANIMA_HOST")
        if os.getenv("ANIMA_PORT"):
            try:
                self.system.port = int(os.getenv("ANIMA_PORT"))
            except ValueError:
                pass

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """
        智能加载配置
        
        优先级:
        1. 指定的配置文件路径
        2. 环境变量 ANIMA_CONFIG
        3. 默认路径 ./config/config.yaml
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
            logger.debug(f"从配置文件加载: {path}")
            return cls.from_yaml(path)
        
        raise FileNotFoundError(
            "未找到配置文件。请创建 config/config.yaml 或设置 ANIMA_CONFIG 环境变量"
        )