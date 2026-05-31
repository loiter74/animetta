#!/usr/bin/env python3
"""Add missing imports to test files by analyzing NameErrors."""
import ast
import os
import re

# Symbol → import module mapping
SYMBOL_IMPORT = {
    # Orchestration
    "create_initial_state": "from animetta.orchestration.graph.state import create_initial_state",
    "AgentState": "from animetta.orchestration.graph.state import AgentState",
    "emotion_node": "from animetta.orchestration.graph.emotion_node import emotion_node",
    "llm_node": "from animetta.orchestration.graph.llm_node import llm_node",
    "output_node": "from animetta.orchestration.graph.output_node import output_node",
    "tool_node": "from animetta.orchestration.graph.tool_node import tool_node",
    "tts_node": "from animetta.orchestration.graph.tts_node import tts_node",
    "asr_node": "from animetta.orchestration.graph.asr_node import asr_node",
    "personality_node": "from animetta.orchestration.graph.personality_node import personality_node",
    "MemoryMiddleware": "from animetta.orchestration.graph.memory_middleware import MemoryMiddleware",
    "LangGraphOrchestrator": "from animetta.orchestration.graph.orchestrator import LangGraphOrchestrator",
    "ToolManager": "from animetta.orchestration.graph.tool_manager import ToolManager",

    # Core
    "ServiceContext": "from animetta.core.service_context import ServiceContext",
    "ServicePool": "from animetta.core.service_pool import ServicePool",
    "AppConfig": "from animetta.config.app import AppConfig",
    "SystemConfig": "from animetta.config.system import SystemConfig",
    "AgentConfig": "from animetta.config.agent import AgentConfig",
    "PersonaConfig": "from animetta.config.persona import PersonaConfig",
    "UserSettings": "from animetta.config.user import UserSettings",
    "Live2DConfig": "from animetta.config.live2d import Live2DConfig",
    "ProviderRegistry": "from animetta.config.core.registry import ProviderRegistry",
    "ProviderConfig": "from animetta.config.core.base import ProviderConfig",

    # Avatar / Emotion
    "KeywordAnalyzer": "from animetta.avatar.analyzers.keyword import KeywordAnalyzer",
    "StandaloneLLMTagAnalyzer": "from animetta.avatar.analyzers.llm_tag import StandaloneLLMTagAnalyzer",
    "EmotionParamMapper": "from animetta.avatar.mappers.emotion_param_mapper import EmotionParamMapper",
    "EmotionPromptBuilder": "from animetta.avatar.prompts import EmotionPromptBuilder",
    "EmotionAnalyzerFactory": "from animetta.avatar.factory import EmotionAnalyzerFactory",
    "TimelineStrategyFactory": "from animetta.avatar.factory import TimelineStrategyFactory",
    "EmotionData": "from animetta.avatar.analyzers.base import EmotionData",
    "IEmotionAnalyzer": "from animetta.avatar.analyzers.base import IEmotionAnalyzer",

    # Strategies
    "PositionBasedStrategy": "from animetta.avatar.strategies.position import PositionBasedStrategy",
    "IntensityBasedStrategy": "from animetta.avatar.strategies.intensity import IntensityBasedStrategy",
    "DurationBasedStrategy": "from animetta.avatar.strategies.duration import DurationBasedStrategy",

    # LLM
    "LLMInterface": "from animetta.services.llm import LLMInterface",
    "LLMFactory": "from animetta.services.llm import LLMFactory",
    "MockLLM": "from animetta.services.llm import MockLLM",
    "GLMLLM": "from animetta.services.llm import GLMLLM",
    "OpenAILLM": "from animetta.services.llm import OpenAILLM",
    "OllamaLLM": "from animetta.services.llm import OllamaLLM",
    "LocalLoraLLM": "from animetta.services.llm import LocalLoraLLM",

    # TTS
    "TTSInterface": "from animetta.services.tts import TTSInterface",
    "TTSFactory": "from animetta.services.tts import TTSFactory",
    "MockTTS": "from animetta.services.tts import MockTTS",
    "EdgeTTS": "from animetta.services.tts import EdgeTTS",
    "GLMTTS": "from animetta.services.tts import GLMTTS",
    "KokoroTTS": "from animetta.services.tts import KokoroTTS",
    "Qwen3TTS": "from animetta.services.tts import Qwen3TTS",

    # ASR
    "ASRInterface": "from animetta.services.asr import ASRInterface",
    "ASRFactory": "from animetta.services.asr import ASRFactory",
    "MockASR": "from animetta.services.asr import MockASR",
    "GLMASR": "from animetta.services.asr import GLMASR",
    "FasterWhisperASR": "from animetta.services.asr import FasterWhisperASR",
    "FunASRASR": "from animetta.services.asr import FunASRASR",

    # VAD
    "VADInterface": "from animetta.services.vad import VADInterface",
    "VADFactory": "from animetta.services.vad import VADFactory",
    "MockVAD": "from animetta.services.vad import MockVAD",
    "SileroVAD": "from animetta.services.vad import SileroVAD",
    "VADState": "from animetta.services.vad import VADState",

    # Minecraft
    "MinecraftBridge": "from animetta.tools.minecraft.bridge import MinecraftBridge",
    "WorldState": "from animetta.tools.minecraft.world_state import WorldState",
    "ActionPlanner": "from animetta.tools.minecraft.planner import ActionPlanner",
    "MinecraftPlanner": "from animetta.tools.minecraft.planner import ActionPlanner",
    "AutonomousLoop": "from animetta.tools.minecraft.autonomous import AutonomousLoop",
    "CooldownTracker": "from animetta.tools.minecraft.autonomous import CooldownTracker",
    "RulesEngine": "from animetta.tools.minecraft.rules_engine import RulesEngine",
    "MinecraftConfig": "from animetta.tools.minecraft.config import MinecraftConfig",

    # Tools
    "calculator": "from animetta.tools import calculator",
    "MCPManager": "from animetta.tools import MCPManager",
    "MCPClient": "from animetta.tools.mcp_bridge import MCPClient",

    # Meme
    "DanmakuBuffer": "from animetta.services.meme.danmaku_buffer import DanmakuBuffer",
    "MemePool": "from animetta.services.meme import MemePool",
    "BilibiliCollector": "from animetta.services.meme.bilibili_collector import BilibiliCollector",
    "BilibiliInteraction": "from animetta.services.meme.bilibili_interaction import BilibiliInteraction",

    # Misc
    "EnvHelper": "from animetta.utils.env_helper import EnvHelper",
    "MemorySystem": "from animetta.memory.v2.system import LivingMemorySystem",
    "NotifierManager": "from animetta.notifier.manager import NotifierManager",
}

