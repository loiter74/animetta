"""
Service context - core service container
"""

import asyncio
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
from anima.core.model_loading_manager import ModelLoadingManager


class ServiceContext:
    """Service context class"""

    def __init__(self, model_manager: Optional[ModelLoadingManager] = None):
        self.config: Optional[AppConfig] = None
        self.model_manager = model_manager

        # Service instances
        self.asr_engine: Optional[ASRInterface] = None
        self.tts_engine: Optional[TTSInterface] = None
        self.llm_engine: Optional[LLMInterface] = None
        self.local_llm_engine: Optional[LLMInterface] = None
        self.vad_engine: Optional[VADInterface] = None

        # Memory system
        self.audio_processor: Optional[AudioProcessorInterface] = None
        self.memory_system: Optional[MemorySystem] = None

        # Session state
        self.session_id: Optional[str] = None
        self.is_speaking: bool = False
        self.is_processing: bool = False

        # Callback functions
        self.send_text: Optional[Callable] = None

        # Emotion analyzer
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

    # Initialization methods
    async def load_from_config(self, config: AppConfig) -> None:
        """Load all services from config"""
        self.config = config
        logger.info(f"[{self.session_id}] Loading services from config...")

        await self.init_asr(config.asr)
        await self.init_tts(config.tts)
        await self.init_llm(config.agent, config.get_persona(), app_config=config)
        await self.init_local_llm(config.local_llm, app_config=config)
        await self.init_vad(config.vad)
        await self.init_audio_processor()
        await self.init_memory()
        await self.init_emotion_analyzer(config)

        # Preload conversation tokenizer to avoid download/load delay on first use
        await self._preload_tokenizers()

        # Trigger preload for all registered services via model manager
        if self.model_manager is not None:
            asyncio.create_task(self.model_manager.warmup())

        logger.info(f"[{self.session_id}] Services loaded")

    async def load_cache(
        self,
        config: AppConfig,
        asr_engine: Optional[ASRInterface] = None,
        tts_engine: Optional[TTSInterface] = None,
        llm_engine: Optional[LLMInterface] = None,
        send_text: Optional[Callable] = None,
    ) -> None:
        """Load services from cache (reuse existing instances)"""
        self.config = config
        self.asr_engine = asr_engine
        self.tts_engine = tts_engine
        self.llm_engine = llm_engine
        self.send_text = send_text
        logger.debug(f"[{self.session_id}] Loading service context from cache")

    async def init_asr(self, asr_config: ASRConfig) -> None:
        """Initialize ASR service"""
        if self.asr_engine is not None:
            logger.debug(f"[{self.session_id}] ASR already initialized, skipping")
            return

        provider = asr_config.type
        model = getattr(asr_config, 'model', 'default')
        logger.info(f"[{self.session_id}] Initializing ASR: {provider}/{model}")

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

        if hasattr(self.asr_engine, 'preload') and self.model_manager is not None:
            self.model_manager.register("asr", self.asr_engine.preload, "asr")

    async def _preload_tokenizers(self) -> None:
        """Preload conversation tokenizer (tiktoken, etc.) to avoid download/load delay on first use"""
        try:
            import tiktoken
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: tiktoken.get_encoding("cl100k_base"))
            logger.info(f"[{self.session_id}] tiktoken tokenizer preloaded")
        except ImportError:
            logger.debug(f"[{self.session_id}] tiktoken not installed, skipping preload")
        except Exception as e:
            logger.warning(f"[{self.session_id}] Tokenizer preload failed (does not affect operation): {e}")

    async def init_tts(self, tts_config: TTSConfig) -> None:
        """Initialize TTS service"""
        if self.tts_engine is not None:
            logger.debug(f"[{self.session_id}] TTS already initialized, skipping")
            return

        provider = tts_config.type
        model = getattr(tts_config, 'model', 'default')
        logger.info(f"[{self.session_id}] Initializing TTS: {provider}/{model}")

        # Convert the config object to dict and pass all fields to factory
        # This ensures provider-specific params (ref_audio_path, prompt_text, etc.)
        # are forwarded properly, not just the generic ones.
        tts_kwargs = {"provider": provider}
        # Try model_dump() for Pydantic v2 configs, fall back to manual field extraction
        if hasattr(tts_config, 'model_dump'):
            cfg_dict = tts_config.model_dump(exclude={'type'})
            tts_kwargs.update(cfg_dict)
        else:
            # Manual extraction for non-standard configs
            for field in ['api_key', 'model', 'voice', 'base_url', 'response_format',
                          'speed', 'volume', 'ref_audio_path', 'prompt_text',
                          'prompt_lang', 'text_lang', 'top_k', 'top_p', 'temperature',
                          'media_type', 'streaming_mode', 'text_split_method',
                          'sample_steps', 'seed']:
                val = getattr(tts_config, field, None)
                if val is not None:
                    tts_kwargs[field] = val
        self.tts_engine = TTSFactory.create(**tts_kwargs)

        if hasattr(self.tts_engine, 'preload') and self.model_manager is not None:
            self.model_manager.register("tts", self.tts_engine.preload, "tts")

    async def init_llm(self, agent_config: AgentConfig, persona_config: PersonaConfig, app_config: AppConfig = None) -> None:
        """Initialize LLM service"""
        if self.llm_engine is not None:
            logger.debug(f"[{self.session_id}] LLM already initialized, skipping")
            return

        llm_config = agent_config.llm_config
        logger.info(f"[{self.session_id}] Initializing LLM: {llm_config.type}/{llm_config.model}")

        if app_config:
            live2d_prompt = self._get_live2d_prompt()
            system_prompt = app_config.get_system_prompt(live2d_prompt=live2d_prompt)
            persona_name = app_config.persona
            logger.info(f"[{self.session_id}] Using persona: {persona_name}")
        else:
            system_prompt = self._build_system_prompt(agent_config, persona_config)

        self.llm_engine = LLMFactory.create_from_config(config=llm_config, system_prompt=system_prompt)
        logger.info(f"[{self.session_id}] LLM created: {type(self.llm_engine).__name__}")

        if hasattr(self.llm_engine, 'preload') and self.model_manager is not None:
            self.model_manager.register("llm", self.llm_engine.preload, "llm")

    async def init_local_llm(self, llm_config, app_config: AppConfig = None) -> None:
        """Initialize local LLM service (no persona)"""
        if self.local_llm_engine is not None:
            logger.debug(f"[{self.session_id}] Local LLM already initialized, skipping")
            return

        if llm_config is None:
            logger.info(f"[{self.session_id}] Local LLM config is empty, skipping initialization")
            return

        logger.info(f"[{self.session_id}] Initializing local LLM: {llm_config.type}/{llm_config.model}")
        self.local_llm_engine = LLMFactory.create_from_config(config=llm_config, system_prompt="")
        logger.info(f"[{self.session_id}] Local LLM created: {type(self.local_llm_engine).__name__}")

    def _get_live2d_prompt(self) -> Optional[str]:
        """Get Live2D emotion prompt"""
        try:
            from anima.config.live2d import get_live2d_config
            from anima.avatar.prompts import EmotionPromptBuilder

            live2d_config = get_live2d_config()
            if not live2d_config.enabled:
                return None

            builder = EmotionPromptBuilder.from_config({"valid_emotions": live2d_config.valid_emotions})
            return builder.build_prompt()
        except Exception as e:
            logger.warning(f"Failed to get Live2D prompt: {e}")
            return None

    def _build_system_prompt(self, agent_config: AgentConfig, persona_config: PersonaConfig) -> str:
        """Build system prompt (fallback method)"""
        return persona_config.build_system_prompt()

    async def init_vad(self, vad_config: VADConfig) -> None:
        """Initialize VAD service"""
        if self.vad_engine is not None:
            logger.debug(f"[{self.session_id}] VAD already initialized, skipping")
            return

        provider = vad_config.type
        logger.info(f"[{self.session_id}] Initializing VAD engine: {provider}")

        try:
            self.vad_engine = VADFactory.create_from_config(vad_config)
            logger.info(f"[{self.session_id}] VAD engine created: {type(self.vad_engine).__name__}")

            if hasattr(self.vad_engine, 'preload') and self.model_manager is not None:
                self.model_manager.register("vad", self.vad_engine.preload, "vad")

            if hasattr(self.vad_engine, 'prob_threshold'):
                logger.info(f"[{self.session_id}] VAD config: "
                           f"prob_threshold={self.vad_engine.prob_threshold}, "
                           f"db_threshold={self.vad_engine.db_threshold}, "
                           f"required_hits={self.vad_engine.required_hits}, "
                           f"required_misses={self.vad_engine.required_misses}")
        except Exception as e:
            logger.error(f"[{self.session_id}] VAD engine creation failed: {e}")
            self.vad_engine = None

    async def init_audio_processor(self) -> None:
        """Initialize audio processor"""
        if hasattr(self, 'audio_processor') and self.audio_processor is not None:
            logger.debug(f"[{self.session_id}] AudioProcessor already initialized, skipping")
            return
        if self.vad_engine is None:
            logger.debug(f"[{self.session_id}] No VAD engine, skipping audio processor initialization")
            return
        logger.debug(f"[{self.session_id}] Audio processor will be created by SessionManager")

    async def init_memory(self) -> None:
        """Initialize memory system"""
        try:
            memory_config_path = Path(__file__).parent.parent.parent.parent / "config" / "features" / "memory.yaml"
            if not memory_config_path.exists():
                logger.info(f"[{self.session_id}] Memory system config file not found: {memory_config_path}")
                return

            with open(memory_config_path, 'r', encoding='utf-8') as f:
                memory_config = yaml.safe_load(f)

            if not memory_config.get('memory', {}).get('enabled', False):
                logger.info(f"[{self.session_id}] Memory system not enabled")
                return

            mem_cfg = memory_config['memory']
            config = {
                "workspace_dir": mem_cfg.get('workspace_dir', '~/.anima/workspace'),
                "short_term_max_turns": mem_cfg.get('short_term', {}).get('max_turns', 20),
                # Forward search configuration (hybrid weights, defaults from MemoryConfig)
                "search": mem_cfg.get('search', {}),
                # Forward chunk configuration (token/overlap settings)
                "chunk": mem_cfg.get('chunk', {}),
            }

            embedding_cfg = mem_cfg.get('embedding', {})
            if embedding_cfg.get('model_name'):
                config['embedding_model'] = embedding_cfg['model_name']

            self.memory_system = MemorySystem(config)
            await self.memory_system.start()
            self.memory_system.sync()

            logger.info(f"[{self.session_id}] Memory system initialized")
            logger.info(f"[{self.session_id}] Workspace directory: {config['workspace_dir']}")

        except Exception as e:
            logger.warning(f"[{self.session_id}] Memory system initialization failed: {e}")
            self.memory_system = None

    async def init_emotion_analyzer(self, config: AppConfig) -> None:
        """Initialize emotion analyzer"""
        try:
            from anima.avatar.factory import EmotionAnalyzerFactory
            from anima.config.live2d import get_live2d_config

            live2d_config = get_live2d_config()
            if not live2d_config.enabled:
                logger.info(f"[{self.session_id}] Live2D not enabled, skipping emotion analyzer initialization")
                return

            self.emotion_analyzer = EmotionAnalyzerFactory.create(
                name="keyword_analyzer",
                config={"valid_emotions": live2d_config.valid_emotions}
            )
            logger.info(f"[{self.session_id}] Emotion analyzer initialized")

        except Exception as e:
            logger.warning(f"[{self.session_id}] Emotion analyzer initialization failed: {e}")
            self.emotion_analyzer = None

    # Lifecycle management
    async def close(self) -> None:
        """Close and clean up all resources"""
        logger.info(f"[{self.session_id}] Shutting down service context...")

        if self.memory_system:
            await self.memory_system.stop()
            self.memory_system.close()
            self.memory_system = None
            logger.info(f"[{self.session_id}] Memory system closed")

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

        logger.info(f"[{self.session_id}] Service context closed")

    # Core business flow
    async def process_text_input(self, text: str) -> str:
        """Process text input"""
        if not self.llm_engine:
            raise RuntimeError("LLM not initialized")
        self.is_processing = True
        try:
            response = await self.llm_engine.chat(text)
            return response
        finally:
            self.is_processing = False

    # Configuration switching
    async def handle_config_switch(self, new_config: AppConfig) -> None:
        """Handle configuration switch"""
        logger.info(f"[{self.session_id}] Switching configuration...")
        await self.close()
        await self.load_from_config(new_config)
        logger.info(f"[{self.session_id}] Configuration switch complete")
