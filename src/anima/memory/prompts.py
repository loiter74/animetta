"""
记忆模块 Prompt 模板

包含记忆口语化转换的 Prompt 模板。
"""

from typing import Optional


class MemoryPrompts:
    """记忆相关 Prompt 模板"""

    # 口语化记忆转换 Prompt
    ORAL_MEMORY_TEMPLATE = """你是一个记忆整理助手。请把以下对话内容转换为第一人称的口语化记忆表达。

规则：
1. 用"我记得"、"你之前提到过"、"我们上次聊过"等自然句式
2. 保留关键信息，不要添加或歪曲原意
3. 只输出转换后的文本，不要输出任何解释
4. 控制在1-2句话以内

原始对话：{original_text}
口语化记忆："""

    @staticmethod
    def build_oral_memory_prompt(original_text: str) -> str:
        """
        构建口语化记忆转换的 Prompt

        Args:
            original_text: 原始对话文本

        Returns:
            完整的 Prompt 字符串
        """
        return MemoryPrompts.ORAL_MEMORY_TEMPLATE.format(
            original_text=original_text
        )
