"""
Memory scorer

Computes importance scores for conversations based on rules, determines whether long-term storage is warranted.
"""

import math
import re
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger

from ..models.turns import MemoryTurn

# Emotion intensity mapping: label → base intensity (0.0-1.0)
# High-intensity emotions get stronger retrieval boost and slower decay
EMOTION_INTENSITY: dict[str, float] = {
    "happy": 0.7,
    "surprised": 0.8,
    "angry": 0.9,
    "sad": 0.8,
    "thinking": 0.3,
    "neutral": 0.1,
}

# Retrieve weight boost multiplier for high-emotion results
EMOTION_BOOST_FACTOR = 0.5  # up to +50% boost for max intensity

# Decay parameters
DECAY_BASE_RATE = 0.05       # λ base rate (decay per day)
DECAY_EPSILON = 0.01         # Prevent division by zero
DECAY_ARCHIVE_THRESHOLD = 0.15  # Score below this → archived


class MemoryScorer:
    """
    Memory importance scorer

    Evaluates conversation importance using multiple rule-based criteria.

    Scoring rules:
    1. Base score (0.3): every conversation has a base score
    2. Key info bonus (+0.15): name, preference, age, location, etc.
    3. Length reward (+0.1): 50+ characters
    4. Question penalty (-0.1): questions are usually less important

    Score range: 0.0 ~ 1.0
    Threshold: >= 0.5 write to MEMORY.md, >= 0.3 write to daily log, < 0.3 skip
    """

    # Key information patterns (bonus)
    KEY_INFO_PATTERNS = [
        r'我[叫是](.+)',
        r'我的名字[是为](.+)',
        r'我今年(\d+)',
        r'我\d+岁',
        r'我住在(.+)',
        r'我的职业[是为](.+)',
        r'我(比较|特别|非常)(喜欢|讨厌|爱|恨)(.+)',
        r'我(想|希望|想要)(.+)',
        r'记住(.+)',
        r'别忘了(.+)',
    ]

    def __init__(self):
        # Compile patterns
        self._key_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.KEY_INFO_PATTERNS
        ]

    def score(self, turn: MemoryTurn) -> float:
        """
        Compute conversation importance score

        Args:
            turn: Conversation turn

        Returns:
            Score from 0.0 to 1.0
        """
        user_input = turn.user_input.strip()

        # 1. Base score
        score = 0.3

        # 2. Key info bonus
        for pattern in self._key_patterns:
            if pattern.search(user_input):
                score += 0.15
                logger.debug(f"[MemoryScorer] Detected key info: {pattern.pattern}")
                break  # Only add once

        # 3. Length reward (more information likely)
        if len(user_input) > 50:
            score += 0.1

        # 4. Question penalty (usually less important)
        if user_input.endswith('?') and len(user_input) < 15:
            score -= 0.1

        # Clamp to range
        score = max(0.0, min(score, 1.0))

        logger.debug(f"[MemoryScorer] Scoring complete: {score:.2f} (input: {user_input[:30]}...)")

        return score

    def should_store(self, score: float) -> bool:
        """
        Determine if the turn should be stored

        Args:
            score: Importance score

        Returns:
            True if should store
        """
        return score >= 0.3

    # ── Emotion-weighted scoring ──────────────────────────────

    @staticmethod
    def emotion_intensity(turn: MemoryTurn) -> float:
        """Compute emotion intensity from turn's emotion labels.

        Returns a value in [0.0, 1.0] where higher = more intense emotion.
        Neutral = 0.1, happy = 0.7, angry = 0.9, etc.
        """
        if not turn.emotions:
            return 0.0
        intensities = [
            EMOTION_INTENSITY.get(e.lower(), 0.3)
            for e in turn.emotions
        ]
        return max(intensities) if intensities else 0.0

    @staticmethod
    def emotion_weight(emotion_value: Optional[float]) -> float:
        """Compute retrieval ranking boost from emotion value.

        Returns a multiplier in [1.0, 1.5] where:
        - 0.0 (no emotion): 1.0 (no boost)
        - 0.5 (moderate):  1.25
        - 1.0 (intense):   1.5

        Args:
            emotion_value: 0.0-1.0 emotion intensity
        """
        if emotion_value is None or emotion_value <= 0.0:
            return 1.0
        return 1.0 + min(emotion_value, 1.0) * EMOTION_BOOST_FACTOR

    @staticmethod
    def emotion_decay_factor(emotion_value: Optional[float]) -> float:
        """Compute decay rate multiplier from emotion value.

        Higher emotion → slower decay (inverse relationship).
        Returns a multiplier in (0.2, 1.0] where:
        - 1.0 (intense): almost no decay (factor 1.0)
        - 0.0 (none):    full decay speed (factor 0.2)

        Args:
            emotion_value: 0.0-1.0 emotion intensity
        """
        if emotion_value is None or emotion_value <= 0.0:
            return 0.2
        return min(emotion_value, 1.0)

    # ── Memory decay scoring ─────────────────────────────────

    @staticmethod
    def compute_decay(
        created_at: Optional[str],
        retrieval_count: int = 0,
        emotion_value: Optional[float] = None,
        base_rate: float = DECAY_BASE_RATE,
    ) -> float:
        """Compute decay score for a memory entry.

        Uses exponential decay: e^(-λt) where λ adapts by emotion and retrieval count.

        Formula:
            λ = base_rate / (max(emotion_value, ε) * max(retrieval_count, 1) + ε)
            decay = e^(-λ * days_since_created)

        Args:
            created_at: ISO datetime string of memory creation
            retrieval_count: Times the entry has been retrieved
            emotion_value: Emotion intensity 0.0-1.0
            base_rate: Base decay rate (default 0.05/day)

        Returns:
            Decay multiplier in (0.0, 1.0]: 1.0 = no decay, 0.0 = fully decayed
        """
        if not created_at:
            return 1.0

        try:
            created = datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days = max(0.0, (now - created).total_seconds() / 86400.0)
        except (ValueError, TypeError):
            return 1.0

        if days <= 0:
            return 1.0

        # Adaptive decay rate: slower for high-emotion, frequently-retrieved memories
        e_val = max(emotion_value or 0.0, DECAY_EPSILON)
        r_count = max(retrieval_count, 1)
        lam = base_rate / (e_val * r_count + DECAY_EPSILON)

        decay = math.exp(-lam * days)
        return max(0.0, min(decay, 1.0))

    @staticmethod
    def memory_score(
        confidence: float = 0.5,
        created_at: Optional[str] = None,
        retrieval_count: int = 0,
        emotion_value: Optional[float] = None,
    ) -> tuple[float, float, bool]:
        """Compute a final retrieval score for a MemoryEntry.

        Combines confidence, decay, and emotion boost into a single score.

        Returns:
            (final_score, decay_factor, is_archived)
                final_score: Combined score in [0, 1]
                decay_factor: Raw decay multiplier
                is_archived: True if score below archive threshold
        """
        decay = MemoryScorer.compute_decay(
            created_at=created_at,
            retrieval_count=retrieval_count,
            emotion_value=emotion_value,
        )
        emotion_boost = MemoryScorer.emotion_weight(emotion_value)

        final = confidence * decay * emotion_boost
        final = max(0.0, min(final, 1.0))

        is_archived = final < DECAY_ARCHIVE_THRESHOLD
        return final, decay, is_archived
