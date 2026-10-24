"""Choose a permanent portal site from complete, read-only voxel evidence."""

from dataclasses import dataclass
from math import floor

from animetta.tools.gamebot.contracts.v2 import (
    Observation,
    Position,
    RegionBounds,
    RegionInspection,
)
from animetta.tools.minecraft.blueprint.portal import nether_portal_blueprint

_GROUND = frozenset(
    f"minecraft:{name}"
    for name in (
        "grass_block",
        "dirt",
        "coarse_dirt",
        "rooted_dirt",
        "podzol",
        "mycelium",
        "stone",
        "sandstone",
        "red_sandstone",
        "deepslate",
        "granite",
        "diorite",
        "andesite",
        "tuff",
        "netherrack",
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
    )
)
_FALLING_GROUND = frozenset({"minecraft:sand", "minecraft:red_sand", "minecraft:gravel"})
_AIR = frozenset({"minecraft:air", "minecraft:cave_air"})
_FOOT_COVER = _AIR | {"minecraft:snow"}


def _supported_ground(blocks: dict[tuple[int, int, int], str], point: tuple[int, int, int]) -> bool:
    x, y, z = point
    while blocks.get((x, y, z)) in _FALLING_GROUND:
        y -= 1
    return blocks.get((x, y, z)) in _GROUND


@dataclass(frozen=True)
class NetherPortalSite:
    home: tuple[float, float, float]
    origin: tuple[int, int, int]


def nether_portal_survey_bounds(observation: Observation) -> tuple[RegionBounds, ...]:
    """Eight loaded-chunk inspections, each at most the protocol's 4096 voxels."""
    if observation.position is None:
        raise ValueError("portal survey requires an observed position")
    x, y, z = (
        floor(v)
        for v in (
            observation.position.x,
            observation.position.y,
            observation.position.z,
        )
    )
    return tuple(
        RegionBounds(
            min=Position(x=x + dx, y=max(-64, y + dy), z=z + dz),
            max=Position(x=x + dx + 15, y=min(319, y + dy + 15), z=z + dz + 15),
        )
        for dx in (-16, 0)
        for dz in (-16, 0)
        for dy in (-24, -8)
        if y + dy + 15 >= -64 and y + dy <= 319
    )


def select_nether_portal_site(
    observation: Observation,
    inspections: tuple[RegionInspection, ...],
) -> NetherPortalSite:
    """Keep explicit caller goals untouched; select only before declaring a mission."""
    if observation.position is None or not inspections:
        raise ValueError("portal site requires a position and inspected blocks")
    blocks: dict[tuple[int, int, int], str] = {}
    for inspection in inspections:
        if inspection.world_identity != observation.world_identity:
            raise ValueError("portal survey belongs to another world or runtime")
        for key, block in inspection.blocks.items():
            x, y, z = (int(v) for v in key.split(","))
            point = (x, y, z)
            if point in blocks and blocks[point] != block:
                raise ValueError("portal survey contains conflicting voxel evidence")
            blocks[point] = block
    if not blocks:
        raise ValueError("portal site requires inspected blocks")
    dimensions = nether_portal_blueprint().dimensions
    ceiling = max(point[1] for point in blocks)
    candidates = []
    for x, support_y, z in blocks:
        if not _supported_ground(blocks, (x, support_y, z)):
            continue
        y = support_y + 1
        # The home stands beside the portal, on permanent ground. Require a
        # fully known open column, so a cave or a harvested canopy is not home.
        if y + dimensions.height > ceiling + 1:
            continue
        cover = blocks.get((x, y, z))
        if cover not in _FOOT_COVER or not all(
            blocks.get((x, yy, z)) in _AIR for yy in range(y + 1, ceiling + 1)
        ):
            continue
        if not all(
            _supported_ground(blocks, (xx, y - 1, z))
            and blocks.get((xx, y, z)) in _FOOT_COVER
            and all(blocks.get((xx, yy, z)) in _AIR for yy in range(y + 1, y + dimensions.height))
            for xx in range(x + 1, x + 1 + dimensions.width)
        ):
            continue
        distance = (
            (x - observation.position.x) ** 2
            + (y - observation.position.y) ** 2
            + (z - observation.position.z) ** 2
        )
        candidates.append((distance, x, y, z, cover == "minecraft:snow"))
    if not candidates:
        raise ValueError("no permanent, clear portal site in the inspected region")
    _, x, y, z, snow = min(candidates)
    # All SDK snow-layer collision tops lie in [0, 1). Center this standing
    # band without changing the navigation cell or the existing 1.5 tolerance.
    return NetherPortalSite(home=(x, y + 0.5 if snow else y, z), origin=(x + 1, y, z))
