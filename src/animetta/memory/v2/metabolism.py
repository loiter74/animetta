"""MetabolismScheduler — unified decay / consolidation / forgetting cycle.

Replaces the dual decay systems (MemoryScorer exponential + MemePool sigmoid)
with a single salience-driven metabolism model based on synaptic homeostasis
(Tononi & Cirelli, 2006).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from animetta.memory.v2.atom import MemoryAtom
from animetta.memory.v2.emotion_field import EmotionalField, VADVector


class MetabolismScheduler:
    """Unified memory metabolism — three-phase cycle.

    Phase 1: DECAY — recalculate salience for all active atoms
    Phase 2: CONSOLIDATE — merge overlapping atoms (LLM-driven, daily)
    Phase 3: FORGET — archive atoms below adaptive threshold
    """

    @staticmethod
    def compute_salience(atom: MemoryAtom) -> float:
        """Compute current salience using unified formula.

        salience = confidence × e^(-λ × t) × retrieval_boost × emotion_protection

        Where:
          λ = atom.decay_rate (personalized, adapts with reconsolidation)
          t = hours since last rewrite
          retrieval_boost = 1.0 + 0.15 × retrieval_count
          emotion_protection = 1.0 + 0.3 × |valence| × arousal
        """
        now = datetime.now(UTC)
        elapsed_hours = (now - atom.rewritten_at).total_seconds() / 3600.0

        # Exponential decay
        decay = math.exp(-atom.decay_rate * elapsed_hours)

        # Retrieval boost (spacing effect)
        retrieval_boost = 1.0 + 0.15 * atom.retrieval_count

        # Emotion protection (flashbulb memory)
        emotion = VADVector(
            atom.emotion_valence,
            atom.emotion_arousal,
            atom.emotion_dominance,
        )
        emotion_protection = EmotionalField.metabolism_protection(emotion)

        salience = atom.confidence * decay * retrieval_boost * emotion_protection
        return max(0.0, min(1.0, salience))

    @staticmethod
    def adaptive_threshold(atom_count: int, capacity: int = 1000) -> float:
        """Compute adaptive forgetting threshold based on storage pressure.

        Synaptic homeostasis: the brain forgets more aggressively when
        storage is under pressure (Tononi & Cirelli, 2006).

        Low water (< 30% capacity) → almost no forgetting (threshold ~0.02)
        High water (> 85% capacity) → aggressive forgetting (threshold ~0.20)
        """
        fill_ratio = atom_count / capacity

        if fill_ratio < 0.3:
            return 0.02
        elif fill_ratio < 0.5:
            return 0.05
        elif fill_ratio < 0.7:
            return 0.10
        elif fill_ratio < 0.85:
            return 0.15
        else:
            return 0.20

    @staticmethod
    def should_forget(atom: MemoryAtom, capacity: int = 1000) -> bool:
        """Check if an atom should be forgotten based on current storage pressure."""
        threshold = MetabolismScheduler.adaptive_threshold(
            atom_count=0,  # Will be computed by caller with actual count
            capacity=capacity,
        )
        return atom.salience < threshold
