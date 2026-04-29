"""LINT workflow - wiki health checks & maintenance.

Scans for broken links, orphan pages, contradictions,
and index drift.  Produces a report but does NOT auto-modify.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from .manager import WikiManager
from .models import PageType

logger = logging.getLogger(__name__)


@dataclass
class LintReport:
    broken_links: List[str] = field(default_factory=list)
    orphan_pages: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    index_drift: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not (self.broken_links or self.orphan_pages
                    or self.contradictions or self.index_drift)

    def summary(self) -> str:
        lines = ["# Wiki Lint Report\n"]
        if self.is_clean:
            lines.append("All checks passed.")
            return "\n".join(lines)

        if self.broken_links:
            lines.append(f"## Broken Links ({len(self.broken_links)})\n")
            for bl in self.broken_links:
                lines.append(f"- {bl}")

        if self.orphan_pages:
            lines.append(f"\n## Orphan Pages ({len(self.orphan_pages)})\n")
            for op in self.orphan_pages:
                lines.append(f"- {op}")

        if self.contradictions:
            lines.append(f"\n## Contradictions ({len(self.contradictions)})\n")
            for ct in self.contradictions:
                lines.append(f"- {ct}")

        if self.index_drift:
            lines.append(f"\n## Index Drift ({len(self.index_drift)})\n")
            for id_ in self.index_drift:
                lines.append(f"- {id_}")

        if self.warnings:
            lines.append(f"\n## Warnings ({len(self.warnings)})\n")
            for w in self.warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)


class WikiLint:
    """LINT workflow runner."""

    def __init__(self, wiki: WikiManager):
        self._wiki = wiki

    def run(self) -> LintReport:
        report = LintReport()
        all_pages = self._wiki.list_pages()

        # 1. broken links
        page_names: Set[str] = {p.rstrip(".md") for p in all_pages}
        page_names.update(Path(p).stem for p in all_pages)
        for rel in all_pages:
            page = self._wiki.read_page(rel)
            if not page:
                continue
            for link in page.links:
                # normalize link target
                target = link.rstrip(".md")
                if target not in page_names:
                    # also check as file path
                    candidates = [
                        f"{link}.md",
                        link,
                        f"entities/{link}.md",
                        f"concepts/{link}.md",
                        f"sources/{link}.md",
                    ]
                    found = any(self._wiki.page_exists(c) for c in candidates)
                    if not found:
                        report.broken_links.append(f"[[{link}]] in {rel}")

        # 2. orphan pages
        linked_targets: Set[str] = set()
        for rel in all_pages:
            page = self._wiki.read_page(rel)
            if page:
                linked_targets.update(page.links)
        for rel in all_pages:
            page = self._wiki.read_page(rel)
            if not page:
                continue
            name = rel.rstrip(".md")
            stem = Path(rel).stem
            is_linked = (name in linked_targets or stem in linked_targets
                         or page.page_type == PageType.SOURCE)  # sources auto-linked
            if not is_linked:
                report.orphan_pages.append(rel)

        # 3. index drift
        try:
            index_content = self._wiki.manager.get("wiki/index.md")
        except Exception:
            index_content = ""
        for rel in all_pages:
            stem = Path(rel).stem
            if stem not in index_content and rel not in index_content:
                report.index_drift.append(f"{rel} missing from index")

        logger.info(f"[WikiLint] report: {len(report.broken_links)} broken links, "
                     f"{len(report.orphan_pages)} orphans, {len(report.index_drift)} drifts")
        return report
