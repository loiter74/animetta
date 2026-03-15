"""
记忆注入 Prompt 构建器

负责构建注入到 Agent system提示的记忆上下文。
"""

from typing import List
from loguru import logger


class MemoryPromptBuilder:
    """
    记忆注入 Prompt 构建器

    规则:
    - 只包含用户原话 (防止幻觉)
    - 清晰分隔
    - 标注来源日期
    """

    @staticmethod
    def build_injection_prompt(memory_context: str) -> str:
        """
        构建完整的记忆注入 Prompt

        Args:
            memory_context: 原始记忆上下文 (包含格式化的用户原话)

        Returns:
            格式化后的 Prompt 字符串
        """
        if not memory_context:
            # 没有记忆时，也要注入规则防止编造
            return """

## 记忆规则
当前没有关于用户的历史记忆。
如果用户问你关于他的信息（如名字、偏好、喜好等），直接回答"我没有相关记录"。
不要编造、猜测或推断任何用户信息。"""

        return f"""

## 用户历史记忆(仅限以下内容)
{memory_context}

【规则】
只能引用上面出现的原文内容回答。上面没有的信息一律回答"我没有相关记录"。"""
