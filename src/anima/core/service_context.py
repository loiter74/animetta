"""
服务上下文 - 核心服务容器
"""

from typing import Callable, Optional
from loguru import logger
from pathlib import Path
import yaml

from anima.services.audio import AudioProcessorInterface
from anima.services.audio.vad_audio_processor import VADAudioProcessor
from anima.config import AppConfig, ASRConfig, TTSConfig, AgentConfig, PersonaConfig, VADConfig
from anima.services import ASRInterface, TTSInterface, LLMInterface
from anima.services.speech.asr import ASRFactory
from anima.services.speech.tts import TTSFactory
from anima.services.intelligence.llm import LLMFactory
from anima.services.intelligence.vad import VADInterface, VADFactory
from anima.memory import MemorySystem


class ServiceContext:
    """服务上下文类"""

    def __init__(self):
        self.config: Optional[AppConfig] = None

        # 服务实例
        self.asr_engine: Optional[ASRInterface] = None
        self.tts_engine: Optional[TTSInterface] = None
        self.llm_engine: Optional[LLMInterface] = None
        self.local_llm_engine: Optional[LLMInterface] = None
        self.vad_engine: Optional[VADInterface] = None

        # 记忆系统
        self.audio_processor: Optional[AudioProcessorInterface] = None
        self.memory_system: Optional[MemorySystem] = None

        # 会话状态
        self.session_id: Optional[str] = None
        self.is_speaking: bool = False
        self.is_processing: bool = False

        # 回调函数
        self.send_text: Optional[Callable] = None

        # 表情分析器
        self.emotion_analyzer = None

    def __str__(self) -> str:
        return (
            f"ServiceContext(\n"
            f"  session_id={self.session_id},\n"
            f"  asr={type(self.asr_engine).__name__ if self.asr_engine else 'Not Loaded'},\n"
            f"  tts={type(self.tts_engine).__name__ if self.tts_engine else 'Not Loaded'},\n"
            f"  llm={type(self.llm_engine).__name__ if self.llm_engine else 'Not Loaded'},\n"
            f"  is_speaking={self.is_speaking},\n"
            f"  is_processing={self.is_processing}\n"
            f")"
        )

    # 初始化方法
    async def load_from_config(self, config: AppConfig) -> None:
        """从配置加载所有服务"""
        self.config = config
        logger.info(f"[{self.session_id}] 正在从配置加载服务...")

        await self.init_asr(config.asr)
        await self.init_tts(config.tts)
        await self.init_llm(config.agent, config.get_persona(), app_config=config)
        await self.init_local_llm(config.local_llm, app_config=config)
        await self.init_vad(config.vad)
        await self.init_audio_processor()
        await self.init_memory()
        await self.init_emotion_analyzer(config)

        logger.info(f"[{self.session_id}] 服务加载完成")

    async def load_cache(
        self,
        config: AppConfig,
        asr_engine: Optional[ASRInterface] = None,
        tts_engine: Optional[TTSInterface] = None,
        llm_engine: Optional[LLMInterface] = None,
        send_text: Optional[Callable] = None,
    ) -> None:
        """从缓存加载服务（复用已有实例）"""
        self.config = config
        self.asr_engine = asr_engine
        self.tts_engine = tts_engine
        self.llm_engine = llm_engine
        self.send_text = send_text
        logger.debug(f"[{self.session_id}] 从缓存加载服务上下文")

    async def init_asr(self, asr_config: ASRConfig) -> None:
        """初始化 ASR 服务"""
        if self.asr_engine is not None:
            logger.debug(f"[{self.session_id}] ASR 已初始化，跳过")
            return

        provider = asr_config.type
        model = getattr(asr_config, 'model', 'default')
        logger.info(f"[{self.session_id}] 初始化 ASR: {provider}/{model}")

        self.asr_engine = ASRFactory.create(
            provider=provider,
            api_key=getattr(asr_config, 'api_key', None),
            model=getattr(asr_config, 'model', 'whisper-1'),
            language=asr_config.language,
            base_url=getattr(asr_config, 'base_url', None),
            stream=getattr(asr_config, 'stream', False),
            device=getattr(asr_config, 'device', 'auto'),
            compute_type=getattr(asr_config, 'compute_type', 'default'),
            download_root=getattr(asr_config, 'download_root', None),
            beam_size=getattr(asr_config, 'beam_size', 5),
            vad_filter=getattr(asr_config, 'vad_filter', True),
            vad_parameters=getattr(asr_config, 'vad_parameters', {}),
            ncpu=getattr(asr_config, 'ncpu', 4),
            vad_model=getattr(asr_config, 'vad_model', None),
            punc_model=getattr(asr_config, 'punc_model', None),
            spk_model=getattr(asr_config, 'spk_model', None),
            hotword=getattr(asr_config, 'hotword', None),
            model_hub=getattr(asr_config, 'model_hub', 'ms'),
            disable_update=getattr(asr_config, 'disable_update', True),
        )

        if hasattr(self.asr_engine, 'preload'):
            logger.info(f"[{self.session_id}] 后台预加载 ASR 模型...")
            import asyncio
            asyncio.create_task(self._preload_asr_background())

    async def _preload_asr_background(self) -> None:
        """后台预加载 ASR 模型"""
        try:
            await self.asr_engine.preload()
            logger.info(f"[{self.session_id}] ASR 模型预加载完成")
        except Exception as e:
            logger.warning(f"[{self.session_id}] ASR 模型预加载失败: {e}")

    async def init_tts(self, tts_config: TTSConfig) -> None:
        """初始化 TTS 服务"""
        if self.tts_engine is not None:
            logger.debug(f"[{self.session_id}] TTS 已初始化，跳过")
            return

        provider = tts_config.type
        model = getattr(tts_config, 'model', 'default')
        logger.info(f"[{self.session_id}] 初始化 TTS: {provider}/{model}")

        self.tts_engine = TTSFactory.create(
            provider=provider,
            api_key=getattr(tts_config, 'api_key', None),
            model=getattr(tts_config, 'model', 'tts-1'),
            voice=getattr(tts_config, 'voice', 'alloy'),
            base_url=getattr(tts_config, 'base_url', None),
            response_format=getattr(tts_config, 'response_format', 'wav'),
            speed=getattr(tts_config, 'speed', 1.0),
            volume=getattr(tts_config, 'volume', 1.0)
        )

    async def init_llm(self, agent_config: AgentConfig, persona_config: PersonaConfig, app_config: AppConfig = None) -> None:
        """初始化 LLM 服务"""
        if self.llm_engine is not None:
            logger.debug(f"[{self.session_id}] LLM 已初始化，跳过")
            return

        llm_config = agent_config.llm_config
        logger.info(f"[{self.session_id}] 初始化 LLM: {llm_config.type}/{llm_config.model}")

        if app_config:
            live2d_prompt = self._get_live2d_prompt()
            system_prompt = app_config.get_system_prompt(live2d_prompt=live2d_prompt)
            persona_name = app_config.persona
            logger.info(f"[{self.session_id}] 使用人设: {persona_name}")
        else:
            system_prompt = self._build_system_prompt(agent_config, persona_config)

        self.llm_engine = LLMFactory.create_from_config(config=llm_config, system_prompt=system_prompt)
        logger.info(f"[{self.session_id}] LLM 创建完成: {type(self.llm_engine).__name__}")

    async def init_local_llm(self, llm_config, app_config: AppConfig = None) -> None:
        """初始化本地 LLM 服务（无 persona）"""
        if self.local_llm_engine is not None:
            logger.debug(f"[{self.session_id}] Local LLM 已初始化，跳过")
            return

        if llm_config is None:
            logger.info(f"[{self.session_id}] Local LLM 配置为空，跳过初始化")
            return

        logger.info(f"[{self.session_id}] 初始化本地LLM: {llm_config.type}/{llm_config.model}")
        self.local_llm_engine = LLMFactory.create_from_config(config=llm_config, system_prompt="")
        logger.info(f"[{self.session_id}] 本地LLM创建完成: {type(self.local_llm_engine).__name__}")

    def _get_live2d_prompt(self) -> Optional[str]:
        """获取 Live2D 表情提示词"""
        try:
            from anima.config.live2d import get_live2d_config
            from anima.avatar.prompts import EmotionPromptBuilder

            live2d_config = get_live2d_config()
            if not live2d_config.enabled:
                return None

            builder = EmotionPromptBuilder.from_config({"valid_emotions": live2d_config.valid_emotions})
            return builder.build_prompt()
        except Exception as e:
            logger.warning(f"获取 Live2D 提示词失败: {e}")
            return None

    def _build_system_prompt(self, agent_config: AgentConfig, persona_config: PersonaConfig) -> str:
        """构建系统提示词（备用方法）"""
        return persona_config.build_system_prompt()

    async def init_vad(self, vad_config: VADConfig) -> None:
        """初始化 VAD 服务"""
        if self.vad_engine is not None:
            logger.debug(f"[{self.session_id}] VAD 已初始化，跳过")
            return

        provider = vad_config.type
        logger.info(f"[{self.session_id}] 正在初始化 VAD 引擎: {provider}")

        try:
            self.vad_engine = VADFactory.create_from_config(vad_config)
            logger.info(f"[{self.session_id}] VAD 引擎创建成功: {type(self.vad_engine).__name__}")

            if hasattr(self.vad_engine, 'prob_threshold'):
                logger.info(f"[{self.session_id}] VAD 配置: "
                           f"prob_threshold={self.vad_engine.prob_threshold}, "
                           f"db_threshold={self.vad_engine.db_threshold}, "
                           f"required_hits={self.vad_engine.required_hits}, "
                           f"required_misses={self.vad_engine.required_misses}")
        except Exception as e:
            logger.error(f"[{self.session_id}] VAD 引擎创建失败: {e}")
            self.vad_engine = None

    async def init_audio_processor(self) -> None:
        """初始化音频处理器"""
        if hasattr(self, 'audio_processor') and self.audio_processor is not None:
            logger.debug(f"[{self.session_id}] AudioProcessor 已初始化，跳过")
            return
        if self.vad_engine is None:
            logger.debug(f"[{self.session_id}] 没有 VAD 引擎，跳过音频处理器初始化")
            return
        logger.debug(f"[{self.session_id}] 音频处理器将由 SessionManager 创建")

    async def init_memory(self) -> None:
        """初始化记忆系统"""
        try:
            memory_config_path = Path(__file__).parent.parent.parent / "config" / "features" / "memory.yaml"
            if not memory_config_path.exists():
                logger.info(f"[{self.session_id}] 记忆系统配置文件不存在: {memory_config_path}")
                return

            with open(memory_config_path, 'r', encoding='utf-8') as f:
                memory_config = yaml.safe_load(f)

            if not memory_config.get('memory', {}).get('enabled', False):
                logger.info(f"[{self.session_id}] 记忆系统未启用")
                return

            mem_cfg = memory_config['memory']
            config = {
                "workspace_dir": mem_cfg.get('workspace_dir', '~/.anima/workspace'),
                "short_term_max_turns": mem_cfg.get('short_term', {}).get('max_turns', 20),
            }

            embedding_cfg = mem_cfg.get('embedding', {})
            if embedding_cfg.get('model_name'):
                config['embedding_model'] = embedding_cfg['model_name']

            self.memory_system = MemorySystem(config)
            await self.memory_system.start()
            self.memory_system.sync()

            logger.info(f"[{self.session_id}] 记忆系统初始化完成")
            logger.info(f"[{self.session_id}] 工作目录: {config['workspace_dir']}")

        except Exception as e:
            logger.warning(f"[{self.session_id}] 记忆系统初始化失败: {e}")
            self.memory_system = None

    async def init_emotion_analyzer(self, config: AppConfig) -> None:
        """初始化表情分析器"""
        try:
            from anima.avatar.analyzers import EmotionAnalyzerFactory
            from anima.config.live2d import get_live2d_config

            live2d_config = get_live2d_config()
            if not live2d_config.enabled:
                logger.info(f"[{self.session_id}] Live2D 未启用，跳过表情分析器初始化")
                return

            self.emotion_analyzer = EmotionAnalyzerFactory.create(
                analyzer_type="keyword",
                valid_emotions=live2d_config.valid_emotions
            )
            logger.info(f"[{self.session_id}] 表情分析器初始化完成")

        except Exception as e:
            logger.warning(f"[{self.session_id}] 表情分析器初始化失败: {e}")
            self.emotion_analyzer = None

    # 生命周期管理
    async def close(self) -> None:
        """关闭并清理所有资源"""
        logger.info(f"[{self.session_id}] 正在关闭服务上下文...")

        if self.memory_system:
            await self.memory_system.stop()
            self.memory_system.close()
            self.memory_system = None
            logger.info(f"[{self.session_id}] 记忆系统已关闭")

        if self.asr_engine:
            await self.asr_engine.close()
            self.asr_engine = None
        if self.tts_engine:
            await self.tts_engine.close()
            self.tts_engine = None
        if self.llm_engine:
            await self.llm_engine.close()
            self.llm_engine = None
        if self.vad_engine:
            await self.vad_engine.close()
            self.vad_engine = None
        if hasattr(self, 'audio_processor') and self.audio_processor:
            if hasattr(self.audio_processor, 'reset'):
                self.audio_processor.reset()
            self.audio_processor = None

        logger.info(f"[{self.session_id}] 服务上下文已关闭")

    # 核心业务流程
    async def process_text_input(self, text: str) -> str:
        """处理文本输入"""
        if not self.llm_engine:
            raise RuntimeError("LLM 未初始化")
        self.is_processing = True
        try:
            response = await self.llm_engine.chat(text)
            return response
        finally:
            self.is_processing = False

    # 配置切换
    async def handle_config_switch(self, new_config: AppConfig) -> None:
        """处理配置切换"""
        logger.info(f"[{self.session_id}] 切换配置...")
        await self.close()
        await self.load_from_config(new_config)
        logger.info(f"[{self.session_id}] 配置切换完成")
