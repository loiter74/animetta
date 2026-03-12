"""
Preset Loader
加载 Live2D 动作预设配置（YAML 格式）
参考 open-yachiyo 的 live2d-presets.yaml
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

from .action_queue import ActionFactory, ActionMessage


@dataclass
class EmotePreset:
    """情感预设"""
    name: str
    intensity: str  # low, medium, high
    expression: str
    params: List[Dict[str, Any]]


@dataclass
class GesturePreset:
    """手势预设"""
    name: str
    expression: Optional[str]
    motion_group: Optional[str]
    motion_index: Optional[int]


@dataclass
class ReactPreset:
    """反应预设"""
    name: str
    actions: List[Dict[str, Any]]


class PresetLoader:
    """
    Live2D 预设加载器

    从 YAML 文件加载表情、手势和反应预设
    """

    def __init__(self, config_path: str = None):
        """
        初始化预设加载器

        Args:
            config_path: 预设配置文件路径
        """
        if config_path is None:
            # 默认路径
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "config" / "live2d-presets.yaml"

        self.config_path = Path(config_path)
        self.presets: Dict[str, Any] = {}
        self._load_presets()

    def _load_presets(self):
        """加载预设文件"""
        if not self.config_path.exists():
            logger.warning(f"[PresetLoader] 预设文件不存在: {self.config_path}")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.presets = yaml.safe_load(f)
            logger.info(f"[PresetLoader] 预设加载成功: {self.config_path}")
        except Exception as e:
            logger.error(f"[PresetLoader] 预设加载失败: {e}")

    def get_emote(self, emotion: str, intensity: str = "medium") -> Optional[Dict]:
        """
        获取情感预设

        Args:
            emotion: 情感名称 (e.g., "happy", "sad")
            intensity: 强度 ("low", "medium", "high")

        Returns:
            预设数据
        """
        emote_presets = self.presets.get('emote', {})
        emotion_data = emote_presets.get(emotion, {})
        intensity_data = emotion_data.get(intensity)

        if not intensity_data:
            # 尝试使用 medium 作为默认
            intensity_data = emotion_data.get('medium')

        return intensity_data

    def get_gesture(self, gesture_name: str) -> Optional[Dict]:
        """
        获取手势预设

        Args:
            gesture_name: 手势名称 (e.g., "greet", "think")

        Returns:
            预设数据
        """
        gesture_presets = self.presets.get('gesture', {})
        return gesture_presets.get(gesture_name)

    def get_react(self, react_name: str) -> Optional[List[Dict]]:
        """
        获取反应预设

        Args:
            react_name: 反应名称 (e.g., "success", "error")

        Returns:
            动作列表
        """
        react_presets = self.presets.get('react', {})
        return react_presets.get(react_name)

    def create_emote_action(self, emotion: str, intensity: str = "medium") -> Optional[ActionMessage]:
        """
        创建情感动作

        Args:
            emotion: 情感名称
            intensity: 强度

        Returns:
            动作消息
        """
        preset = self.get_emote(emotion, intensity)
        if not preset:
            return None

        # 创建动作
        actions = []

        # 表情
        expression = preset.get('expression')
        if expression:
            actions.append({
                "type": "expression",
                "name": expression
            })

        # 参数
        params = preset.get('params', [])
        for param in params:
            actions.append({
                "type": "param",
                "name": param.get('name'),
                "value": param.get('value')
            })

        # 如果有多个动作，包装成序列
        if len(actions) > 1:
            return ActionFactory.sequence(actions, 0.5)
        elif actions:
            return ActionMessage(
                action_id=f"emote_{emotion}_{intensity}",
                action=actions[0],
                duration_sec=0.3
            )

        return None

    def create_gesture_action(self, gesture_name: str) -> Optional[ActionMessage]:
        """
        创建手势动作

        Args:
            gesture_name: 手势名称

        Returns:
            动作消息
        """
        preset = self.get_gesture(gesture_name)
        if not preset:
            return None

        actions = []

        # 表情
        expression = preset.get('expression')
        if expression:
            actions.append({
                "type": "expression",
                "name": expression
            })

        # 动作
        motion = preset.get('motion')
        if motion:
            actions.append({
                "type": "motion",
                "group": motion.get('group'),
                "index": motion.get('index')
            })

        if len(actions) > 1:
            return ActionFactory.sequence(actions, 1.0)
        elif actions:
            return ActionMessage(
                action_id=f"gesture_{gesture_name}",
                action=actions[0],
                duration_sec=0.8
            )

        return None

    def create_react_action(self, react_name: str) -> Optional[ActionMessage]:
        """
        创建反应动作

        Args:
            react_name: 反应名称

        Returns:
            动作消息（序列）
        """
        preset = self.get_react(react_name)
        if not preset:
            return None

        # 计算总时长
        total_duration = 0
        for action in preset:
            if action.get('type') == 'wait':
                total_duration += action.get('ms', 0) / 1000
            else:
                total_duration += 0.3  # 默认动作时长

        return ActionMessage(
            action_id=f"react_{react_name}",
            action={
                "type": "sequence",
                "actions": preset
            },
            duration_sec=total_duration
        )

    def list_emotes(self) -> List[str]:
        """列出所有可用的情感"""
        return list(self.presets.get('emote', {}).keys())

    def list_gestures(self) -> List[str]:
        """列出所有可用的手势"""
        return list(self.presets.get('gesture', {}).keys())

    def list_reacts(self) -> List[str]:
        """列出所有可用的反应"""
        return list(self.presets.get('react', {}).keys())


# 全局实例
_preset_loader: Optional[PresetLoader] = None


def get_preset_loader() -> PresetLoader:
    """获取全局预设加载器实例"""
    global _preset_loader
    if _preset_loader is None:
        _preset_loader = PresetLoader()
    return _preset_loader
