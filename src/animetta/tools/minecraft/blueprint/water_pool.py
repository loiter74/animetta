"""Three water cells that refill each other into an infinite source."""

from .models import BlueprintDimensions, PaletteEntry, RelativePlacement, StructureBlueprint


def infinite_water_source_blueprint() -> StructureBlueprint:
    return StructureBlueprint(
        blueprint_id="infinite-water-source-v1",
        dimensions=BlueprintDimensions(width=3, height=1, depth=1),
        palette={
            "water": PaletteEntry(
                default_block="minecraft:water", allowed_blocks=("minecraft:water",)
            )
        },
        placements=tuple(
            RelativePlacement(
                x=x,
                y=0,
                z=0,
                material="water",
            )
            for x in range(3)
        ),
    )
