"""Ten obsidian blocks, four common supports and six activated portal blocks."""

from .models import BlueprintDimensions, PaletteEntry, RelativePlacement, StructureBlueprint


def nether_portal_blueprint() -> StructureBlueprint:
    return StructureBlueprint(
        blueprint_id="nether-portal-v1",
        dimensions=BlueprintDimensions(width=4, height=5, depth=1),
        palette={
            name: PaletteEntry(default_block=block, allowed_blocks=(block,))
            for name, block in (
                ("frame", "minecraft:obsidian"),
                ("support", "minecraft:cobbled_deepslate"),
                ("portal", "minecraft:nether_portal"),
            )
        },
        placements=tuple(
            RelativePlacement(
                x=x,
                y=y,
                z=0,
                material=(
                    "support"
                    if x in (0, 3) and y in (0, 4)
                    else "frame"
                    if x in (0, 3) or y in (0, 4)
                    else "portal"
                ),
            )
            for y in range(5)
            for x in range(4)
        ),
    )
