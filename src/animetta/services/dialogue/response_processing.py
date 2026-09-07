"""Pure visible-reply and speech-text processing shared by dialogue paths."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from animetta.avatar.performance import parse_performance_plan

from .reasoning_classifier import is_english_meta_reasoning

AFFINITY_MIN = 0
AFFINITY_MAX = 100

FALLBACK_RESPONSE = "I need a moment to think about that."

_THINKING_BLOCK_RE = re.compile(
    r"(?is)<(?:think|thinking)\b[^>]*>.*?</(?:think|thinking)>"
    r"|\[(?:think|thinking)\].*?\[/(?:think|thinking)\]"
)

_ORPHAN_THINKING_PREFIX_RE = re.compile(
    r"(?is)^.*?(?:</(?:think|thinking)>|\[/(?:think|thinking)\])\s*"
)

_LEADING_RESPONSE_TAG_RE = re.compile(
    r"(?is)^\s*(?:(?:<(?:think|thinking)\b[^>]*>)|"
    r"\[(?:think|thinking|happy|sad|angry|neutral|surprised)\])\s*"
)

_UNTAGGED_REASONING_PREFIX_RE = re.compile(
    r"(?is)^\s*"
    r"(?=(?:the user\s+(?:just\s+)?(?:says|said|asks|asked|wants|is)\b|"
    r"user\s+(?:says|said|asks|asked|wants|is)\b|"
    r"as an?\b|i should\b|let me\b))"
    r"(?=.*\b(?:i should|let me|actually|respond in character|"
    r"not a minecraft command|usual style)\b)"
    r".*[.!?](?:\s+|(?=[\"“]))"
    r"(?P<answer>(?:[\u4e00-\u9fff]|[\"“][^\"”\r\n]{1,64}[\"”]\s*"
    r"(?:[-—–:：]+\s*)?[\u4e00-\u9fff])[\s\S]*)$"
)

_CHINESE_UNTAGGED_REASONING_PREFIX_RE = re.compile(
    r"(?s)^\s*"
    r"(?=(?:用户(?:问|说|想|要|发|在)|作为AI|作为Anima|我(?:需要|应该|知道|可以|得)|这个问题|实际上))"
    r"(?=.*(?:作为AI|作为Anima|符合人设|对话历史|方式来回应|假装记得|保持神秘感|这是个测试|实际上))"
    r".*?[。！？]\s*"
    r"(?P<answer>(?:上一个话题|我的数据库告诉你|你(?:刚才|上次|刚刚)|哎呀|这就|赛博酒馆|后厨|牛到了|欢迎光临|来都来了)[\s\S]*)$"
)

_CHINESE_REASONING_START_RE = re.compile(
    r"^\s*(?:用户|旅人(?:问|说|想|要|发|在|继续|再次|测试|表示|让)|"
    r"作为(?:AI|Anima)|我(?:需要|应该|知道|可以|得)|"
    r"用[^。！？]{0,60}世界观[^。！？]{0,30}(?:包装|回答|回应)|这个问题|"
    r"保持[^。！？]{0,80}风格)"
)

_CHINESE_SENTENCE_RE = re.compile(r"[^。！？]*[。！？]\s*")

_CHINESE_REASONING_SIGNAL_RE = re.compile(
    r"(?:用户|旅人(?:问|说|想|要|发|在|继续|再次|测试|表示|让)|"
    r"作为AI|作为Anima|作为[^。！？]{0,20}AI|AI VTuber|我是Anima|让我想想|"
    r"我(?:需要|应该|知道|可以|得)|符合人设|对话历史|方式来回应|方式回应|"
    r"假装记得|保持神秘感|这是(?:个)?测试|实际上|弹幕|轻吐槽|自然收住|"
    r"调用工具|不要解释|不要写分析|不要跳出角色|角色内|保持[^。！？]{0,30}语气|"
    r"好感(?:度|值)?[^。！？\d]{0,16}\d*|亲密度[^。！？\d]{0,16}\d*|"
    r"风格\s*[:：]|表情标签|用[^。！？]{0,60}世界观[^。！？]{0,30}(?:包装|回答|回应)|"
    r"适合用[^。！？]{0,80}来处理|身份接住|先[^。！？]{0,40}再[^。！？]{0,40}(?:最后|收尾)|"
    r"连续对话检查|承认上下文|保持角色感|这个问题(?:有点意思|偏[^。！？]{0,40}类)|"
    r"不需要搜索|直接用自己的知识回答|每条回复必须|保持[^。！？]{0,80}风格)"
)

_CHINESE_INLINE_PLANNING_SENTENCE_RE = re.compile(
    r"\s*(?:然后|再)套(?:一下)?世界观"
    r"(?:（[^。！？）]{0,40}）|\([^.!?)]{0,40}\))?，?\s*"
    r"最后(?:再)?(?:轻轻)?接住[。！？]\s*"
)

_CHINESE_INCOMPLETE_REASONING_RE = re.compile(
    r"^(?:好感(?:度|值)?|亲密度|情绪(?:标签)?|表情(?:标签)?)\s*(?::|：)?\s*\d*\s*$"
)

_INVISIBLE_FORMATTING_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")

_AFFINITY_MARKER_RE = re.compile(r"\[affinity:(-?\d+)\]")

_SENTENCE_END_RE = re.compile(r"([^。！？!?]+)([。！？!?])")


def _strip_emotion_tags(text: str) -> str:
    """Remove bounded performance and legacy emotion tags from visible text."""
    return parse_performance_plan(text).cleaned_text


def _strip_model_thinking(text: str) -> str:
    """Remove provider-emitted thinking blocks before exposing visible replies."""
    if not text:
        return text

    text = _INVISIBLE_FORMATTING_RE.sub("", text)
    stripped = _THINKING_BLOCK_RE.sub("", text)
    stripped = _ORPHAN_THINKING_PREFIX_RE.sub("", stripped, count=1)
    # Providers occasionally emit an unclosed leading ``[thinking]`` or
    # ``<think>`` tag. Remove only the leading tag, then classify the body;
    # in-character emotion-tagged replies keep their visible text.
    stripped = _LEADING_RESPONSE_TAG_RE.sub("", stripped, count=1)
    match = _UNTAGGED_REASONING_PREFIX_RE.match(stripped)
    if match:
        stripped = match.group("answer")
    else:
        stripped = _strip_chinese_untagged_reasoning_prefix(stripped)
        if is_english_meta_reasoning(_AFFINITY_MARKER_RE.sub("", stripped)):
            return ""
    stripped = _CHINESE_INLINE_PLANNING_SENTENCE_RE.sub("", stripped)
    return stripped.strip()


def _visible_response_or_fallback(text: str) -> str:
    """Return a user-visible response, never an empty stripped reasoning trace."""
    return _strip_model_thinking(text) or FALLBACK_RESPONSE


def _has_user_visible_response(text: str | None) -> bool:
    """Return whether provider output contains text after all delivery markers are removed."""
    if not text:
        return False
    stripped = _strip_model_thinking(text)
    stripped = _AFFINITY_MARKER_RE.sub("", stripped)
    return bool(_strip_emotion_tags(stripped))


def _strip_chinese_untagged_reasoning_prefix(text: str) -> str:
    """Strip Chinese meta-reasoning sentences before the visible character reply."""
    if not _CHINESE_REASONING_START_RE.match(text):
        return text

    unambiguous_user_prefix = text.lstrip().startswith("用户")
    pos = 0
    reasoning_sentence_count = 0
    while match := _CHINESE_SENTENCE_RE.match(text, pos):
        sentence = match.group(0)
        if not _CHINESE_REASONING_SIGNAL_RE.search(sentence):
            break
        reasoning_sentence_count += 1
        pos = match.end()

    if reasoning_sentence_count >= 2 or (reasoning_sentence_count >= 1 and unambiguous_user_prefix):
        remainder = text[pos:].lstrip()
        if not remainder or _CHINESE_INCOMPLETE_REASONING_RE.fullmatch(remainder):
            return ""
        return remainder

    fallback_match = _CHINESE_UNTAGGED_REASONING_PREFIX_RE.match(text)
    if fallback_match:
        return fallback_match.group("answer")
    return text


def _enforce_persona_verbal_tics(response_text: str, system_prompt: str | None) -> str:
    """Apply explicit persona verbal-tic hard rules to visible replies.

    This is intentionally narrow: it only handles the Anima v0.1-style
    "每一句话后面都要加上喵" rule when it appears in the compiled prompt.
    """
    if not response_text or not system_prompt:
        return response_text
    if "每一句话后面都要加上喵" not in system_prompt:
        return response_text

    def _add_nya(match: re.Match[str]) -> str:
        body = match.group(1).rstrip()
        punct = match.group(2)
        if body.endswith("喵"):
            return f"{body}{punct}"
        return f"{body}喵{punct}"

    rewritten = _SENTENCE_END_RE.sub(_add_nya, response_text)
    if (
        rewritten == response_text
        and response_text.strip()
        and not response_text.rstrip().endswith("喵")
    ):
        return f"{response_text.rstrip()}喵"
    return rewritten


def extract_affinity(text: str | None, *, user_text: str = "") -> tuple[str | None, int | None]:
    """Return the last bounded affinity marker without mutating conversation state."""
    matches = _AFFINITY_MARKER_RE.findall(text or "")
    if not matches:
        return text, None
    value = max(AFFINITY_MIN, min(AFFINITY_MAX, int(matches[-1])))
    return (text if "【debug】" in user_text else _AFFINITY_MARKER_RE.sub("", text or "")), value


@dataclass(frozen=True, slots=True)
class ProcessedReply:
    text: str
    chunks: tuple[str, ...]
    affinity: int | None
    fallback: bool


def process_reply(
    text: str,
    *,
    user_text: str = "",
    system_prompt: str | None = None,
    chunks: Sequence[str] | None = None,
) -> ProcessedReply:
    """Apply the shared final reply policy, retaining the original chunk contract."""
    visible = _strip_model_thinking(text)
    fallback = not bool(_strip_emotion_tags(_AFFINITY_MARKER_RE.sub("", visible)))
    cleaned, affinity = extract_affinity(visible or FALLBACK_RESPONSE, user_text=user_text)
    original = cleaned or ""
    processed = _enforce_persona_verbal_tics(original, system_prompt)
    result_chunks = (
        (processed,)
        if chunks is None or processed != text or processed != original
        else tuple(_AFFINITY_MARKER_RE.sub("", chunk) for chunk in chunks)
    )
    return ProcessedReply(processed, result_chunks, affinity, fallback)


_EMOTION_TAG_RE = re.compile(r"\[[\w-]+\]")

_EMOJI_RE = re.compile(
    "[\U0001f600-\U0001f64f"  # Emoticons
    "\U0001f300-\U0001f5ff"  # Misc symbols & pictographs
    "\U0001f680-\U0001f6ff"  # Transport & map
    "\U0001f1e0-\U0001f1ff"  # Flags (regional indicators)
    "\U00002702-\U000027b0"  # Dingbats
    "\U0001f900-\U0001f9ff"  # Supplemental symbols
    "\U0001fa00-\U0001fa6f"  # Chess symbols
    "\U0001fa70-\U0001faff"  # Symbols extended-A
    "\U00002600-\U000026ff"  # Misc symbols
    "\U0000fe00-\U0000fe0f"  # Variation selectors
    "\U0000200d"  # Zero-width joiner
    "]"
)


def clean_text_for_tts(text: str) -> str:
    """Remove emoji and emotion tags from text before TTS synthesis."""
    text = parse_performance_plan(text).cleaned_text
    text = _EMOTION_TAG_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    # Collapse multiple spaces into one
    text = re.sub(r"  +", " ", text).strip()
    return text
