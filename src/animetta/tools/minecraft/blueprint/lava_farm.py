"""A cauldron fed by one dripping lava block held on a dripstone column."""

from .models import BlueprintDimensions, PaletteEntry, RelativePlacement, StructureBlueprint


def lava_drip_farm_blueprint() -> StructureBlueprint:
    return StructureBlueprint(
        blueprint_id="lava-drip-farm-v1",
        dimensions=BlueprintDimensions(width=1, height=4, depth=1),
        palette={
            name: PaletteEntry(default_block=block, allowed_blocks=allowed)
            for name, block, allowed in (
                ("cauldron", "minecraft:cauldron", ("minecraft:cauldron",)),
                ("dripstone", "minecraft:pointed_dripstone", ("minecraft:pointed_dripstone",)),
                (
                    "support",
                    "minecraft:cobblestone",
                    ("minecraft:cobblestone", "minecraft:dirt"),
                ),
                ("lava", "minecraft:lava", ("minecraft:lava",)),
            )
        },
        placements=tuple(
            RelativePlacement(
                x=0,
                y=y,
                z=0,
                material=("cauldron", "dripstone", "support", "lava")[y],
            )
            for y in range(4)
        ),
    )
