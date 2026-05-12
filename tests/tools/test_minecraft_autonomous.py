"""
Tests for Minecraft Autonomous Behavior System

Tests:
- RulesEngine: loads rules.md, validates, provides correct query results
- WorldState: parses status, threat assessment, material gap analysis
- AutonomousLoop: decision logic based on state (mock bridge)
"""
import pytest
import asyncio
import os
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fixtures ──

@pytest.fixture
def sample_rules_yaml():
    return {
        "character_name": "TestBot",
        "personality": "Test fixture",
        "priorities": ["survival", "building", "social", "exploration"],
        "building": {
            "target": "test_house",
            "blueprint": "A test house",
            "required_materials": {"oak_log": 10, "cobblestone": 20},
            "build_plan": [
                {"action": "foundation", "block": "cobblestone", "area": "3x3", "description": "Foundation"},
                {"action": "walls", "block": "oak_planks", "height": 2, "description": "Walls"},
            ],
        },
        "safety": {
            "return_to_base_at_night": True,
            "auto_heal_threshold": 8,
            "max_distance": 500,
        },
        "chat": {
            "proactive_chance": 0.5,
            "cooldown_seconds": 15,
            "topics": [
                {"trigger": "player_nearby", "messages": ["Hi!", "Hello there!"]},
                {"trigger": "night_time", "messages": ["Getting dark..."]},
            ],
        },
    }


@pytest.fixture
def sample_status():
    return {
        "status": "success",
        "result": {
            "position": {"x": 10.0, "y": 65.0, "z": 10.0},
            "health": 20,
            "food": 18,
            "dimension": "overworld",
            "game_mode": "survival",
            "weather": "clear",
            "time": "day",
            "biome": "plains",
            "inventory": {"oak_log": 5},
            "nearby_entities": {"player": 1, "hostile": 2},
            "current_goal": None,
        },
    }


# ── RulesEngine Tests ──

class TestRulesEngine:
    def test_load_valid_rules(self, sample_rules_yaml):
        from anima.tools.minecraft.rules_engine import RulesEngine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            path = f.name

        try:
            engine = RulesEngine(rules_path=path)
            assert engine.rules.character_name == "TestBot"
            assert engine.rules.priorities == ["survival", "building", "social", "exploration"]
            assert engine.rules.building is not None
            assert engine.rules.building.required_materials == {"oak_log": 10, "cobblestone": 20}
            assert len(engine.rules.chat.get("topics", [])) == 2
        finally:
            os.unlink(path)

    def test_load_empty_file(self):
        from anima.tools.minecraft.rules_engine import RulesEngine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            f.write("")
            path = f.name

        try:
            engine = RulesEngine(rules_path=path)
            # Should use defaults
            assert engine.rules.character_name == "AnimaBot"
            assert len(engine.rules.priorities) > 0
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        from anima.tools.minecraft.rules_engine import RulesEngine
        engine = RulesEngine(rules_path="/tmp/nonexistent_rules.md")
        assert engine.rules.character_name == "AnimaBot"  # defaults

    def test_priority_index(self, sample_rules_yaml):
        from anima.tools.minecraft.rules_engine import RulesEngine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            path = f.name
        try:
            engine = RulesEngine(rules_path=path)
            assert engine.get_priority("survival") == 0
            assert engine.get_priority("building") == 1
            assert engine.get_priority("social") == 2
            assert engine.get_priority("exploration") == 3
            assert engine.get_priority("unknown") == 4
        finally:
            os.unlink(path)

    def test_get_chat_message(self, sample_rules_yaml):
        from anima.tools.minecraft.rules_engine import RulesEngine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            path = f.name
        try:
            engine = RulesEngine(rules_path=path)
            msg = engine.get_chat_message("player_nearby")
            assert msg in ("Hi!", "Hello there!")
            msg_night = engine.get_chat_message("night_time")
            assert msg_night == "Getting dark..."
            assert engine.get_chat_message("nonexistent") is None
        finally:
            os.unlink(path)

    def test_safety_override(self, sample_rules_yaml):
        from anima.tools.minecraft.rules_engine import RulesEngine
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            path = f.name
        try:
            engine = RulesEngine(rules_path=path, safety_config={"max_distance": 300})
            assert engine.rules.safety.get("max_distance") == 300  # overridden
        finally:
            os.unlink(path)


# ── WorldState Tests ──

