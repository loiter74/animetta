"""Wiki Memory Organizer - LLM-driven topological reorganization.

Triggered manually via frontend button. Uses the configured LLM to:
1. Analyze all wiki pages and build a relationship graph
2. Identify clusters, duplicates, and missing connections
3. Merge similar pages and create synthesis pages
4. Rebuild the wiki index
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .manager import WikiManager
from .models import PageType, WikiPage

logger = logging.getLogger(__name__)

ORGANIZE_PROMPT = """\
你是一个记忆整理助手。以下是当前 wiki 中所有页面的摘要信息。
请分析这些页面，找出可以合并的重复/相似主题，以及可以创建的跨时间线合成页。

## 当前页面

{pages_summary}

## 任务

请以 JSON 格式输出整理建议:

```json
{{
  "merges": [
    {{
      "sources": ["entities/a.md", "concepts/like-a.md"],
      "target": "synthesis/topic-a.md",
      "title": "主题名称",
      "reason": "合并原因"
    }}
  ],
  "synthesis": [
    {{
      "path": "synthesis/topic.md",
      "title": "合成页标题",
      "source_pages": ["entities/x.md", "concepts/y.md"],
      "summary": "要写入合成页的摘要内容"
    }}
  ],
  "updates": [
    {{
      "path": "entities/x.md",
      "add_links": ["synthesis/topic.md"],
      "reason": "补充关联"
    }}
  ]
}}
```

