"""Application-owned shared provider engines.

Each ProviderPool owns LLM/TTS/ASR construction, readiness and shutdown.
Sessions borrow these engines and release only their own resources.
ServicePool remains a stateless compatibility facade for legacy callers.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger

from .session_context import ServiceContext

if TYPE_CHECKING:
    from animetta.config.manifest import EffectiveConfig
    from animetta.observability.ports import ObservationRecorder

    from .model_loading import ModelLoadingManager
    from .readiness import RuntimeReadinessSnapshot


class ProviderPool:
    """Application-owned LLM/TTS/ASR engines and lifecycle state."""

    def __init__(self) -> None:
        self._llm: Any | None = None
        self._tts: Any | None = None
        self._asr: Any | None = None
        self._ready: bool = False
        self._ctx: Any | None = None
        self._runtime_config: Any | None = None
        self._model_manager: Any | None = None
        self._init_state: str = "pending"
        self._init_error: str | None = None
        self._initializing_task: asyncio.Task[None] | None = None
        self._shutdown_task: asyncio.Task[None] | None = None
        self._shutdown_requested: bool = False
        self._shutdown_errors: tuple[str, ...] = ()
        self._resolved_identities: dict[str, dict[str, str | None]] = {}
        self._llm_connectivity: dict[str, Any] = {
            "state": "pending",
            "ready": False,
            "reason": None,
        }

    # ── Lifecycle ──────────────────────────────────────────

    async def init(
        self,
        config: EffectiveConfig,
        model_manager: ModelLoadingManager | None = None,
        observation_recorder: ObservationRecorder | None = None,
    ) -> None:
        """Initialize once; concurrent callers await the same lifecycle task."""
        if self._init_state == "closed" and (
            self._shutdown_task is None or self._shutdown_task.done()
        ):
            self._init_state = "pending"
            self._shutdown_task = None
            self._shutdown_requested = False
        if self._shutdown_requested or self._init_state == "closing":
            raise RuntimeError("ServicePool shutdown is in progress")

        current_task = asyncio.current_task()
        existing_task = self._initializing_task
        if (
            existing_task is not None
            and existing_task is not current_task
            and not existing_task.done()
        ):
            await asyncio.shield(existing_task)
            return

        if self._ready:
            logger.debug("[ServicePool] Already initialized")
            return
        if self._init_state == "ready" and (
            self._ctx is not None
            or self._llm is not None
            or self._tts is not None
            or self._asr is not None
        ):
            logger.debug("[ServicePool] Already initialized")
            return
        if self._init_state in {"loading", "failed"}:
            raise RuntimeError(
                "ServicePool initialization is not retryable; "
                "perform explicit shutdown before retry"
            )

        self._initializing_task = current_task
        try:
            await self._init_once(
                config,
                model_manager=model_manager,
                observation_recorder=observation_recorder,
            )
        finally:
            if self._initializing_task is current_task:
                self._initializing_task = None

    async def _init_once(
        self,
        config: EffectiveConfig,
        model_manager: ModelLoadingManager | None = None,
        observation_recorder: ObservationRecorder | None = None,
    ) -> None:
        """Create all shareable engines from *config* and keep them alive.

        Spawns a temporary ServiceContext, loads all services, then
        extracts LLM/TTS/ASR and discards the per-session services
        (VAD, Memory).
        """
        import time as _time

        t0 = _time.perf_counter()
        logger.info("[ServicePool] Initializing shared service instances...")
        self._runtime_config = config
        self._model_manager = model_manager
        self._init_state = "loading"
        self._init_error = None
        self._llm_connectivity = {
            "state": "pending",
            "ready": False,
            "reason": None,
        }
        self._ready = False
        self._resolved_identities = {}

        if observation_recorder is None:
            ctx = ServiceContext(model_manager=model_manager)
        else:
            ctx = ServiceContext(
                model_manager=model_manager,
                observation_recorder=observation_recorder,
            )
        ctx.session_id = "__pool__"
        try:
            await ctx.load_from_config(config, initialize_memory=False)
            self._llm = ctx.llm_engine
            self._tts = ctx.tts_engine
            self._asr = ctx.asr_engine
            self._ctx = ctx
            vad_engine = ctx.vad_engine

            # Close per-session services — they are NOT shared.
            if ctx.vad_engine is not None:
                await ctx.vad_engine.close()
                ctx.vad_engine = None
            if ctx.memory_system is not None:
                await ctx.memory_system.shutdown()
                ctx.memory_system = None
            if ctx.emotion_analyzer is not None:
                ctx.emotion_analyzer = None
            if ctx.audio_processor is not None:
                ctx.audio_processor = None

            profile = self._runtime_profile(config)
            strict_runtime = profile in {"smoke", "selftest", "production", "golden"}
            if strict_runtime:
                # ServiceContext registers preload functions before returning.
                # Await a post-registration pass even though the ASGI bootstrap
                # also launches an intentionally early, possibly empty warmup.
                if model_manager is not None:
                    await model_manager.warmup()

                try:
                    self._llm_connectivity = dict(await ctx.wait_for_llm_connectivity())
                except Exception:
                    self._llm_connectivity = {
                        "state": "failed",
                        "ready": False,
                        "reason": "request_failed",
                    }
            else:
                self._llm_connectivity = dict(
                    getattr(
                        ctx,
                        "llm_connectivity_status",
                        {"state": "pending", "ready": False, "reason": None},
                    )
                )

            if hasattr(config, "providers"):
                from .readiness import resolve_service_identity

                engines = {
                    "llm": self._llm,
                    "asr": self._asr,
                    "tts": self._tts,
                    "vad": vad_engine,
                }
                self._resolved_identities = {
                    category: identity
                    for category, engine in engines.items()
                    if (
                        identity := resolve_service_identity(
                            category,
                            engine,
                            config.providers[category],
                        )
                    )
                    is not None
                }

            # Engine construction has reached a terminal state.  Golden
            # readiness is computed from the real provider, connectivity, and
            # preload caches; development retains explicit-mock behavior.
            if self._shutdown_requested:
                raise asyncio.CancelledError
            self._init_state = "ready"
            self._ready = self._compute_engine_readiness()

            elapsed = (_time.perf_counter() - t0) * 1000
            if self._ready:
                logger.info(f"[ServicePool] Ready ({elapsed:.0f}ms) — shared LLM/TTS/ASR")
            else:
                logger.warning("[ServicePool] Shared engines initialized but readiness is pending")
        except asyncio.CancelledError:
            logger.warning("[ServicePool] Initialization cancelled")
            await self._abort_initialization(ctx, "initialization_cancelled")
            raise
        except Exception as exc:
            logger.error(
                "[ServicePool] Initialization failed: {}",
                type(exc).__name__,
            )
            await self._abort_initialization(ctx, "initialization_failed")
            raise

    def configure_runtime(self, config: Any, model_manager: Any | None = None) -> None:
        """Register the effective profile before background initialization starts."""
        if self._init_state not in {"closing"}:
            self._runtime_config = config
            if model_manager is not None:
                self._model_manager = model_manager
        if self._init_state in {"pending", "closed"} and self._ctx is None:
            self._model_manager = model_manager
            if self._init_state == "closed":
                self._init_state = "pending"
                self._shutdown_task = None
                self._shutdown_requested = False

    def get_context(self) -> dict[str, Any]:
        """Return a dict of shareable engines for ``ServiceContext.load_cache()``.

        Development callers receive an empty dict while the pool is unavailable.
        Golden callers fail closed so they cannot allocate a second engine set.
        """
        if not self.is_ready():
            if self._runtime_profile(self._runtime_config) in {
                "smoke",
                "selftest",
                "production",
                "golden",
            }:
                raise RuntimeError(
                    "Real-profile ServicePool is not ready; refusing per-session engine initialization"
                )
            return {}
        return {
            "llm_engine": self._llm,
            "tts_engine": self._tts,
            "asr_engine": self._asr,
        }

    def apply_llm_config(self, llm_config: Any, system_prompt: str | None = None) -> None:
        """Apply lightweight LLM config and prompt updates to the pooled engine."""
        if self._llm is None:
            return
        from animetta.services.runtime_config import apply_runtime_llm_config

        apply_runtime_llm_config(self._llm, llm_config, system_prompt)

    async def shutdown(self) -> None:
        """Await one shielded, application-owned best-effort shutdown operation."""
        existing = self._shutdown_task
        if self._init_state == "closed" and existing is not None and existing.done():
            await asyncio.shield(existing)
            return

        # Atomic lifecycle gate: no await is allowed before every readiness
        # signal becomes non-ready and late initialization is forbidden.
        self._shutdown_requested = True
        self._ready = False
        self._init_state = "closing"
        self._llm_connectivity = {
            "state": "pending",
            "ready": False,
            "reason": None,
        }

        if existing is None:
            existing = asyncio.create_task(self._shutdown_once())
            self._shutdown_task = existing
        await asyncio.shield(existing)

    async def _shutdown_once(self) -> None:
        """Close shared resources once and always clear lifecycle references."""
        initializing_task = self._initializing_task
        current_task = asyncio.current_task()
        errors: list[str] = []
        try:
            if (
                initializing_task is not None
                and initializing_task is not current_task
                and not initializing_task.done()
            ):
                initializing_task.cancel()
                await asyncio.gather(
                    initializing_task,
                    return_exceptions=True,
                )

            if any(engine is not None for engine in (self._llm, self._tts, self._asr)):
                logger.info("[ServicePool] Shutting down shared instances...")

            context = self._ctx
            try:
                if context is not None:
                    await context.close_session_resources()
            except asyncio.CancelledError:
                errors.append("context:CancelledError")
            except Exception as exc:
                errors.append(f"context:{type(exc).__name__}")

            seen: set[int] = set()
            for name, engine in (
                ("llm", self._llm),
                ("tts", self._tts),
                ("asr", self._asr),
            ):
                if engine is None or id(engine) in seen:
                    continue
                seen.add(id(engine))
                try:
                    await engine.close()
                except asyncio.CancelledError:
                    errors.append(f"{name}:CancelledError")
                except Exception as exc:
                    errors.append(f"{name}:{type(exc).__name__}")
        finally:
            self._ready = False
            self._llm = None
            self._tts = None
            self._asr = None
            self._ctx = None
            self._runtime_config = None
            self._model_manager = None
            self._init_state = "closed"
            self._init_error = None
            self._initializing_task = None
            self._shutdown_requested = False
            self._shutdown_errors = tuple(errors)
            self._resolved_identities = {}
            self._llm_connectivity = {
                "state": "pending",
                "ready": False,
                "reason": None,
            }
            if errors:
                logger.warning(
                    "[ServicePool] Shutdown completed with cleanup errors: {}",
                    ",".join(errors),
                )
            else:
                logger.info("[ServicePool] Shut down")

    def is_ready(self) -> bool:
        self._ready = self._compute_engine_readiness()
        return self._ready

    def get_readiness_snapshot(
        self,
        *,
        config: Any | None = None,
        model_manager: Any | None = None,
        frontend: Any | None = None,
    ) -> RuntimeReadinessSnapshot:
        """Return the cached, content-free runtime readiness snapshot."""
        from .readiness import build_runtime_readiness_snapshot

        active_config = config if config is not None else self._runtime_config
        active_manager = model_manager if model_manager is not None else self._model_manager
        frontend_status = frontend or {
            "state": "failed",
            "ready": False,
            "reason": "frontend_state_unavailable",
        }
        return build_runtime_readiness_snapshot(
            config=active_config,
            llm_engine=self._llm,
            tts_engine=self._tts,
            model_manager=active_manager,
            init_state=self._init_state,
            init_reason=self._init_error,
            connectivity=self._llm_connectivity,
            frontend=frontend_status,
            development_ready=self._ready,
            pool_config=self._runtime_config,
            resolved_identities=self._resolved_identities,
        )

    def _compute_engine_readiness(self) -> bool:
        """Evaluate cached engine readiness without frontend policy or I/O."""
        if self._shutdown_requested or self._init_state in {"closing", "closed"}:
            return False
        profile = self._runtime_profile(self._runtime_config)
        if profile not in {"smoke", "selftest", "production", "golden"}:
            return self._ready or (
                self._init_state == "ready" and self._llm is not None and self._tts is not None
            )
        snapshot = self.get_readiness_snapshot(
            frontend={"state": "ready", "ready": True, "reason": None},
        )
        return bool(snapshot.components.get("pool", {}).get("ready"))

    @staticmethod
    def _runtime_profile(config: Any | None) -> str:
        direct = getattr(config, "profile", None)
        if direct in {"test", "smoke", "selftest", "production"}:
            return direct
        try:
            profile = config.system.runtime_profile
        except Exception:
            return "development"
        return (
            profile
            if profile in {"development", "test", "smoke", "selftest", "production", "golden"}
            else "development"
        )

    async def _abort_initialization(self, ctx: Any, reason: str) -> None:
        """Best-effort cleanup for failed or cancelled initialization."""
        errors: list[str] = []
        try:
            await ctx.close_session_resources()
        except asyncio.CancelledError:
            errors.append("context:CancelledError")
        except Exception as exc:
            errors.append(f"context:{type(exc).__name__}")

        candidates = (
            ("llm", getattr(ctx, "llm_engine", None)),
            ("tts", getattr(ctx, "tts_engine", None)),
            ("asr", getattr(ctx, "asr_engine", None)),
            ("llm", self._llm),
            ("tts", self._tts),
            ("asr", self._asr),
        )
        seen: set[int] = set()
        for name, engine in candidates:
            if engine is None or id(engine) in seen:
                continue
            seen.add(id(engine))
            try:
                await engine.close()
            except asyncio.CancelledError:
                errors.append(f"{name}:CancelledError")
            except Exception as exc:
                errors.append(f"{name}:{type(exc).__name__}")

        for attr in ("llm_engine", "tts_engine", "asr_engine"):
            setattr(ctx, attr, None)
        self._llm = self._tts = self._asr = None
        self._ctx = None
        self._ready = False
        if self._shutdown_requested:
            self._init_state = "closing"
            self._init_error = None
        else:
            self._init_state = "failed"
            self._init_error = reason
        self._shutdown_errors = tuple(errors)
        if errors:
            logger.warning(
                "[ServicePool] Initialization cleanup errors: {}",
                ",".join(errors),
            )


default_provider_pool = ProviderPool()


class ServicePool:
    """One-release stateless compatibility facade for legacy imports."""

    @staticmethod
    async def init(
        config: EffectiveConfig,
        model_manager: ModelLoadingManager | None = None,
        observation_recorder: ObservationRecorder | None = None,
    ) -> None:
        await default_provider_pool.init(config, model_manager, observation_recorder)

    @staticmethod
    def configure_runtime(config: Any, model_manager: Any | None = None) -> None:
        default_provider_pool.configure_runtime(config, model_manager)

    @staticmethod
    def get_context() -> dict[str, Any]:
        return default_provider_pool.get_context()

    @staticmethod
    def apply_llm_config(llm_config: Any, system_prompt: str | None = None) -> None:
        default_provider_pool.apply_llm_config(llm_config, system_prompt)

    @staticmethod
    async def shutdown() -> None:
        await default_provider_pool.shutdown()

    @staticmethod
    def is_ready() -> bool:
        return default_provider_pool.is_ready()

    @staticmethod
    def get_readiness_snapshot(
        *,
        config: Any | None = None,
        model_manager: Any | None = None,
        frontend: Any | None = None,
    ) -> RuntimeReadinessSnapshot:
        return default_provider_pool.get_readiness_snapshot(
            config=config,
            model_manager=model_manager,
            frontend=frontend,
        )


__all__ = ["ProviderPool", "ServicePool", "default_provider_pool"]
