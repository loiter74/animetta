"""
记忆评分器

基于规则计算对话的重要性分数，决定是否值得长期存储。
"""

import re
from typing import List, Optional
from datetime import datetime
from loguru import logger

from .memory_turn import MemoryTurn


class MemoryScorer:
    """
    记忆评分器

    根据多条规则评估对话的重要性分数。

    评分规则:
    1. 基础分 (0.3): 每条对话都有基础分
    2. 关键信息加分 (+0.15): 名字、偏好、年龄、住址等
    3. 长度奖励 (+0.1): 50+ 字符
    4. 问句降分 (-0.1): 通常不重要

    分数范围: 0.0 ~ 1.0
    阈值: >= 0.5 写入 MEMORY.md, >= 0.3 写入 daily log, < 0.3 跳过
    """

    # 关键信息模式 (加分)
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
        # 编译模式
        self._key_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.KEY_INFO_PATTERNS
        ]

    def score(self, turn: MemoryTurn) -> float:
        """
        计算对话的重要性分数

        Args:
            turn: 对话轮次

        Returns:
            0.0 ~ 1.0 的分数
        """
        user_input = turn.user_input.strip()

        # 1. 基础分
        score = 0.3

        # 2. 关键信息加分
        for pattern in self._key_patterns:
            if pattern.search(user_input):
                score += 0.15
                logger.debug(f"[MemoryScorer] 检测到关键信息: {pattern.pattern}")
                break  # 只加一次

        # 3. 长度奖励 (信息量可能更多)
        if len(user_input) > 50:
            score += 0.1

        # 4. 问句降分 (通常不重要)
        if user_input.endswith('?') and len(user_input) < 15:
            score -= 0.1

        # 限制范围
        score = max(0.0, min(score, 1.0))

        logger.debug(f"[MemoryScorer] 评分完成: {score:.2f} (输入: {user_input[:30]}...)")

        return score

    def should_store(self, score: float) -> bool:
        """
        判断是否应该存储

        Args:
            score: 评分

        Returns:
            True 表示应该存储
        """
        return score >= 0.3
