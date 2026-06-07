"""Generate seed MemoryAtoms for 草十郎 persona.

Usage: PYTHONPATH=src python scripts/seed_soujuurou.py [--force]
"""
import asyncio
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from animetta.config.persona.base import PersonaConfig
from animetta.memory.v2.seed_generator import PersonaSeedGenerator, CanonicalQuote


async def main(force: bool = False) -> None:
    root = Path(__file__).parent.parent

    # Load persona
    persona_path = root / "config" / "personas" / "soujuurou.yaml"
    persona = PersonaConfig.from_yaml(str(persona_path))
    print(f"Loaded persona: {persona.name} ({persona.personality.mbti.type})")

    # Load canonical quotes
    quotes_path = root / "config" / "personas" / "soujuurou_quotes.yaml"
    quotes: list[CanonicalQuote] = []
    if quotes_path.exists():
        with open(quotes_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for q in data.get("quotes", []):
            quotes.append(CanonicalQuote(
                speaker=q.get("speaker", "草十郎"),
                text=q["text"],
                context=q.get("context", ""),
                emotion_valence=q.get("emotion_valence", 0.0),
                emotion_arousal=q.get("emotion_arousal", 0.0),
            ))
        print(f"Loaded {len(quotes)} canonical quotes")
    else:
        print(f"Quotes file not found: {quotes_path}")

    # Generate seeds
    gen = PersonaSeedGenerator(persona, store=None)
    result = await gen.generate(quotes=quotes, force=force)
    print(f"\nGenerated {len(result.atoms)} seed atoms:")
    print(f"  RAW:      {result.stats['raw']}")
    print(f"  EPISODIC: {result.stats['episodic']}")
    print(f"  SEMANTIC: {result.stats['semantic']}")

    # Print first few atoms as preview
    print("\n--- Preview (first RAW atom) ---")
    for a in result.atoms:
        if a.layer.name == "RAW":
            print(f"  Layer: {a.layer.name}")
            print(f"  Tags: {a.tags}")
            print(f"  Confidence: {a.confidence}")
            print(f"  Content: {a.content[:200]}...")
            break

    print("\nDone.")


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    asyncio.run(main(force=force_flag))
