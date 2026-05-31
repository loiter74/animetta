"""Tests for PageType enum, WikiPage with frontmatter."""

from __future__ import annotations

from datetime import datetime

import pytest

from animetta.memory.wiki.models import PageType, WikiPage


class TestPageType:
    """PageType enum members."""

    def test_members(self):
        assert PageType.ENTITY.value == "entity"
        assert PageType.CONCEPT.value == "concept"
        assert PageType.SOURCE.value == "source"
        assert PageType.SYNTHESIS.value == "synthesis"
        assert PageType.MEME.value == "meme"

    def test_all_types_covered(self):
        assert len(PageType) == 5


class TestWikiPage:
    """WikiPage dataclass — construction, to_markdown, from_markdown."""

    def test_minimal_page(self):
        page = WikiPage(title="Test", page_type=PageType.ENTITY, path="entities/test.md", content="Hello")
        assert page.title == "Test"
        assert page.page_type == PageType.ENTITY
        assert page.tags == []
        assert page.links == []

    def test_to_markdown_contains_frontmatter(self):
        page = WikiPage(
            title="User Profile",
            page_type=PageType.ENTITY,
            path="entities/user.md",
            content="## About\nThe user is...",
            tags=["user", "profile"],
            links=["concepts/preferences"],
        )
        md = page.to_markdown()
        assert md.startswith("---")
        assert "type: entity" in md
        assert "tags:" in md
        assert "links:" in md
        assert "## About" in md

    def test_to_markdown_roundtrip(self):
        original = WikiPage(
            title="My Page",
            page_type=PageType.CONCEPT,
            path="concepts/my-page.md",
            content="# My Page\n\nSome content here.\n\nSee [[entities/other]] for details.",
            tags=["tag1", "tag2"],
            links=["entities/other"],
            raw_source="raw/2026-05-10.md",
        )
        md = original.to_markdown()
        parsed = WikiPage.from_markdown("concepts/my-page.md", md)
        assert parsed.title == original.title
        assert parsed.page_type == original.page_type
        assert parsed.tags == original.tags
        assert parsed.raw_source == original.raw_source
        # Links are parsed from wikilinks in content body, not from frontmatter
        assert "entities/other" in parsed.links

    def test_from_markdown_no_frontmatter(self):
        md = "# Just Content\n\nNo frontmatter here."
        page = WikiPage.from_markdown("entities/simple.md", md)
        assert page.title == "Just Content"
        assert page.page_type == PageType.ENTITY  # default
        assert page.content == md.strip()

    def test_from_markdown_title_from_filename(self):
        """When no H1 heading, title is derived from filename."""
        md = "Some plain content without heading."
        page = WikiPage.from_markdown("entities/my-entity.md", md)
        assert page.title == "my entity"

    def test_from_markdown_extracts_wikilinks(self):
        md = "See [[entities/other]] and [[concepts/something]]."
        page = WikiPage.from_markdown("entities/test.md", md)
        assert "entities/other" in page.links
        assert "concepts/something" in page.links

    def test_from_markdown_frontmatter_tags(self):
        md = "---\ntags: [a, b, c]\ntype: concept\n---\n\nContent"
        page = WikiPage.from_markdown("concepts/x.md", md)
        assert page.tags == ["a", "b", "c"]
        assert page.page_type == PageType.CONCEPT

    def test_from_markdown_invalid_frontmatter(self):
        """Invalid YAML frontmatter falls back gracefully."""
        md = "---\ninvalid: [unclosed\n---\n\nContent"
        page = WikiPage.from_markdown("entities/x.md", md)
        # Should not crash; content is everything after frontmatter
        assert page is not None
        assert "Content" in page.content

    def test_created_at_updated_at_defaults(self):
        page = WikiPage(title="X", page_type=PageType.ENTITY, path="x.md", content="x")
        assert isinstance(page.created_at, datetime)
        assert isinstance(page.updated_at, datetime)

    def test_metadata_dict(self):
        page = WikiPage(
            title="Meta",
            page_type=PageType.SYNTHESIS,
            path="synthesis/m.md",
            content="meta",
            metadata={"custom_key": "custom_value"},
        )
        assert page.metadata["custom_key"] == "custom_value"

    def test_to_markdown_includes_raw_source(self):
        page = WikiPage(
            title="Source",
            page_type=PageType.SOURCE,
            path="sources/daily.md",
            content="summary",
            raw_source="raw/2026-01-01.md",
        )
        md = page.to_markdown()
        assert "raw_source" in md

    def test_page_type_roundtrip_via_frontmatter(self):
        for pt in PageType:
            page = WikiPage(
                title=pt.value,
                page_type=pt,
                path=f"{pt.value}/p.md",
                content="test",
            )
            md = page.to_markdown()
            parsed = WikiPage.from_markdown(f"{pt.value}/p.md", md)
            assert parsed.page_type == pt
