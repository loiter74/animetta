"""MemePool — meme lifecycle engine with time-decay scoring and resurrection."""

from __future__ import annotations

import logging
import math
import random
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import Meme, MemeSource
from .store import MemeStore

logger = logging.getLogger(__name__)


class MemePool:
    """Manages the 10-slot meme lifecycle with time-decay scoring and resurrection.

    Config keys (with defaults):
        max_active              10
        k (decay rate)           0.5
        t_half_days              7
        resurrection_threshold   0.6
        resurrection_bonus       0.1
        resurrection_max_bonuses  3
    """

    def __init__(
        self,
        store: Optional[MemeStore] = None,
        wiki: Optional[object] = None,
        config: Optional[Dict[str, Any]] = None,
        search_fn: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        # Handle both calling conventions:
        # 1. new: MemePool(wiki=wiki_manager, config=cfg) — store created internally
        # 2. tests: MemePool(store=fake_store, config=cfg)
        if wiki is not None and not isinstance(wiki, dict):
            self.store = MemeStore(wiki)
        elif store is not None:
            self.store = store
        else:
            raise ValueError("MemePool requires either 'store' or 'wiki' argument")
        cfg = wiki if isinstance(wiki, dict) else (config or {})
        cfg = cfg or {}

        self.max_active: int = cfg.get("max_active", 10)
        self.k: float = cfg.get("k", 0.5)
        self.t_half_days: int = cfg.get("t_half_days", 7)
        self.resurrection_threshold: float = cfg.get("resurrection_threshold", 0.6)
        self.resurrection_bonus: float = cfg.get("resurrection_bonus", 0.1)
        self.resurrection_max_bonuses: int = cfg.get("resurrection_max_bonuses", 3)
        self.persona_fit_threshold: float = cfg.get("persona_fit_threshold", 0.5)
        self._search_fn = search_fn  # Optional external semantic search

    # ── public API ────────────────────────────────────────────────────────

    def add_meme(
        self,
        text: str,
        context_hint: str = "",
        source: MemeSource = MemeSource.AI,
        tags: Optional[List[str]] = None,
    ) -> Meme:
        meme = Meme(
            text=text,
            context_hint=context_hint,
            source=source,
            tags=tags or [],
            base_score=0.7,
            current_score=0.7,
        )
        active = self.store.list_active()
        if len(active) < self.max_active:
            self.store.save(meme)
            logger.info("Meme added (pool has space): %s", meme.id)
        else:
            self._replace_lowest(meme)
        return meme

    def add_from_candidate(
        self,
        text: str,
        context_hint: str = "",
        confidence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> Optional[Meme]:
        active = self.store.list_active()
        pool_has_space = len(active) < self.max_active
        if not pool_has_space and confidence <= 0.4:
            logger.debug(
                "Candidate rejected (low confidence, pool full): %.2f", confidence
            )
            return None
        meme = Meme(
            text=text,
            context_hint=context_hint,
            source=MemeSource.AI,
            tags=tags or [],
            base_score=min(confidence + 0.1, 1.0),
            current_score=min(confidence + 0.1, 1.0),
        )
        if pool_has_space:
            self.store.save(meme)
        else:
            self._replace_lowest(meme)
        logger.info("Candidate accepted: %s (confidence=%.2f, review_status=%s, is_active=%s)",
                     meme.id, confidence, meme.review_status, meme.is_active)
        return meme

    def select_for_context(
        self,
        user_input: str,
        personality_mode: str = "normal",
        source_platform: Optional[str] = None,
    ) -> Optional[Meme]:
        """Select the best meme for the current conversation context.

        Uses semantic search (if available) or improved text matching
        to find memes relevant to user input. Filters by persona_fit_score
        and optional source_platform.

        Args:
            user_input: Current user message text.
            personality_mode: "normal" or "streaming".
            source_platform: Optional filter (e.g., "bilibili", "internal").

        Returns:
            Best matching Meme, or None if no suitable meme found.
        """
        active = self.store.list_active()
        if not active:
            return None

        # Apply source_platform filter
        if source_platform:
            active = [m for m in active if m.source_platform == source_platform]
            if not active:
                return None

        if personality_mode == "streaming":
            remaining = [m for m in active if m.is_active]
            # In streaming mode, still prefer higher persona_fit memes
            high_fit = [
                m for m in remaining
                if m.cognitive_analysis and m.cognitive_analysis.persona_fit_score >= self.persona_fit_threshold
            ]
            pool = high_fit if high_fit else remaining
            return random.choice(pool) if pool else None

        # Normal mode: semantic or text-based matching
        matches: List[Meme] = []
        for meme in active:
            if not meme.is_active:
                continue
            if not self._context_match(user_input, meme):
                continue
            # Filter by persona_fit_score if cognitive analysis available
            if meme.cognitive_analysis and meme.cognitive_analysis.persona_fit_score < self.persona_fit_threshold:
                continue
            matches.append(meme)

        if not matches:
            return None
        return max(matches, key=lambda m: m.current_score)

    def score_after_use(self, meme_id: str, effectiveness: float) -> None:
        meme = self._find_meme(meme_id)
        if meme is None:
            logger.warning("Meme not found for scoring: %s", meme_id)
            return
        meme.base_score = 0.7 * meme.base_score + 0.3 * effectiveness
        meme.current_score = meme.base_score
        meme.use_count += 1
        meme.last_used_at = datetime.now()
        self.store.update(meme)

    def maintain_pool(self) -> None:
        now = datetime.now()
        active = self.store.list_active()
        for meme in active:
            meme.current_score = self._effective_score(meme, now)
            self.store.update(meme)
        if len(active) > self.max_active:
            sorted_active = sorted(active, key=lambda m: m.current_score)
            to_discard = sorted_active[: len(active) - self.max_active]
            for meme in to_discard:
                self.store.discard(meme.id)
                logger.info(
                    "Discarded low-scoring meme: %s (score=%.3f)",
                    meme.id,
                    meme.current_score,
                )
        resurrected = self._check_resurrection()
        if resurrected:
            logger.info("Resurrected %d meme(s)", resurrected)

    def get_active(self) -> List[Meme]:
        return self.store.list_active()

    def get_stats(self) -> dict:
        active = self.store.list_active()
        discarded = self.store.list_discarded()
        avg_score = (
            sum(m.current_score for m in active) / len(active) if active else 0.0
        )
        return {
            "total_active": len(active),
            "total_discarded": len(discarded),
            "max_active": self.max_active,
            "average_score": round(avg_score, 4),
            "total_uses": sum(m.use_count for m in active),
            "config": {
                "k": self.k,
                "t_half_days": self.t_half_days,
                "resurrection_threshold": self.resurrection_threshold,
                "resurrection_bonus": self.resurrection_bonus,
                "resurrection_max_bonuses": self.resurrection_max_bonuses,
                "persona_fit_threshold": self.persona_fit_threshold,
            },
        }

    # ── internal helpers ──────────────────────────────────────────────────

    def _effective_score(self, meme: Meme, now: Optional[datetime] = None) -> float:
        now = now or datetime.now()
        ref = meme.last_used_at or meme.created_at or now
        delta_days = (now - ref).days
        decay = 1.0 / (1.0 + math.exp(self.k * (delta_days - self.t_half_days)))
        return meme.base_score * decay

    def _replace_lowest(self, new_meme: Meme) -> bool:
        active = self.store.list_active()
        if not active:
            self.store.save(new_meme)
            return True
        lowest = min(active, key=lambda m: m.current_score)
        self.store.discard(lowest.id)
        self.store.save(new_meme)
        logger.info(
            "Replaced %s (score=%.3f) with %s",
            lowest.id,
            lowest.current_score,
            new_meme.id,
        )
        return True

    def _check_resurrection(self) -> int:
        now = datetime.now()
        discarded = self.store.list_discarded()
        active = self.store.list_active()
        count = 0
        for meme in discarded:
            if len(active) + count >= self.max_active:
                break
            if meme.resurrection_count >= self.resurrection_max_bonuses:
                continue
            effective = self._effective_score(meme, now)
            if effective > self.resurrection_threshold:
                meme.base_score += self.resurrection_bonus
                meme.current_score = effective + self.resurrection_bonus
                meme.is_active = True
                meme.resurrection_count += 1
                meme.last_used_at = now
                self.store.update(meme)
                self.store.resurrect(meme.id)
                count += 1
        return count

    def _context_match(self, user_input: str, meme: Meme) -> bool:
        """Check if a meme matches the user's current input context.

        Uses semantic search if a search_fn was provided, otherwise falls
        back to improved text overlap matching (substring + case-insensitive
        word overlap).

        Also checks meme text and cognitive_analysis fields for broader matching.

        Backward-compatible: also accepts a plain string as second argument
        (treated as context_hint for legacy callers).
        """
        if not user_input:
            return False

        # Backward compatibility: if second arg is a string, use legacy matching
        if isinstance(meme, str):
            return self._text_overlap(user_input, meme)

        # Build search text from all meme context fields
        search_text = " ".join(filter(None, [
            meme.context_hint,
            meme.text,
            meme.cognitive_analysis.context_trigger if meme.cognitive_analysis else "",
            meme.cognitive_analysis.usage_example if meme.cognitive_analysis else "",
        ]))

        if not search_text.strip():
            return False

        # Try semantic search if available
        if self._search_fn:
            try:
                results = self._search_fn(user_input)
                if results:
                    # Check if any result text overlaps with meme's context
                    for r in results[:5]:
                        result_text = r.get("text", r.get("content", ""))
                        if result_text and self._text_overlap(result_text, search_text):
                            return True
                # If semantic search didn't find a match, fall through to text matching
            except Exception as e:
                logger.debug("[MemePool] Search function failed, falling back: %s", e)

        # Fallback: improved text-based matching
        return self._text_overlap(user_input, search_text)

    @staticmethod
    def _text_overlap(a: str, b: str) -> bool:
        """Check if two text strings have meaningful overlap.

        Steps:
        1. Guard against empty inputs
        2. Case-insensitive substring containment
        3. Word-level overlap (at least 25% of shorter text's words match)
        """
        if not a or not b:
            return False

        a_lower = a.lower()
        b_lower = b.lower()

        # Substring containment
        if a_lower in b_lower or b_lower in a_lower:
            return True

        # Word-level overlap for space-separated and mixed text
        a_words = set(re.findall(r'\w+', a_lower))
        b_words = set(re.findall(r'\w+', b_lower))
        if a_words and b_words:
            overlap = a_words & b_words
            min_count = min(len(a_words), len(b_words))
            if len(overlap) >= max(1, min_count * 0.25):
                return True

        return False

    @staticmethod
    def _context_match_legacy(user_input: str, context_hint: str) -> bool:
        """Legacy context matching (exact word overlap). Kept for reference."""
        if not context_hint:
            return False
        hint_words = set(context_hint.lower().split())
        input_words = set(user_input.lower().split())
        return bool(hint_words & input_words)

    def _find_meme(self, meme_id: str) -> Optional[Meme]:
        for meme in self.store.list_active():
            if meme.id == meme_id:
                return meme
        for meme in self.store.list_discarded():
            if meme.id == meme_id:
                return meme
        return None
