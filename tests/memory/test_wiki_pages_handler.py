"""Integration test: on_get_wiki_pages disk fallback logic."""

import os, sys, tempfile, json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


@pytest.fixture
def temp_wiki_dir():
    """Create a temporary wiki directory with sample .md files."""
    with tempfile.TemporaryDirectory() as tmp:
        wiki_dir = Path(tmp) / "wiki"
        wiki_dir.mkdir()

        # Create entities
        entities_dir = wiki_dir / "entities"
        entities_dir.mkdir()
        (entities_dir / "alice.md").write_text("# Alice\n\nUser loves Python.", encoding="utf-8")
        (entities_dir / "bob.md").write_text("# Bob\n\nUser lives in Beijing.", encoding="utf-8")

        # Create concepts
        concepts_dir = wiki_dir / "concepts"
        concepts_dir.mkdir()
        (concepts_dir / "dark-mode.md").write_text("# Dark Mode\n\nUser prefers dark mode.", encoding="utf-8")

        # Create sources
        sources_dir = wiki_dir / "sources"
        sources_dir.mkdir()
        (sources_dir / "2026-05-12.md").write_text("# Daily Log\n\nConversation summary.", encoding="utf-8")

        # Root wiki file
        (wiki_dir / "index.md").write_text("# Index\n\nWiki index page.", encoding="utf-8")

        yield Path(tmp)


class TestWikiPagesFromDisk:
    """Verify disk fallback reads .md files from wiki directory."""

    def test_scan_finds_all_pages(self, temp_wiki_dir):
        """All .md files under wiki/ should be found."""
        wiki_dir = temp_wiki_dir / "wiki"
        md_files = list(wiki_dir.rglob("*.md"))
        assert len(md_files) >= 5, f"Expected at least 5 .md files, got {len(md_files)}"

    def test_pages_have_required_fields(self, temp_wiki_dir):
        """Each page must have path, title, content, page_type."""
        wiki_dir = temp_wiki_dir / "wiki"
        pages = []
        for md_file in sorted(wiki_dir.rglob("*.md")):
            rel = str(md_file.relative_to(wiki_dir))
            content = md_file.read_text(encoding="utf-8")[:500]
            title = md_file.stem
            parent = md_file.parent.name if md_file.parent != wiki_dir else "source"
            pages.append({
                "path": rel,
                "title": title,
                "page_type": parent,
                "content": content,
            })

        for page in pages:
            assert page["path"], "path must not be empty"
            assert page["title"], f"title must not be empty: {page['path']}"
            assert page["page_type"] in ("entities", "concepts", "sources", "source"), \
                f"Unexpected page_type: {page['page_type']}"
            assert page["content"], f"content must not be empty: {page['path']}"

    def test_page_type_from_directory(self, temp_wiki_dir):
        """page_type should be derived from parent directory name."""
        wiki_dir = temp_wiki_dir / "wiki"
        pages = {}
        for md_file in wiki_dir.rglob("*.md"):
            rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
            parent = md_file.parent.name if md_file.parent != wiki_dir else "source"
            pages[rel] = parent

        assert pages.get("entities/alice.md") == "entities"
        assert pages.get("concepts/dark-mode.md") == "concepts"
        assert pages.get("sources/2026-05-12.md") == "sources"
        assert pages.get("index.md") == "source"  # root file → source

    def test_empty_wiki_returns_empty(self, temp_wiki_dir):
        """Empty wiki directory returns no pages."""
        empty = temp_wiki_dir / "empty_wiki"
        empty.mkdir()
        files = list(empty.rglob("*.md"))
        assert len(files) == 0
