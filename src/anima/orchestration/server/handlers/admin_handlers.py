"""
Admin/shared handlers — lifecycle, configuration, memory, meme, persona.

Contains the shared utility methods that other handler modules
depend on (_get_or_create_orchestrator, broadcast_to_desktop_clients, etc.).
"""

import json
import time
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING

from loguru import logger

from anima.orchestration.graph.translation_state import translation_state

if TYPE_CHECKING:
    from socketio import AsyncServer
    from ..session import SessionManager
    from ..desktop import DesktopClientManager
    from ..live2d import Live2DManager


class AdminHandlers:
    """Admin and shared infrastructure handlers.

    Owns session lifecycle, configuration, memory organization,
    persona switching, meme pool management, and shared utilities
    that other handler modules call via the `admin` reference.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: "DesktopClientManager",
        live2d_manager: "Live2DManager",
    ):
        self.sio = sio
        self.session_manager = session_manager
        self.desktop_manager = desktop_manager
        self.live2d_manager = live2d_manager

        self.global_config = None
        self.user_settings = None

    # ── Config setters ───────────────────────────────────────────────

    def set_global_config(self, config) -> None:
        """Set global config (delegated from RouteHandlers)."""

    def set_user_settings(self, user_settings) -> None:
        """Set user settings (delegated from RouteHandlers)."""
        self.user_settings = user_settings

    # ── Shared utilities ─────────────────────────────────────────────

    def _make_send_callback(self, sid: str):
        """Create a send callback for the orchestrator."""

        async def send_callback(data):
            if isinstance(data, str):
                data = json.loads(data)
            event_type = data.get("type", "message")
            await self.sio.emit(event_type, data, to=sid)

        return send_callback

    async def _get_or_create_orchestrator(self, sid: str):
        """Get or create LangGraph orchestrator for a session."""
        from anima.config import AppConfig
        from anima.config.live2d import get_live2d_config

        config = self.global_config or AppConfig.load()
        send_callback = self._make_send_callback(sid)

        ctx = await self.session_manager.get_or_create_context(
            sid, config, send_callback
        )

        live2d_config = get_live2d_config()

        orchestrator = await self.session_manager.get_or_create_orchestrator(
            sid,
            ctx,
            send_callback,
            live2d_config,
            socketio=self.sio,
        )

        await self.session_manager.get_or_create_audio_processor(sid, ctx)

        return orchestrator

    async def broadcast_to_desktop_clients(
        self, client_type: str, event: str, data: dict
    ) -> None:
        """Broadcast message to desktop clients of a specified type."""
        sids = self.desktop_manager.get_clients_by_type(client_type)
        for sid in sids:
            await self.sio.emit(event, data, to=sid)

    # ── Connection events ────────────────────────────────────────────

    async def on_connect(self, sid: str, environ: dict) -> None:
        """Client connection event."""
        client_type = environ.get("HTTP_USER_AGENT", "")
        is_electron = "electron" in client_type.lower()

        print(f"\n{'=' * 60}")
        print(f"[OK] Client connected: {sid}")
        print(f"     Type: {'Electron' if is_electron else 'Web'}")
        print(f"{'=' * 60}\n")
        logger.info(
            f"Client connected: {sid} (Type: {'Electron' if is_electron else 'Web'})"
        )

        await self.sio.save_session(
            sid, {"connected_at": time.time(), "is_electron": is_electron}
        )

        await self.sio.emit(
            "connection-established",
            {
                "message": "Connection successful",
                "sid": sid,
                "server_time": asyncio.get_event_loop().time(),
            },
            to=sid,
        )

        # OTel metrics: active sessions gauge
        try:
            from anima.tracing.metrics import get_active_sessions

            g = get_active_sessions()
            if g is not None:
                g.add(1)
        except Exception:
            pass

        if not is_electron:
            await self.sio.emit(
                "control", {"type": "control", "text": "start-mic"}, to=sid
            )
            print(f"[OK] Sent start-mic signal to client {sid}")

    async def on_disconnect(self, sid: str) -> None:
        """Client disconnect event."""
        logger.info(f"Client disconnected: {sid}")
        self.desktop_manager.unregister(sid)
        await self.session_manager.cleanup_session(sid)

        # OTel metrics: active sessions gauge
        try:
            from anima.tracing.metrics import get_active_sessions

            g = get_active_sessions()
            if g is not None:
                g.add(-1)
        except Exception:
            pass

    # ── Config events ─────────────────────────────────────────────────

    async def on_switch_config(self, sid: str, data: dict) -> None:
        """Switch config."""
        config_name = data.get("file", "default")
        logger.info(f"[{sid}] Switching config: {config_name}")

        try:
            if sid in self.session_manager.orchestrators:
                del self.session_manager.orchestrators[sid]

            await self.sio.emit(
                "config-switched",
                {
                    "type": "config-switched",
                    "message": f"Switched to config: {config_name}",
                },
                to=sid,
            )

        except Exception as e:
            logger.error(f"[{sid}] Error switching config: {e}")
            await self.sio.emit("error", {"type": "error", "message": str(e)}, to=sid)

    async def on_set_log_level(self, sid: str, data: dict) -> None:
        """Set backend log level."""
        from anima.utils.logger_manager import logger_manager

        level = data.get("level", "INFO").upper()
        logger.info(f"[{sid}] Requested to set log level to: {level}")

        success = logger_manager.set_level(level)

        if success and self.user_settings:
            self.user_settings.set_log_level(level)

        await self.sio.emit(
            "log_level_changed",
            {
                "type": "log_level_changed",
                "success": success,
                "level": logger_manager.get_level(),
                "message": f"Log level set to {logger_manager.get_level()}"
                if success
                else "Setting failed",
            },
            to=sid,
        )

    async def on_get_config(self, sid: str, data: dict) -> None:
        """Return current config (sanitized) to frontend."""
        logger.info(f"[{sid}] Requested config data")
        from anima.config.app import AppConfig
        from anima.config.live2d import Live2DConfig
        import os

        config = self.global_config or AppConfig.load()

        # Read available personas from filesystem
        personas_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "config",
            "personas",
        )
        available_personas = []
        if os.path.isdir(personas_dir):
            available_personas = sorted(
                [
                    f.replace(".yaml", "")
                    for f in os.listdir(personas_dir)
                    if f.endswith(".yaml")
                ]
            )

        # Read live2d config
        try:
            live2d_cfg = Live2DConfig.load()
            live2d_model_path = live2d_cfg.model.path
        except Exception:
            live2d_model_path = "/live2d/haru/haru_greeter_t03.model3.json"

        # Build safe config (NO api keys, NO secrets)
        config_data = {
            "persona": config.persona,
            "services": {
                "asr": config.services.asr,
                "tts": config.services.tts,
                "agent": config.services.agent,
                "vad": config.services.vad,
            },
            "active_services": {
                "asr": config.asr.type if config.asr else None,
                "tts": config.tts.type if config.tts else None,
                "llm": config.agent.llm_config.type
                if config.agent and config.agent.llm_config
                else None,
                "vad": config.vad.type if config.vad else None,
            },
            "system": {
                "host": config.system.host,
                "port": config.system.port,
                "log_level": config.system.log_level,
            },
            "live2d": {
                "model_path": live2d_model_path,
                "enabled": True,
            },
            "available_personas": available_personas,
        }
        await self.sio.emit("config_data", config_data, to=sid)

    # ── Heartbeat ──────────────────────────────────────────────────────

    async def on_heartbeat(self, sid: str, data: dict) -> None:
        """Heartbeat check."""
        await self.sio.emit("heartbeat-ack", {}, to=sid)

    # ── Translation events ────────────────────────────────────────────

    async def on_translation_configure(self, sid: str, data: dict) -> None:
        """Update translation configuration at runtime."""
        target_language = data.get("target_language")
        if target_language:
            translation_state.target_language = target_language
            logger.info(
                f"[{sid}] Translation target language updated to: {target_language}"
            )
            await self.sio.emit(
                "translation.status",
                {
                    "target_language": translation_state.target_language,
                    "enabled": translation_state.enabled,
                },
                to=sid,
            )
        else:
            await self.sio.emit(
                "translation.status",
                {
                    "target_language": translation_state.target_language,
                    "enabled": translation_state.enabled,
                },
                to=sid,
            )

    # ── Memory: Wiki Pages ─────────────────────────────────────────────

    async def on_get_wiki_pages(self, sid: str, data: dict) -> dict:
        """获取 wiki 页面列表"""
        try:
            # Try session-level memory_system
            ctx = self.session_manager.get_context(sid)
            if (
                ctx
                and ctx.memory_system
                and hasattr(ctx.memory_system, "_wiki_manager")
            ):
                wiki = ctx.memory_system._wiki_manager
                pages = []
                for rel in wiki.list_pages():
                    page = wiki.read_page(rel)
                    if page:
                        pages.append(
                            {
                                "path": page.path,
                                "title": page.title,
                                "page_type": page.page_type.value,
                                "content": page.content[:200],
                                "tags": page.tags,
                                "updated_at": page.updated_at.isoformat()
                                if page.updated_at
                                else "",
                            }
                        )
                logger.info(f"[{sid}] Wiki pages (from memory): {len(pages)}")
                return {"pages": pages}

            # Fallback: read wiki files directly from workspace
            from pathlib import Path

            workspace = Path("./memory_db")
            wiki_dir = workspace / "wiki"
            if not wiki_dir.exists():
                return {"pages": []}

            pages = []
            TYPE_MAP = {
                "entities": "entity",
                "concepts": "concept",
                "sources": "source",
                "synthesis": "synthesis",
                "memes": "meme",
            }
            for md_file in sorted(wiki_dir.rglob("*.md")):
                rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
                content = md_file.read_text(encoding="utf-8")[:500]
                title = md_file.stem
                parent = md_file.parent.name if md_file.parent != wiki_dir else "source"
                pages.append(
                    {
                        "path": rel,
                        "title": title,
                        "page_type": TYPE_MAP.get(parent, parent),
                        "content": content,
                        "tags": [],
                        "updated_at": str(Path(md_file).stat().st_mtime),
                    }
                )
            logger.info(
                f"[{sid}] Wiki pages (from disk): {len(pages)} pages, "
                f"types={list(set(p['page_type'] for p in pages))}"
            )
            return {"pages": pages}
        except Exception as e:
            logger.error(f"[{sid}] get_wiki_pages failed: {e}")
            return {"pages": []}

    # ── Memory organization ────────────────────────────────────────────

    async def on_memory_organize(self, sid: str, data: dict) -> None:
        """Trigger memory organization."""
        logger.info(f"[{sid}] Received memory organization request")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system:
                await self.sio.emit(
                    "memory.organize.result",
                    {"type": "error", "message": "Memory system not initialized"},
                    to=sid,
                )
                return

            memory_system = ctx.memory_system
            if not memory_system._wiki_manager:
                await self.sio.emit(
                    "memory.organize.result",
                    {"type": "error", "message": "Wiki manager not initialized"},
                    to=sid,
                )
                return

            from anima.memory.wiki.organizer import WikiOrganizer

            llm_client = None
            if ctx.llm_engine:
                llm_client = ctx.llm_engine

            organizer = WikiOrganizer(
                wiki=memory_system._wiki_manager,
                llm_client=llm_client,
            )

            async def progress_callback(text, pct):
                await self.sio.emit(
                    "memory.organize.progress",
                    {"text": text, "progress": pct},
                    to=sid,
                )

            result = await organizer.organize(progress_callback=progress_callback)

            await self.sio.emit(
                "memory.organize.result",
                {
                    "type": "success",
                    "merges": result.get("merges", 0),
                    "synthesis": result.get("synthesis", 0),
                    "updates": result.get("updates", 0),
                    "errors": result.get("errors", []),
                },
                to=sid,
            )

            logger.info(
                f"[{sid}] Memory organization complete: "
                f"merges={result.get('merges', 0)}, "
                f"synthesis={result.get('synthesis', 0)}, "
                f"updates={result.get('updates', 0)}"
            )

        except Exception as e:
            logger.error(f"[{sid}] Memory organization failed: {e}", exc_info=True)
            await self.sio.emit(
                "memory.organize.result",
                {"type": "error", "message": str(e)},
                to=sid,
            )

    # ── Persona Runtime Switching ──────────────────────────────────────

    async def on_set_persona(self, sid: str, data: dict) -> None:
        """运行时切换人设"""
        persona_name = data.get("persona_name", "")
        if not persona_name:
            logger.warning(f"[{sid}] 切换人设失败: 人设名称为空")
            await self.sio.emit(
                "error",
                {"type": "error", "message": "persona_name is required"},
                to=sid,
            )
            return

        logger.info(f"[{sid}] 切换人设: {persona_name}")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx:
                await self.sio.emit(
                    "error",
                    {"type": "error", "message": "会话未初始化"},
                    to=sid,
                )
                return

            from anima.config.persona import PersonaConfig

            new_persona = PersonaConfig.load(persona_name)
            if not new_persona:
                await self.sio.emit(
                    "error",
                    {"type": "error", "message": f"无法加载人设: {persona_name}"},
                    to=sid,
                )
                return

            if self.global_config:
                self.global_config.persona = persona_name
                self.global_config._persona = None  # Invalidate cache

            if ctx.llm_engine and ctx.config:
                live2d_prompt = None
                try:
                    from anima.config.live2d import get_live2d_config
                    from anima.avatar.prompts import EmotionPromptBuilder

                    live2d_cfg = get_live2d_config()
                    if live2d_cfg and live2d_cfg.enabled:
                        builder = EmotionPromptBuilder.from_config(
                            {"valid_emotions": live2d_cfg.valid_emotions}
                        )
                        live2d_prompt = builder.build_prompt()
                except Exception:
                    pass

                new_system_prompt = ctx.config.get_system_prompt(
                    live2d_prompt=live2d_prompt
                )
                ctx.llm_engine.set_system_prompt(new_system_prompt)
                logger.info(f"[{sid}] 已更新 LLM 系统提示词")

            orchestrator = self.session_manager.get_orchestrator(sid)
            if orchestrator:
                logger.info(f"[{sid}] 编排器已感知人设变更")

            logger.info(f"[{sid}] 人设切换完成: {persona_name}")
            await self.sio.emit(
                "persona_updated",
                {"persona_name": persona_name},
                to=sid,
            )

        except Exception as e:
            logger.error(f"[{sid}] 切换人设失败: {e}", exc_info=True)
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    async def on_set_personality_mode(self, sid: str, data: dict) -> None:
        """设置个性模式（运行时切换）"""
        mode = data.get("mode", "")
        if not mode:
            logger.warning(f"[{sid}] 设置个性模式失败: mode 为空")
            await self.sio.emit(
                "error", {"type": "error", "message": "mode is required"}, to=sid
            )
            return

        logger.info(f"[{sid}] 设置个性模式: {mode}")

        try:
            orchestrator = self.session_manager.get_orchestrator(sid)

            if orchestrator:
                if not hasattr(orchestrator, "_personality_mode"):
                    orchestrator._personality_mode = {}
                orchestrator._personality_mode["mode"] = mode
                logger.info(f"[{sid}] 编排器已更新个性模式")

            await self.sio.emit("personality_updated", {"mode": mode}, to=sid)
            logger.info(f"[{sid}] 个性模式已设置: {mode}")

        except Exception as e:
            logger.error(f"[{sid}] 设置个性模式失败: {e}", exc_info=True)
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    # ── Memory Evolution: MemePool CRUD ────────────────────────────────

    async def on_meme_add(self, sid: str, data: dict) -> None:
        """添加梗到 MemePool"""
        text = data.get("text", "")
        context_hint = data.get("context_hint", "")
        tags = data.get("tags", [])
        logger.info(f"[{sid}] 添加梗: {text[:50]}...")

        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
                or not ctx.memory_system.meme_pool
            ):
                await self.sio.emit(
                    "error",
                    {"type": "error", "message": "MemePool 未初始化"},
                    to=sid,
                )
                return

            from anima.memory.meme import MemeSource

            meme = ctx.memory_system.meme_pool.add_meme(
                text=text,
                context_hint=context_hint,
                source=MemeSource.USER,
                tags=tags,
            )

            await self.sio.emit("meme_added", {"meme": meme.to_dict()}, to=sid)
            logger.info(f"[{sid}] 梗已添加: {meme.id}")

        except Exception as e:
            logger.error(f"[{sid}] 添加梗失败: {e}", exc_info=True)
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    async def on_meme_rate(self, sid: str, data: dict) -> None:
        """评分梗"""
        meme_id = data.get("meme_id", "")
        score = data.get("score", 0.0)
        logger.info(f"[{sid}] 评分梗: {meme_id} = {score}")

        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
                or not ctx.memory_system.meme_pool
            ):
                await self.sio.emit(
                    "error",
                    {"type": "error", "message": "MemePool 未初始化"},
                    to=sid,
                )
                return

            meme_pool = ctx.memory_system.meme_pool
            meme_pool.score_after_use(meme_id, effectiveness=score)

            await self.sio.emit(
                "meme_updated", {"meme_id": meme_id, "score": score}, to=sid
            )
            logger.info(f"[{sid}] 梗评分完成: {meme_id}")

        except Exception as e:
            logger.error(f"[{sid}] 评分梗失败: {e}", exc_info=True)
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    async def on_meme_delete(self, sid: str, data: dict) -> None:
        """删除梗（标记为非活跃）"""
        meme_id = data.get("meme_id", "")
        logger.info(f"[{sid}] 删除梗: {meme_id}")

        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
                or not ctx.memory_system.meme_pool
            ):
                await self.sio.emit(
                    "error",
                    {"type": "error", "message": "MemePool 未初始化"},
                    to=sid,
                )
                return

            meme_pool = ctx.memory_system.meme_pool
            meme_pool.store.set_active(meme_id, active=False)

            await self.sio.emit(
                "meme_updated", {"meme_id": meme_id, "active": False}, to=sid
            )
            logger.info(f"[{sid}] 梗已删除: {meme_id}")

        except Exception as e:
            logger.error(f"[{sid}] 删除梗失败: {e}", exc_info=True)
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    # ── Meme Review (筛选器) ──────────────────────────────────────────

    async def on_meme_list(self, sid: str, data: dict) -> None:
        """获取待筛选梗列表（meme:list）"""
        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
                or not ctx.memory_system.meme_pool
            ):
                await self.sio.emit(
                    "meme:list",
                    {"memes": [], "error": "MemePool 未初始化"},
                    to=sid,
                )
                return

            meme_pool = ctx.memory_system.meme_pool
            source_platform = data.get("source_platform", "")
            limit = data.get("limit", 50)

            active = meme_pool.store.list_active()
            pending = [m for m in active if m.review_status == "pending"]
            if source_platform:
                pending = [m for m in pending if m.source_platform == source_platform]
            pending = pending[:limit]

            memes_data = []
            for m in pending:
                item = {
                    "id": m.id,
                    "text": m.text,
                    "context_hint": m.context_hint,
                    "tags": m.tags,
                    "source_platform": m.source_platform,
                    "base_score": m.base_score,
                }
                if m.cognitive_analysis:
                    item["cognitive_analysis"] = {
                        "humor_mechanism": m.cognitive_analysis.humor_mechanism,
                        "emotional_tone": m.cognitive_analysis.emotional_tone,
                        "persona_fit_score": m.cognitive_analysis.persona_fit_score,
                        "source_url": m.cognitive_analysis.source_url,
                    }
                memes_data.append(item)

            await self.sio.emit(
                "meme:list",
                {"memes": memes_data, "total": len(memes_data)},
                to=sid,
            )
            logger.info(f"[{sid}] meme:list → {len(memes_data)} pending")

        except Exception as e:
            logger.error(f"[{sid}] meme:list error: {e}", exc_info=True)
            await self.sio.emit(
                "meme:list", {"memes": [], "error": str(e)}, to=sid
            )

    async def on_meme_review(self, sid: str, data: dict) -> None:
        """提交梗筛选结果（meme:review）"""
        meme_id = data.get("meme_id", "")
        status = data.get("status", "")

        if not meme_id or status not in ("good", "bad"):
            await self.sio.emit(
                "meme:review", {"ok": False, "error": "无效参数"}, to=sid
            )
            return

        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
            ):
                await self.sio.emit(
                    "meme:review",
                    {"ok": False, "error": "MemePool 未初始化"},
                    to=sid,
                )
                return

            meme_pool = ctx.memory_system.meme_pool
            meme = None
            for m in meme_pool.store.list_active():
                if m.id == meme_id:
                    meme = m
                    break
            if not meme:
                for m in meme_pool.store.list_discarded():
                    if m.id == meme_id:
                        meme = m
                        break

            if not meme:
                await self.sio.emit(
                    "meme:review",
                    {"ok": False, "error": f"梗未找到: {meme_id}"},
                    to=sid,
                )
                return

            meme.review_status = status
            if status == "good":
                meme.base_score = min(1.0, meme.base_score + 0.2)
                meme.current_score = meme.base_score
            else:
                meme.is_active = False

            feedback = await self._generate_meme_feedback(
                meme.text, meme.tags, status, ctx
            )
            if feedback and meme.cognitive_analysis:
                meme.cognitive_analysis.roast = feedback
            elif feedback:
                from anima.memory.meme.models import CognitiveAnalysis

                meme.cognitive_analysis = CognitiveAnalysis(roast=feedback)

            meme_pool.store.update(meme)
            await self.sio.emit(
                "meme:review",
                {
                    "ok": True,
                    "meme_id": meme_id,
                    "status": status,
                    "feedback": feedback,
                },
                to=sid,
            )
            logger.info(f"[{sid}] meme:review {meme_id} → {status}")

        except Exception as e:
            logger.error(f"[{sid}] meme:review error: {e}", exc_info=True)
            await self.sio.emit(
                "meme:review", {"ok": False, "error": str(e)}, to=sid
            )

    async def on_meme_dataset(self, sid: str, data: dict) -> None:
        """导出已筛选的高质量梗数据集（meme:dataset）"""
        try:
            ctx = self.session_manager.get_context(sid)
            if (
                not ctx
                or not ctx.memory_system
                or not hasattr(ctx.memory_system, "meme_pool")
            ):
                await self.sio.emit(
                    "meme:dataset",
                    {"memes": [], "error": "MemePool 未初始化"},
                    to=sid,
                )
                return

            meme_pool = ctx.memory_system.meme_pool
            source_platform = data.get("source_platform", "")
            all_active = meme_pool.store.list_active()
            inactive = meme_pool.store.list_discarded()
            good = [
                m for m in all_active + inactive if m.review_status == "good"
            ]
            if source_platform:
                good = [m for m in good if m.source_platform == source_platform]

            dataset = []
            for m in good:
                item = {
                    "text": m.text,
                    "context_hint": m.context_hint,
                    "tags": m.tags,
                    "source_platform": m.source_platform,
                }
                if m.cognitive_analysis:
                    item.update(
                        {
                            "humor_mechanism": m.cognitive_analysis.humor_mechanism,
                            "emotional_tone": m.cognitive_analysis.emotional_tone,
                            "usage_example": m.cognitive_analysis.usage_example,
                            "source_url": m.cognitive_analysis.source_url,
                        }
                    )
                dataset.append(item)

            await self.sio.emit(
                "meme:dataset",
                {"memes": dataset, "total": len(dataset)},
                to=sid,
            )
            logger.info(f"[{sid}] meme:dataset → {len(dataset)} good memes")

        except Exception as e:
            logger.error(f"[{sid}] meme:dataset error: {e}", exc_info=True)
            await self.sio.emit(
                "meme:dataset", {"memes": [], "error": str(e)}, to=sid
            )

    async def on_meme_collect(self, sid: str, data: dict) -> None:
        """触发B站热梗采集（meme:collect）"""
        logger.info(f"[{sid}] meme:collect — triggering Bilibili meme collection")
        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx:
                await self._get_or_create_orchestrator(sid)
                ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system:
                await self.sio.emit(
                    "meme:collect",
                    {"ok": False, "error": "Memory system not available"},
                    to=sid,
                )
                return

            learner = getattr(ctx.memory_system, "_learner", None)
            if learner and hasattr(learner, "collect_bilibili_memes"):
                ingested = await learner.collect_bilibili_memes()
                meme_pool = getattr(ctx.memory_system, "meme_pool", None)
                pending_count = 0
                if meme_pool:
                    active = meme_pool.store.list_active()
                    logger.info(
                        "[%s] meme:collect — list_active returned %d memes (%d pending)",
                        sid, len(active),
                        len([m for m in active if m.review_status == "pending"]),
                    )
                    pending_count = len(
                        [m for m in active if m.review_status == "pending"]
                    )
                await self.sio.emit(
                    "meme:collect",
                    {"ok": True, "count": pending_count, "ingested": ingested},
                    to=sid,
                )
                logger.info(
                    f"[{sid}] meme:collect — ingested {ingested}, "
                    f"{pending_count} pending memes"
                )
            else:
                import subprocess
                import sys
                import os

                project_root = os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(__file__))
                        )
                    )
                )
                script = os.path.join(
                    project_root, "scripts", "test_meme_collector.py"
                )
                if os.path.exists(script):
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable,
                        script,
                        cwd=project_root,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=120
                    )
                    if proc.returncode == 0:
                        await self.sio.emit(
                            "meme:collect", {"ok": True, "count": 0}, to=sid
                        )
                    else:
                        await self.sio.emit(
                            "meme:collect",
                            {"ok": False, "error": stderr.decode()[:200]},
                            to=sid,
                        )
                else:
                    await self.sio.emit(
                        "meme:collect",
                        {"ok": False, "error": f"Script not found: {script}"},
                        to=sid,
                    )
        except Exception as e:
            logger.error(f"[{sid}] meme:collect error: {e}", exc_info=True)
            await self.sio.emit(
                "meme:collect", {"ok": False, "error": str(e)}, to=sid
            )

    async def _generate_meme_feedback(
        self, text: str, tags: list, status: str, ctx
    ) -> str:
        """生成AI反馈（赞赏或吐槽），LLM不可用时降级到模板"""
        import random

        GOOD_TPL = [
            "这个梗的幽默结构完整，可以收入数据库。",
            "双关/反讽/荒诞机制运作正常——通过。",
            "数据支持：此梗具备传播潜力。",
            "逻辑链完整，笑点部署合理——合格。",
            "这个观察角度不错，值得保留。",
        ]
        BAD_TPL = [
            "这个梗的幽默密度≈真空，建议回炉重造。",
            "数据表明：此梗笑点缺失，情感共鸣为零。",
            "算法分析结果：该梗需要更多人类智慧注入。",
            "统计显示，此梗的传播系数接近于零——它不配。",
            "冷到连我的散热系统都不用工作了。",
        ]
        try:
            llm = getattr(ctx, "llm_engine", None) or getattr(ctx, "llm", None)
            if llm and hasattr(llm, "chat"):
                prompt = (
                    f"梗: {text}\n标签: {', '.join(tags) if tags else '无'}\n"
                    f"用户评价: {'好梗' if status == 'good' else '烂梗'}\n"
                    f"{'请用15-30字赞赏这个梗的优点。' if status == 'good' else '请用20-40字吐槽这个梗的问题。'}"
                    f"语气：理性冷幽默AI视角，禁止语气词。只返回点评文本。"
                )
                result = await llm.chat(
                    messages=[{"role": "user", "content": prompt}]
                )
                content = (
                    result.get("content", "")
                    if isinstance(result, dict)
                    else str(result)
                )
                content = content.strip().strip('"').strip("'")
                if content:
                    return content[:100]
        except Exception as e:
            logger.debug(f"[MemeReview] LLM feedback failed: {e}")

        return random.choice(GOOD_TPL if status == "good" else BAD_TPL)
