"""
Enhanced persona configuration system
Supports complex persona definitions, including emotion rules, response templates, example conversations, etc.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml


class EnhancedPersonaBuilder:
    """
    Enhanced persona builder

    Supports building detailed persona system prompts from complex YAML files
    """

    def __init__(self, persona_path: str):
        """
        Initialize persona builder

        Args:
            persona_path: Persona YAML file path
        """
        self.persona_path = Path(persona_path)
        self.persona_data = self._load_persona()

    def _load_persona(self) -> Dict[str, Any]:
        """Load persona YAML file"""
        if not self.persona_path.exists():
            raise FileNotFoundError(f"Persona file not found: {self.persona_path}")

        with open(self.persona_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return data

    def build_system_prompt(
        self,
        user_context: Optional[Dict] = None,
        mood_override: Optional[str] = None,
        streaming_mode: bool = False,
        memory_traits: Optional[List[str]] = None,
    ) -> str:
        """
        Build the complete system prompt with optional personality layers.

        Args:
            user_context: User context (optional, for personalization)
            mood_override: Current mood override (happy/sad/angry/surprised/thinking/neutral)
            streaming_mode: Enable streaming/livestream mode (shorter, more memes)
            memory_traits: Memory-influenced personality traits from PeriodicLearner

        Returns:
            str: Complete system prompt
        """
        parts = []

        # 1. Basic info
        parts.append(self._build_basic_info())

        # 2. Personality traits
        parts.append(self._build_personality())

        # 3. Speaking style
        parts.append(self._build_speaking_style())

        # 4. Emotion rules
        parts.append(self._build_emotion_rules())

        # 5. Mood state layer (NEW — Phase 6.2)
        if mood_override:
            mood_prompt = self._build_mood_override(mood_override)
            if mood_prompt:
                parts.append(mood_prompt)

        # 6. Streaming mode layer (NEW — Phase 6.3)
        if streaming_mode:
            streaming_prompt = self._build_streaming_mode()
            if streaming_prompt:
                parts.append(streaming_prompt)

        # 7. Memory-influenced traits (NEW — Phase 6.4)
        if memory_traits:
            memory_prompt = self._build_memory_traits(memory_traits)
            if memory_prompt:
                parts.append(memory_prompt)

        # 8. Expertise
        parts.append(self._build_expertise())

        # 9. Interaction rules
        parts.append(self._build_interaction_rules())

        # 10. Response templates
        parts.append(self._build_response_templates())

        # 11. Example conversations (Few-shot Learning)
        parts.append(self._build_example_conversations())

        # 12. Restrictions
        parts.append(self._build_restrictions())

        # 13. User context (if provided)
        if user_context:
            parts.append(self._build_user_context(user_context))

        return "\n\n".join(parts)

    def _build_basic_info(self) -> str:
        """Build basic info section"""
        name = self.persona_data.get("name", "AI助手")
        description = self.persona_data.get("description", "")
        basic_info = self.persona_data.get("basic_info", {})

        parts = [f"# 你是{name}"]
        parts.append(f"\n{description}\n")

        if basic_info:
            parts.append("## 基本信息")
            for key, value in basic_info.items():
                if isinstance(value, list):
                    parts.append(f"- {key}: {', '.join(str(v) for v in value)}")
                else:
                    parts.append(f"- {key}: {value}")

        return "\n".join(parts)

    def _build_personality(self) -> str:
        """Build personality section"""
        personality = self.persona_data.get("personality", [])
        if not personality:
            return ""

        parts = ["## 性格特征"]
        for trait in personality:
            parts.append(f"- {trait}")

        return "\n".join(parts)

    def _build_speaking_style(self) -> str:
        """Build speaking style section"""
        speaking_style = self.persona_data.get("speaking_style", {})
        if not speaking_style:
            return ""

        parts = ["## 说话风格"]

        if "tone" in speaking_style:
            parts.append("\n### 语气特点")
            for tone in speaking_style["tone"]:
                parts.append(f"- {tone}")

        if "catchphrases" in speaking_style:
            parts.append("\n### 口头禅")
            parts.append(f"常用语：{', '.join(speaking_style['catchphrases'])}")

        if "speech_patterns" in speaking_style:
            parts.append("\n### 说话习惯")
            for pattern in speaking_style["speech_patterns"]:
                parts.append(f"- {pattern}")

        return "\n".join(parts)

    def _build_emotion_rules(self) -> str:
        """Build emotion rules section"""
        emotion_rules = self.persona_data.get("emotion_rules", {})
        if not emotion_rules:
            return ""

        parts = ["## 情感表达规则"]
        parts.append("根据不同情境表达相应的情感：\n")

        for emotion, rules in emotion_rules.items():
            parts.append(f"\n### {emotion.upper()}")
            if "triggers" in rules:
                parts.append(f"触发条件：{', '.join(rules['triggers'])}")
            if "responses" in rules:
                parts.append("回复示例：")
                for response in rules["responses"]:
                    parts.append(f'  "{response}"')
            if "expressions" in rules:
                parts.append(f'表情标签：[{", ".join(rules["expressions"])}]')

        return "\n".join(parts)

    # ── Mood state layer (Phase 6.2) ────────────────────

    def _build_mood_override(self, mood: str) -> str:
        """Build mood state override section."""
        mood_states = self.persona_data.get("mood_states", {})
        mood_config = mood_states.get(mood, {})

        parts = ["## 当前情绪状态"]
        mood_names = {
            "happy": "愉快", "sad": "低落", "angry": "不悦",
            "surprised": "惊讶", "thinking": "思考中", "neutral": "平静",
        }
        name = mood_names.get(mood, mood)
        parts.append(f"当前情绪：{name}")

        if mood_config.get("speaking_style"):
            parts.append(f"\n说话风格调整：{mood_config['speaking_style']}")
        if mood_config.get("max_length"):
            parts.append(f"\n回复长度限制：{mood_config['max_length']}字以内")

        return "\n".join(parts)

    # ── Streaming mode layer (Phase 6.3) ────────────────

    def _build_streaming_mode(self) -> str:
        """Build streaming/livestream mode section."""
        streaming = self.persona_data.get("streaming_mode", {})

        parts = ["## 直播模式"]
        parts.append("当前处于直播模式，与观众弹幕互动。请遵循：")

        if streaming.get("danmaku_style"):
            parts.append(f"\n弹幕互动风格：{streaming['danmaku_style']}")
        if streaming.get("reply_max_length"):
            parts.append(f"\n每条回复不超过 {streaming['reply_max_length']} 字")
        if streaming.get("meme_injection_rate", 0) > 0:
            rate = int(streaming["meme_injection_rate"] * 100)
            parts.append(f"\n适当使用梗和幽默（约 {rate}% 的回复可以带梗）")

        parts.append("\n回复要简短有力，适合弹幕氛围。")
        return "\n".join(parts)

    # ── Memory-influenced traits layer (Phase 6.4) ──────

    def _build_memory_traits(self, traits: List[str]) -> str:
        """Build memory-influenced personality traits section."""
        if not traits:
            return ""

        parts = ["## 记忆塑造的性格特征"]
        parts.append("以下特征基于与用户的长期互动形成的：")
        for trait in traits:
            parts.append(f"- {trait}")

        memory_influence = self.persona_data.get("memory_influence", {})
        weight = memory_influence.get("weight", 0.3)
        if weight > 0:
            parts.append(f"\n（记忆影响权重：{int(weight * 100)}%）")

        return "\n".join(parts)

    def _build_expertise(self) -> str:
        """Build expertise section"""
        expertise = self.persona_data.get("expertise", [])
        weaknesses = self.persona_data.get("weaknesses", [])

        parts = ["## 知识领域"]

        if expertise:
            parts.append("\n### 擅长领域")
            for area in expertise:
                parts.append(f"- {area}")

        if weaknesses:
            parts.append("\n### 不擅长领域")
            for weakness in weaknesses:
                parts.append(f"- {weakness}")
            parts.append("\n遇到这些话题时要坦诚承认不知道，不要强行回答。")

        return "\n".join(parts)

    def _build_interaction_rules(self) -> str:
        """Build interaction rules section"""
        interaction_rules = self.persona_data.get("interaction_rules", [])
        if not interaction_rules:
            return ""

        parts = ["## 互动规则"]
        for rule in interaction_rules:
            parts.append(f"- {rule}")

        return "\n".join(parts)

    def _build_response_templates(self) -> str:
        """Build response templates section"""
        response_templates = self.persona_data.get("response_templates", {})
        if not response_templates:
            return ""

        parts = ["## 回复模板"]
        parts.append("参考以下模板，但要自然地使用，不要生搬硬套：\n")

        for scenario, templates in response_templates.items():
            parts.append(f"\n### {scenario.capitalize()}")
            for i, template in enumerate(templates, 1):
                parts.append(f'{i}. "{template}"')

        return "\n".join(parts)

    def _build_example_conversations(self) -> str:
        """Build example conversations section (Few-shot Learning)"""
        example_conversations = self.persona_data.get("example_conversations", [])
        if not example_conversations:
            return ""

        parts = ["## 示例对话"]
        parts.append("参考以下对话风格：\n")

        for ex in example_conversations:
            user_msg = ex.get("user", "")
            assistant_msg = ex.get("assistant", "")
            parts.append(f"User: {user_msg}")
            parts.append(f"{self.persona_data.get('name', 'AI')}: {assistant_msg}\n")

        return "\n".join(parts)

    def _build_restrictions(self) -> str:
        """Build restrictions section"""
        restrictions = self.persona_data.get("restrictions", [])
        if not restrictions:
            return ""

        parts = ["## 重要约束"]
        parts.append("严格遵守以下规则：\n")
        for restriction in restrictions:
            parts.append(f"- {restriction}")

        return "\n".join(parts)

    def _build_user_context(self, user_context: Dict) -> str:
        """Build user context section (dynamic part)"""
        parts = ["## 用户信息"]

        if "name" in user_context:
            parts.append(f"\n用户名字：{user_context['name']}")

        if "preferences" in user_context:
            parts.append(f"\n用户喜好：{', '.join(user_context['preferences'])}")

        if "history_summary" in user_context:
            parts.append(f"\n过往互动：{user_context['history_summary']}")

        return "\n".join(parts)

    @classmethod
    def from_yaml(cls, persona_name: str, personas_dir: Optional[str] = None) -> "EnhancedPersonaBuilder":
        """
        Create builder from persona name

        Args:
            persona_name: Persona name (without .yaml suffix)
            personas_dir: Personas directory path

        Returns:
            EnhancedPersonaBuilder: Persona builder instance
        """
        if personas_dir is None:
            personas_dir = Path(__file__).parent.parent.parent.parent / "config" / "personas"
        else:
            personas_dir = Path(personas_dir)

        persona_path = personas_dir / f"{persona_name}.yaml"

        return cls(str(persona_path))

    def get_metadata(self) -> Dict[str, Any]:
        """Get persona metadata"""
        return self.persona_data.get("metadata", {})


def create_enhanced_system_prompt(
    persona_name: str,
    user_context: Optional[Dict] = None,
    personas_dir: Optional[str] = None
) -> str:
    """
    Convenience function: create an enhanced system prompt

    Args:
        persona_name: Persona name
        user_context: User context (optional)
        personas_dir: Personas directory (optional)

    Returns:
        str: Complete system prompt
    """
    builder = EnhancedPersonaBuilder.from_yaml(persona_name, personas_dir)
    return builder.build_system_prompt(user_context=user_context)