规则:
- merges: 将多个高度相关的页面合并为一个 synthesis 页面 (保留原始页面，创建新的合成页)
- synthesis: 为跨时间线的重要主题创建合成总结页
- updates: 为已有页面补充缺失的双链
- 不要建议删除任何页面
- 每个 merge/synthesis 最多涉及 5 个源页面
- 只输出确实有价值的建议，宁缺毋滥
- 如果没有需要整理的内容，输出空的 merges/synthesis/updates 数组
"""

SYSTEM_PROMPT = "你是记忆整理专家，擅长分析和重组知识库。只输出有效 JSON，不要添加任何额外文字。"


class WikiOrganizer:
    """LLM-driven wiki reorganization service."""

    def __init__(self, wiki: WikiManager, llm_client=None):
        self._wiki = wiki
        self._llm_client = llm_client

    async def organize(self, progress_callback=None) -> Dict[str, Any]:
        """Run full organization pipeline.

        Args:
            progress_callback: async callable(status_text, progress_pct)

        Returns:
            Dict with 'merges', 'synthesis', 'updates', 'errors' counts.
        """
        result = {"merges": 0, "synthesis": 0, "updates": 0, "errors": []}

        # Step 1: Collect all pages
        await self._progress(progress_callback, "正在收集 wiki 页面...", 10)
        pages = self._collect_pages()
        if not pages:
            await self._progress(progress_callback, "没有需要整理的页面", 100)
            return result

        # Step 2: Build relationship graph
        await self._progress(progress_callback, "正在分析页面关系...", 25)
        graph = self._build_graph(pages)

        # Step 3: Get LLM suggestions
        await self._progress(progress_callback, "正在调用 AI 分析整理建议...", 40)
        suggestions = await self._get_suggestions(pages, graph)

        if not suggestions:
            await self._progress(progress_callback, "AI 认为当前记忆已经很整洁", 100)
            return result

        # Step 4: Apply suggestions
        total_steps = (
            len(suggestions.get("merges", []))
            + len(suggestions.get("synthesis", []))
            + len(suggestions.get("updates", []))
        )
        if total_steps == 0:
            await self._progress(progress_callback, "没有需要执行的操作", 100)
            return result

        step = 0

        # Apply merges
        for merge in suggestions.get("merges", []):
            step += 1
            pct = 50 + int(40 * step / total_steps)
            await self._progress(
                progress_callback,
                f"正在合并: {merge.get('title', '...')}",
                pct,
            )
            try:
                if self._apply_merge(merge):
                    result["merges"] += 1
            except Exception as e:
                logger.warning(f"[Organizer] merge failed: {e}")
                result["errors"].append(f"merge: {e}")

        # Apply synthesis
        for synth in suggestions.get("synthesis", []):
            step += 1
            pct = 50 + int(40 * step / total_steps)
            await self._progress(
                progress_callback,
                f"正在创建合成页: {synth.get('title', '...')}",
                pct,
            )
            try:
                if self._apply_synthesis(synth):
                    result["synthesis"] += 1
            except Exception as e:
                logger.warning(f"[Organizer] synthesis failed: {e}")
                result["errors"].append(f"synthesis: {e}")

        # Apply updates
        for upd in suggestions.get("updates", []):
            step += 1
            pct = 50 + int(40 * step / total_steps)
            await self._progress(
                progress_callback,
                f"正在更新链接: {upd.get('path', '...')}",
                pct,
            )
            try:
                if self._apply_update(upd):
                    result["updates"] += 1
            except Exception as e:
                logger.warning(f"[Organizer] update failed: {e}")
                result["errors"].append(f"update: {e}")

        # Step 5: Rebuild index
        await self._progress(progress_callback, "正在重建索引...", 95)
        try:
            self._wiki.rebuild_index()
        except Exception as e:
            logger.warning(f"[Organizer] rebuild_index failed: {e}")
        try:
            self._wiki.manager.sync()
        except Exception as e:
            logger.warning(f"[Organizer] sync failed: {e}")
            result["errors"].append(f"sync: {e}")
        self._wiki.append_log("organize", "all", self._summarize_result(result))

        await self._progress(progress_callback, "记忆整理完成!", 100)
        return result

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    async def _progress(callback, text, pct):
        if callback:
            try:
                await callback(text, pct)
            except Exception as e:
                logger.debug(f"[Organizer] Progress callback failed: {e}")

    def _collect_pages(self) -> Dict[str, WikiPage]:
        """Read all wiki pages."""
        pages = {}
        for rel in self._wiki.list_pages():
            page = self._wiki.read_page(rel)
            if page:
                pages[rel] = page
        return pages

    def _build_graph(self, pages: Dict[str, WikiPage]) -> Dict[str, Any]:
        """Build a simple relationship graph from links and tags."""
        tag_map: Dict[str, List[str]] = defaultdict(list)
        link_map: Dict[str, List[str]] = defaultdict(list)
        backlinks: Dict[str, List[str]] = defaultdict(list)

        for rel, page in pages.items():
            for tag in page.tags:
                tag_map[tag].append(rel)
            for link in page.links:
                link_map[rel].append(link)
                backlinks[link].append(rel)

        return {
            "tag_groups": {k: v for k, v in tag_map.items() if len(v) > 1},
            "links": dict(link_map),
            "backlinks": dict(backlinks),
        }

    def _format_pages_summary(self, pages: Dict[str, WikiPage]) -> str:
        """Format page metadata for LLM prompt."""
        lines = []
        for rel, page in sorted(pages.items()):
            content_preview = page.content[:200].replace("\n", " ")
            lines.append(
                f"- {rel}: tags={page.tags}, links={page.links}, "
                f"content_preview=\"{content_preview}\""
            )
        return "\n".join(lines)

    async def _get_suggestions(
        self, pages: Dict[str, WikiPage], graph: Dict[str, Any]
    ) -> Optional[Dict]:
        """Call LLM to get reorganization suggestions."""
        if not self._llm_client:
            logger.warning("[Organizer] No LLM client, using rule-based fallback")
            return self._rule_based_suggestions(pages, graph)

        prompt = ORGANIZE_PROMPT.format(
            pages_summary=self._format_pages_summary(pages),
        )

        try:
            response = await self._call_llm(prompt)
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"[Organizer] LLM call failed: {e}")
            return self._rule_based_suggestions(pages, graph)

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with the given prompt."""
        if hasattr(self._llm_client, 'ainvoke'):
            # LangChain ChatModel
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            resp = await self._llm_client.ainvoke(messages)
            return resp.content if hasattr(resp, 'content') else str(resp)
        elif hasattr(self._llm_client, 'chat'):
            # LLMInterface (anima's own)
            full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
            return await self._llm_client.chat(full_prompt)
        elif callable(self._llm_client):
            return await self._llm_client(prompt)
        else:
            raise ValueError(f"Unsupported LLM client type: {type(self._llm_client)}")

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict]:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find first { ... } block
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            logger.error(f"[Organizer] Failed to parse LLM response")
            return None

    def _rule_based_suggestions(
        self, pages: Dict[str, WikiPage], graph: Dict[str, Any]
    ) -> Dict:
        """Fallback: rule-based suggestions without LLM."""
        suggestions = {"merges": [], "synthesis": [], "updates": []}

        # Find entities mentioned in multiple sources (same tag group)
        for tag, rels in graph.get("tag_groups", {}).items():
            entity_rels = [r for r in rels if r.startswith("entities/")]
            concept_rels = [r for r in rels if r.startswith("concepts/")]

            if len(entity_rels) + len(concept_rels) >= 2 and len(entity_rels) + len(concept_rels) <= 5:
                related = entity_rels + concept_rels
                titles = [Path(r).stem.replace("-", " ") for r in related]
                suggestions["synthesis"].append({
                    "path": f"synthesis/{tag}.md",
                    "title": f"关于{tag}的综合",
                    "source_pages": related,
                    "summary": f"以下页面都与「{tag}」相关: {', '.join(titles)}",
                })

        # Suggest adding backlinks
        for rel, page in pages.items():
            for link in page.links:
                target = pages.get(link)
                if target and rel not in target.links:
                    suggestions["updates"].append({
                        "path": link,
                        "add_links": [rel],
                        "reason": f"补充来自 {rel} 的反向链接",
                    })

        return suggestions

    def _apply_merge(self, merge: Dict) -> bool:
        """Create a synthesis page from merged sources. Returns True if applied."""
        sources = merge.get("sources", [])
        target = merge.get("target", "")
        title = merge.get("title", "合并主题")
        reason = merge.get("reason", "")

        if not sources or not target:
            return False

        if self._wiki.page_exists(target):
            return False

        content_parts = [f"# {title}\n\n"]
        content_parts.append(f"> 合并原因: {reason}\n\n")

        for src_rel in sources:
            page = self._wiki.read_page(src_rel)
            if page:
                content_parts.append(f"## 来自 [{page.title}]({src_rel})\n\n")
                content_parts.append(page.content + "\n\n")

        now = datetime.now()
        new_page = WikiPage(
            title=title,
            page_type=PageType.SYNTHESIS,
            path=target,
            content="".join(content_parts),
            tags=["merged", now.strftime("%Y-%m-%d")],
            links=[Path(s).stem for s in sources],
            created_at=now,
            updated_at=now,
        )
        self._wiki.write_page(new_page)
        self._wiki.append_log("merge", target, f"from: {', '.join(sources)}")
        return True

    def _apply_synthesis(self, synth: Dict) -> bool:
        """Create a new synthesis page. Returns True if created."""
        path = synth.get("path", "")
        title = synth.get("title", "")
        source_pages = synth.get("source_pages", [])
        summary = synth.get("summary", "")

        if not path or not title:
            return False

        if self._wiki.page_exists(path):
            logger.debug(f"[Organizer] synthesis page already exists: {path}")
            return False

        content = f"# {title}\n\n{summary}\n\n"
        content += "## 来源页面\n\n"
        for sp in source_pages:
            content += f"- [[{Path(sp).stem}]]\n"
        content += "\n"

        now = datetime.now()
        new_page = WikiPage(
            title=title,
            page_type=PageType.SYNTHESIS,
            path=path,
            content=content,
            tags=["synthesis", now.strftime("%Y-%m-%d")],
            links=[Path(sp).stem for sp in source_pages],
            created_at=now,
            updated_at=now,
        )
        self._wiki.write_page(new_page)
        self._wiki.append_log("synthesis", path, f"sources: {', '.join(source_pages)}")
        return True

    def _apply_update(self, upd: Dict) -> bool:
        """Add missing links to an existing page. Returns True if updated."""
        path = upd.get("path", "")
        add_links = upd.get("add_links", [])

        if not path or not add_links:
            return False

        page = self._wiki.read_page(path)
        if not page:
            return

        changed = False
        for link in add_links:
            link_name = Path(link).stem if "/" in link else link
            if link_name not in page.links:
                page.links.append(link_name)
                changed = True

        if changed:
            page.updated_at = datetime.now()
            self._wiki.write_page(page)
            return True
        return False

    @staticmethod
    def _summarize_result(result: Dict) -> str:
        parts = []
        if result["merges"]:
            parts.append(f"{result['merges']} merged")
        if result["synthesis"]:
            parts.append(f"{result['synthesis']} synthesis")
        if result["updates"]:
            parts.append(f"{result['updates']} updated")
        if result["errors"]:
            parts.append(f"{len(result['errors'])} errors")
        return "; ".join(parts) or "no changes"