# Also fix old package name
OLD_NEW_PACKAGE = {
    "anima.config": "animetta.config",
    "anima.orchestration": "animetta.orchestration",
    "anima.services": "animetta.services",
    "anima.core": "animetta.core",
    "anima.memory": "animetta.memory",
    "anima.avatar": "animetta.avatar",
    "anima.tools": "animetta.tools",
}

def fix_file(filepath: str) -> int:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    original = content
    changes = 0

    # Fix old package names
    for old, new in OLD_NEW_PACKAGE.items():
        if old in content:
            content = content.replace(old, new)
            changes += 1

    # Find which symbols are used in this file
    # Parse module-level names used
    try:
        tree = ast.parse(content)
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
    except SyntaxError:
        return 0

    # Add imports for missing symbols
    imports_to_add = []
    for name in used_names:
        if name in SYMBOL_IMPORT and name[0].isupper():  # Only class/constant names
            imp = SYMBOL_IMPORT[name]
            if imp not in content:
                imports_to_add.append(imp)

    if imports_to_add:
        # Find where to insert (after last import)
        lines = content.split('\n')
        insert_at = 0
        in_imports = False
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                in_imports = True
                insert_at = i + 1
            elif in_imports and line.strip() == '':
                insert_at = i + 1
            elif in_imports and line.strip() and not line.startswith('#'):
                insert_at = i
                break

        for imp in sorted(set(imports_to_add)):
            lines.insert(insert_at, imp)
            insert_at += 1
            changes += 1

        content = '\n'.join(lines)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return changes


def main():
    total = 0
    for root, dirs, files in os.walk('tests'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith('.py') and f != '__init__.py':
                path = os.path.join(root, f)
                changes = fix_file(path)
                if changes:
                    total += changes
                    print(f"  [{changes:3d}] {path}")
    print(f"\nTotal: {total} changes")


if __name__ == '__main__':
    main()
