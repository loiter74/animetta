"""
Memory module prompt templates

Contains prompt templates for memory colloquialization conversion.
"""

from typing import Optional


class MemoryPrompts:
    """Memory-related prompt templates"""

    # Oral memory conversion prompt
    ORAL_MEMORY_TEMPLATE = """你是一个记忆整理助手。请把以下对话内容转换为第一人称的口语化记忆表达。

规则:
1. 用"我记得"、"你之前提到过"、"我们上次聊过"等自然句式
2. 保留关键信息，不要添加或歪曲原意
3. 只输出转换后的文本，不要输出任何解释
4. 控制在1-2句话以内

原始对话：{original_text}
"""

    @staticmethod
    def build_oral_memory_prompt(original_text: str) -> str:
        """
        Build a prompt for colloquial memory conversion

        Args:
            original_text: Original conversation text

        Returns:
            Complete prompt string
        """
        return MemoryPrompts.ORAL_MEMORY_TEMPLATE.format(
            original_text=original_text
        )
