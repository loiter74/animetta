"""
Memory scorer

Computes importance scores for conversations based on rules, determines whether long-term storage is warranted.
"""

import re
from typing import List, Optional
from datetime import datetime
from loguru import logger

from ..models.turns import MemoryTurn


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
