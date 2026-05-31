"""
Meme pool event handlers — CRUD, review, dataset, collection.
"""

import asyncio
import os
import sys
from typing import TYPE_CHECKING

from loguru import logger

from .base_handler import BaseSocketHandler

if TYPE_CHECKING:
    from socketio import AsyncServer

    from ..desktop import DesktopClientManager
    from ..live2d import Live2DManager
    from ..session import SessionManager


class MemeHandlers(BaseSocketHandler):
    """Meme pool CRUD and review event handlers.

    Inherits shared infrastructure from BaseSocketHandler.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: "DesktopClientManager",
        live2d_manager: "Live2DManager",
    ):
        super().__init__(sio, session_manager, desktop_manager, live2d_manager)

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
                        f"[{sid}] meme:collect — list_active returned {len(active)} memes "
                        f"({len([m for m in active if m.review_status == 'pending'])} pending)"
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