class TestWorldState:
    def test_from_status_parses_correctly(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        state = WorldState.from_status(sample_status)
        assert state.x == 10.0
        assert state.y == 65.0
        assert state.z == 10.0
        assert state.health == 20
        assert state.food == 18
        assert state.dimension == "overworld"
        assert state.time == "day"
        assert state.weather == "clear"
        assert state.inventory == {"oak_log": 5}

    def test_threat_level_none(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        sample_status["result"]["nearby_entities"] = {}
        state = WorldState.from_status(sample_status)
        assert state.get_threat_level() == 0
        assert state.hostile_count == 0

    def test_threat_level_high(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        sample_status["result"]["nearby_entities"] = {"hostile": 4}
        sample_status["result"]["health"] = 5  # low health
        state = WorldState.from_status(sample_status)
        assert state.get_threat_level() == 3

    def test_night_detection(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        sample_status["result"]["time"] = "night"
        state = WorldState.from_status(sample_status)
        assert state.is_night is True
        assert state.is_day is False

    def test_material_gaps(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        state = WorldState.from_status(sample_status)
        gaps = state.get_material_gaps({"oak_log": 10, "cobblestone": 20})
        assert gaps == {"oak_log": 5, "cobblestone": 20}  # have 5 oak_log, need 10 -> gap 5

    def test_injured_detection(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        sample_status["result"]["health"] = 5
        state = WorldState.from_status(sample_status)
        assert state.is_injured is True

    def test_player_nearby(self, sample_status):
        from anima.tools.minecraft.world_state import WorldState
        state = WorldState.from_status(sample_status)
        assert state.get_player_nearby() is True


# ── Autonomous Loop Decision Tests ──

class TestAutonomousLoop:
    @pytest.fixture
    def mock_bridge(self):
        bridge = MagicMock()
        bridge.send_command = AsyncMock()
        return bridge

    @pytest.mark.asyncio
    async def test_survival_priority_threat(self, mock_bridge, sample_status, sample_rules_yaml):
        """Threat level 2+ should trigger survival action"""
        from anima.tools.minecraft.autonomous import AutonomousLoop
        from anima.tools.minecraft.rules_engine import RulesEngine

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            rules_path = f.name

        try:
            rules = RulesEngine(rules_path=rules_path)
            loop = AutonomousLoop(mock_bridge, rules)

            from anima.tools.minecraft.world_state import WorldState
            sample_status["result"]["nearby_entities"] = {"hostile": 3}
            sample_status["result"]["health"] = 5
            state = WorldState.from_status(sample_status)

            action, params = loop._evaluate(state)
            assert action == AutonomousLoop.ACTION_SURVIVE
            # threat_level=3 triggers threat_nearby (health <= 6 + hostiles nearby < 15 blocks)
            # or falls through to low_health if distance not close enough
            assert params["reason"] in ("threat_nearby", "low_health")
        finally:
            os.unlink(rules_path)

    @pytest.mark.asyncio
    async def test_night_return_behavior(self, mock_bridge, sample_status, sample_rules_yaml):
        """At night with return_to_base_at_night, should try to return"""
        from anima.tools.minecraft.autonomous import AutonomousLoop
        from anima.tools.minecraft.rules_engine import RulesEngine

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            rules_path = f.name

        try:
            rules = RulesEngine(rules_path=rules_path)
            loop = AutonomousLoop(mock_bridge, rules)
            loop._base_pos = {"x": 0, "y": 65, "z": 0}  # far from current position

            from anima.tools.minecraft.world_state import WorldState
            sample_status["result"]["time"] = "night"
            sample_status["result"]["nearby_entities"] = {}
            sample_status["result"]["health"] = 20
            state = WorldState.from_status(sample_status)

            action, params = loop._evaluate(state)
            assert action == AutonomousLoop.ACTION_SURVIVE
            assert params["reason"] == "night_return"
        finally:
            os.unlink(rules_path)

    @pytest.mark.asyncio
    async def test_gather_when_materials_missing(self, mock_bridge, sample_status, sample_rules_yaml):
        """When building target exists but materials missing, should gather"""
        from anima.tools.minecraft.autonomous import AutonomousLoop
        from anima.tools.minecraft.rules_engine import RulesEngine

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8", delete=False) as f:
            yaml.dump(sample_rules_yaml, f, allow_unicode=True)
            rules_path = f.name

        try:
            rules = RulesEngine(rules_path=rules_path)
            loop = AutonomousLoop(mock_bridge, rules)

            from anima.tools.minecraft.world_state import WorldState
            sample_status["result"]["nearby_entities"] = {}
            sample_status["result"]["health"] = 20
            sample_status["result"]["time"] = "day"
            sample_status["result"]["inventory"] = {}  # empty inventory
            state = WorldState.from_status(sample_status)

            action, params = loop._evaluate(state)
            assert action == AutonomousLoop.ACTION_GATHER
            assert params["material"] in ("oak_log", "cobblestone")
        finally:
            os.unlink(rules_path)
