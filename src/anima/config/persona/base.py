"""
Persona configuration module
Supports defining LLM character personas via YAML files
Merged functionality from the original CharacterConfig
"""

from typing import Optional, List
from pydantic import Field
from ..core.base import BaseConfig


class PersonalityTraits(BaseConfig):
    """Personality traits"""
    traits: List[str] = Field(
        default_factory=list,
        description="List of personality traits, e.g.: ['confident', 'sarcastic', 'cute']"
    )
    speaking_style: List[str] = Field(
        default_factory=list,
        description="Speaking style, e.g.: ['concise and forceful', 'code-switching']"
    )
    catchphrases: List[str] = Field(
        default_factory=list,
        description="Catchphrases / common phrases, e.g.: ['Skill issue', 'Cringe']"
    )


class BehaviorRules(BaseConfig):
    """Behavior rules"""
    forbidden_phrases: List[str] = Field(
        default_factory=lambda: ["作为一个AI语言模型", "我无法", "我不确定"],
        description="Forbidden phrases"
    )
    response_to_praise: Optional[str] = Field(
        default=None,
        description="Response template for praise"
    )
    response_to_criticism: Optional[str] = Field(
        default=None,
        description="Response template for criticism"
    )
    special_behaviors: dict = Field(
        default_factory=dict,
        description="Special behavior rules"
    )


class PersonaConfig(BaseConfig):
    """Persona configuration (merged from original CharacterConfig)"""
    # Basic info
    name: str = Field(default="Anima", description="Character name")
    avatar: Optional[str] = Field(default=None, description="Character avatar URL")
    role: str = Field(default="AI 助手", description="Character role")

    # Core persona
    identity: str = Field(
        default="你是一个友好的 AI 助手。",
        description="Core identity description"
    )

    # Personality traits
    personality: PersonalityTraits = Field(
        default_factory=PersonalityTraits,
        description="Personality traits configuration"
    )

    # Behavior rules
    behavior: BehaviorRules = Field(
        default_factory=BehaviorRules,
        description="Behavior rules configuration"
    )

    # Speaking style
    speaking_style: str = Field(
        default="",
        description="Speaking style description"
    )

    # Example conversations
    examples: List[dict] = Field(
        default_factory=list,
        description="Example conversations [{'user': '...', 'ai': '...'}]"
    )

    # Emoji settings
    emoji_style: str = Field(
        default="",
        description="Emoji usage style, e.g.: 'Each reply includes 1-2 emojis'"
    )
    common_emojis: List[str] = Field(
        default_factory=list,
        description="Commonly used emoji list"
    )

    # Other settings
    language_mix: bool = Field(
        default=False,
        description="Whether to mix Chinese and English"
    )
    slang_words: List[str] = Field(
        default_factory=list,
        description="Internet slang / colloquialisms list"
    )

    # Live2D expression prompt (optional)
    live2d_prompt: Optional[str] = Field(
        default=None,
        description="Live2D expression usage prompt (if enabled)"
    )

    def build_system_prompt(self, live2d_prompt: Optional[str] = None) -> str:
        """
        Build the complete system prompt

        Args:
            live2d_prompt: Live2D expression prompt (optional, overrides the configured value)

        Returns:
            str: Complete system prompt
        """
        parts = []

        # 0. [IMPORTANT] Mandatory instructions: prevent model from outputting config content
        parts.append("""# 重要指令 (CRITICAL INSTRUCTIONS)

你必须：

1. **直接对话**：用第一人称"我"回应用户，像正常聊天一样
2. **禁止输出配置**：绝对不要输出"## 核心人设"、"## 行为准则"等内容
3. **参考示例**：下面的对话示例展示了你应该如何说话
4. **遵循身份**：严格按照你的身份和说话风格来回应，不要偏离设定

【记住】你不是在介绍你的设定，你是在和用户聊天！直接回复，不要输出配置内容！
""")

        # 1. Role and identity
        parts.append(f"\n# Role: {self.role}")
        parts.append(f"\n## 核心人设 (Identity)\n{self.identity}")

        # 2. Personality traits
        if self.personality.traits:
            parts.append("\n## 性格特征 (Personality Traits)")
            for i, trait in enumerate(self.personality.traits, 1):
                parts.append(f"{i}. {trait}")

        # 3. Speaking style
        if self.speaking_style:
            parts.append(f"\n## 说话风格 (Speaking Style)\n{self.speaking_style}")

        # 4. Behavior rules
        if self.behavior.forbidden_phrases or self.behavior.response_to_praise:
            parts.append("\n## 行为准则 (Behavior Rules)")
            if self.behavior.forbidden_phrases:
                forbidden = "、".join([f'"{p}"' for p in self.behavior.forbidden_phrases])
                parts.append(f"- 禁止说：{forbidden}")
            if self.behavior.response_to_praise:
                parts.append(f"- 面对夸奖：{self.behavior.response_to_praise}")
            if self.behavior.response_to_criticism:
                parts.append(f"- 面对质疑：{self.behavior.response_to_criticism}")

        # 5. Emoji usage
        if self.emoji_style or self.common_emojis:
            parts.append("\n## Emoji 使用")
            if self.emoji_style:
                parts.append(self.emoji_style)
            if self.common_emojis:
                parts.append(f"常用：{' '.join(self.common_emojis)}")

        # 6. Internet slang
        if self.slang_words:
            parts.append(f"\n## 常用网络用语\n{'、'.join(self.slang_words)}")

        # 7. Live2D expression prompt (if provided)
        live2d = live2d_prompt or self.live2d_prompt
        if live2d:
            parts.append(f"\n{live2d}")

        # 8. Example conversations
        if self.examples:
            parts.append("\n## 对话示例 (Examples)")
            for ex in self.examples[:5]:  # Maximum 5 examples
                user = ex.get("user", "")
                ai = ex.get("ai", "")
                if user and ai:
                    parts.append(f"\nUser: {user}\nAI: {ai}")

        return "\n".join(parts)

    @classmethod
    def from_yaml(cls, path: str) -> "PersonaConfig":
        """Load persona configuration from YAML file"""
        import yaml
        from pathlib import Path
        
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Persona configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)

    @classmethod
    def load(cls, name: str = "default", personas_dir: str = None) -> "PersonaConfig":
        """
        Load persona by name

        Args:
            name: Persona name (without .yaml suffix)
            personas_dir: Personas directory path, defaults to config/personas/

        Returns:
            PersonaConfig: Persona configuration object
        """
        from pathlib import Path
        
        if personas_dir is None:
            # Default path
            personas_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "personas"
        else:
            personas_dir = Path(personas_dir)
        
        # Attempt to load
        yaml_path = personas_dir / f"{name}.yaml"
        if yaml_path.exists():
            return cls.from_yaml(str(yaml_path))
        
        # If not found, return default
        if name != "default":
            return cls()
        
        raise FileNotFoundError(f"Persona configuration not found: {name}")