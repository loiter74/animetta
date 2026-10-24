"""A canopy spawn must not become the permanent return target."""

import json
from pathlib import Path

import pytest

from animetta.tools.gamebot.contracts.v2 import (
    Observation,
    Position,
    RegionBounds,
    RegionInspection,
)
from animetta.tools.minecraft.survival.portal_site import (
    nether_portal_survey_bounds,
    select_nether_portal_site,
)

_MESSAGES = json.loads(
    (Path(__file__).resolve().parents[4] / "contracts/gamebot/v2/fixtures/golden.json").read_text(
        encoding="utf-8"
    )
)["messages"]


def _survey() -> tuple[Observation, RegionInspection]:
    observation = Observation.model_validate(
        {
            **_MESSAGES["Observation"],
            "position": {"x": 0, "y": 75, "z": 0},
            "inventory": {},
        }
    )
    blocks = {f"{x},{y},0": "minecraft:air" for x in range(5) for y in range(63, 81)}
    blocks.update({f"{x},63,0": "minecraft:grass_block" for x in range(5)})
    inspection = RegionInspection(
        inspection_id="site-survey",
        correlation_id="site-survey",
        runtime_instance_id=observation.runtime_instance_id,
        world_identity=observation.world_identity,
        captured_at_ms=observation.captured_at_ms,
        tick=observation.tick,
        observation_id=observation.observation_id,
        observation_hash=observation.content_hash,
        content_hash="a" * 64,
        bounds=RegionBounds(min=Position(x=0, y=63, z=0), max=Position(x=4, y=80, z=0)),
        blocks=blocks,
    )
    return observation, inspection


def test_portal_site_uses_known_ground_below_a_canopy_spawn() -> None:
    observation, inspection = _survey()
    site = select_nether_portal_site(observation, (inspection,))
    assert site.home == (0, 64, 0)
    assert site.origin == (1, 64, 0)
    assert observation.position.y == 75
    assert all(bounds.volume <= 4096 for bounds in nether_portal_survey_bounds(observation))
    assert len(nether_portal_survey_bounds(observation)) == 8


@pytest.mark.parametrize(
    "support",
    ["minecraft:spruce_leaves", "minecraft:spruce_log", "minecraft:sand", "minecraft:water"],
)
def test_portal_site_rejects_temporary_or_unsafe_support(support: str) -> None:
    observation, inspection = _survey()
    inspection.blocks["0,63,0"] = support
    with pytest.raises(ValueError, match="no permanent"):
        select_nether_portal_site(observation, (inspection,))


def test_portal_site_does_not_infer_air_from_missing_or_occluded_voxels() -> None:
    observation, inspection = _survey()
    del inspection.blocks["2,66,0"]
    with pytest.raises(ValueError, match="no permanent"):
        select_nether_portal_site(observation, (inspection,))
    inspection.blocks["2,66,0"] = "minecraft:air"
    inspection.blocks["0,76,0"] = "minecraft:spruce_leaves"
    with pytest.raises(ValueError, match="no permanent"):
        select_nether_portal_site(observation, (inspection,))


def test_portal_site_rejects_another_world_and_conflicting_inspections() -> None:
    observation, inspection = _survey()
    other = inspection.model_copy(
        update={
            "world_identity": inspection.world_identity.model_copy(
                update={"world_identity_hash": "f" * 64},
            )
        }
    )
    with pytest.raises(ValueError, match="another world"):
        select_nether_portal_site(observation, (other,))
    conflict = inspection.model_copy(
        update={"blocks": {**inspection.blocks, "0,63,0": "minecraft:stone"}}
    )
    with pytest.raises(ValueError, match="conflicting"):
        select_nether_portal_site(observation, (inspection, conflict))


def _supported_survey(
    material: str = "sand", foundation: str = "stone"
) -> tuple[Observation, RegionInspection]:
    observation, inspection = _survey()
    blocks = {
        **inspection.blocks,
        **{f"{x},{y},0": f"minecraft:{material}" for x in range(5) for y in range(61, 64)},
        **{f"{x},60,0": f"minecraft:{foundation}" for x in range(5)},
    }
    return observation, inspection.model_copy(
        update={
            "blocks": blocks,
            "bounds": RegionBounds(min=Position(x=0, y=60, z=0), max=Position(x=4, y=80, z=0)),
        }
    )


@pytest.mark.parametrize("material", ["sand", "red_sand", "gravel"])
@pytest.mark.parametrize("foundation", ["stone", "sandstone"])
def test_portal_site_accepts_a_fully_inspected_supported_gravity_column(
    material: str, foundation: str
) -> None:
    observation, inspection = _supported_survey(material, foundation)
    site = select_nether_portal_site(observation, (inspection,))
    assert site.home == (0, 64, 0)
    assert site.origin == (1, 64, 0)


@pytest.mark.parametrize("gap", ["minecraft:water", "minecraft:lava", "minecraft:air", None])
@pytest.mark.parametrize("column", [0, 2])
def test_portal_site_rejects_a_gap_under_home_or_portal_gravity_support(
    gap: str | None, column: int
) -> None:
    observation, inspection = _supported_survey()
    key = f"{column},62,0"
    if gap is None:
        del inspection.blocks[key]
    else:
        inspection.blocks[key] = gap
    with pytest.raises(ValueError, match="no permanent"):
        select_nether_portal_site(observation, (inspection,))


@pytest.mark.parametrize("material", ["sandstone", "red_sandstone"])
def test_portal_site_accepts_non_falling_sandstone_ground(material: str) -> None:
    observation, inspection = _survey()
    inspection.blocks.update({f"{x},63,0": f"minecraft:{material}" for x in range(5)})
    assert select_nether_portal_site(observation, (inspection,)).home == (0, 64, 0)


_TERRACOTTA_GROUND = [
    "terracotta",
    "white_terracotta",
    "orange_terracotta",
    "magenta_terracotta",
    "light_blue_terracotta",
    "yellow_terracotta",
    "lime_terracotta",
    "pink_terracotta",
    "gray_terracotta",
    "light_gray_terracotta",
    "cyan_terracotta",
    "purple_terracotta",
    "blue_terracotta",
    "brown_terracotta",
    "green_terracotta",
    "red_terracotta",
    "black_terracotta",
]


@pytest.mark.parametrize("material", _TERRACOTTA_GROUND)
def test_portal_site_accepts_terracotta_ground(material: str) -> None:
    observation, inspection = _survey()
    inspection.blocks.update({f"{x},63,0": f"minecraft:{material}" for x in range(5)})
    site = select_nether_portal_site(observation, (inspection,))
    assert site.home == (0, 64, 0)
    assert site.origin == (1, 64, 0)


def test_portal_site_accepts_mixed_terracotta_palette_ground() -> None:
    observation, inspection = _survey()
    palette = [
        "minecraft:terracotta",
        "minecraft:red_terracotta",
        "minecraft:brown_terracotta",
        "minecraft:orange_terracotta",
        "minecraft:light_gray_terracotta",
    ]
    inspection.blocks.update({f"{x},63,0": palette[x] for x in range(5)})
    site = select_nether_portal_site(observation, (inspection,))
    assert site.home == (0, 64, 0)
    assert site.origin == (1, 64, 0)
