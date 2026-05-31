"""LivingMemorySystem — entry point for the living memory architecture.

Orchestrates: AtomStore → MemorySearch → EmotionalField → Reconsolidation → Metabolism.

Replaces MemorySystem with unified encode/recall API.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from animetta.memory.v2.atom import MemoryAtom, Layer
from animetta.memory.v2.store import AtomStore
from animetta.memory.v2.emotion_field import EmotionalField, VADVector
from animetta.memory.v2.search import MemorySearch


@dataclass
class RecallResult:
    """Result of a memory recall operation.

    atoms:    Recall output atoms sorted by emotion congruence.
             Each atom's `summary` field is the reconsolidated version
             (or original content if never recalled).
    profile:  User profile extracted from SEMANTIC layer atoms.
    memes:    Active memes from EMERGENT layer.
    """
    atoms: list[MemoryAtom] = field(default_factory=list)
    profile: dict = field(default_factory=dict)
    memes: list[MemoryAtom] = field(default_factory=list)


class LivingMemorySystem:
    """Living memory system — encode, recall, reconsolidate, metabolize.

    USAGE:
        system = LivingMemorySystem()
        await system.initialize()

        # Encode a conversation turn
        atom = await system.encode(
            user_input="今天喝了拿铁",
            agent_response="拿铁不错！",
            emotion_vad=VAD_MAP["happy"],
            session_id="s1",
        )

        # Recall memories with emotion bias
        result = await system.recall(
            query="咖啡",
            session_id="s1",
            current_emotion=VAD_MAP["happy"],
        )
        # result.atoms contain memories with summaries
        # Reconsolidation runs async in background
    """

    # Reconsolidation cooldown (minutes)
    RECONSOLIDATION_COOLDOWN_MINUTES = 30

    # Maximum atoms to reconsolidate per recall
    MAX_RECONSOLIDATION_PER_RECALL = 3

    # Minimum salience for reconsolidation
    MIN_RECONSOLIDATION_SALIENCE = 0.3

    def __init__(self, db_path: str = "memory_db/living_memory.sqlite"):
        self.store = AtomStore(db_path=db_path)
        self._initialized = False

    async def initialize(self) -> None:
        await self.store.initialize()
        self._initialized = True

    async def shutdown(self) -> None:
        await self.store.close()

    # ── Encode ──

    async def encode(
        self,
        user_input: str,
        agent_response: str,
        emotion_vad: VADVector | None = None,
        session_id: str = "default",
    ) -> MemoryAtom:
        """Encode a conversation turn as a RAW layer MemoryAtom.

        Confidence is computed from emotion intensity (flashbulb memory effect).
        High-arousal events get higher initial confidence.
        """
        if emotion_vad is None:
            emotion_vad = VADVector(0.0, 0.0, 0.0)

        content = f"用户: {user_input}\n助手: {agent_response}"
        now = datetime.now(timezone.utc)

        conf = EmotionalField.encoding_confidence(emotion_vad)

        atom = MemoryAtom(
            id=f"raw-{uuid.uuid4().hex[:12]}",
            layer=Layer.RAW,
            content=content,
            summary=None,
            occurred_at=now,
            rewritten_at=now,
            version=1,
            confidence=conf,
            salience=conf,
            emotion_valence=emotion_vad.valence,
            emotion_arousal=emotion_vad.arousal,
            emotion_dominance=emotion_vad.dominance,
            tags=[session_id],
        )
        await self.store.create(atom)
        return atom

    # ── Recall ──

    async def recall(
        self,
        query: str,
        session_id: str = "default",
        current_emotion: VADVector | None = None,
        limit: int = 20,
    ) -> RecallResult:
        """Recall memories relevant to the query, biased by current emotion.

        Returns RecallResult with emotion-ranked atoms, user profile, and memes.
        Asynchronously triggers reconsolidation for high-salience recalled atoms.
        """
        if current_emotion is None:
            current_emotion = VADVector(0.0, 0.0, 0.0)

        # Get all active atoms (simplified — future: integrate Chroma vector search)
        all_active = await self.store.get_all_active(limit * 3)

        # Filter by session if specified
        if session_id != "default":
            all_active = [
                a for a in all_active if session_id in a.tags
            ]

        # Emotion-biased ranking
        ranked = MemorySearch.rank_by_emotion(all_active, current_emotion)

        # Take top-K
        top_atoms = ranked[:limit]

        # Extract profile from SEMANTIC layer
        profile_atoms = [a for a in top_atoms if a.layer == Layer.SEMANTIC]
        profile = {a.tags[0] if a.tags else "unknown": a.summary or a.content
                   for a in profile_atoms} if profile_atoms else {}

        # Extract memes from EMERGENT layer
        meme_atoms = [a for a in ranked if a.layer == Layer.EMERGENT][:5]

        result = RecallResult(
            atoms=top_atoms,
            profile=profile,
            memes=meme_atoms,
        )

        # Trigger async reconsolidation (fire-and-forget)
        asyncio.create_task(
            self._reconsolidate(top_atoms, current_emotion, query)
        )

        return result

    # ── Reconsolidation (integrated) ──

    async def _reconsolidate(
        self,
        atoms: list[MemoryAtom],
        current_emotion: VADVector,
        query: str,
    ) -> None:
        """Async reconsolidation — recall triggers memory rewriting.

        Throttled: max 3 atoms per recall, 30min cooldown, salience > 0.3.
        The LLM rewrite is a placeholder — in production, this calls the
        actual LLM service with the reconsolidation prompt.
        """
        now = datetime.now(timezone.utc)
        cooldown = timedelta(minutes=self.RECONSOLIDATION_COOLDOWN_MINUTES)
        reconsolidated = 0

        for atom in atoms:
            if reconsolidated >= self.MAX_RECONSOLIDATION_PER_RECALL:
                break

            # Cooldown check
            if atom.last_accessed_at and (now - atom.last_accessed_at) < cooldown:
                continue

            # Salience threshold
            if atom.salience <= self.MIN_RECONSOLIDATION_SALIENCE:
                continue

            # Perform reconsolidation
            try:
                await self._reconsolidate_atom(atom, current_emotion, query)
                reconsolidated += 1
            except Exception:
                # Reconsolidation failure is non-fatal
                pass

    async def _reconsolidate_atom(
        self,
        atom: MemoryAtom,
        current_emotion: VADVector,
        query: str,
    ) -> None:
        """Reconsolidate a single atom.

        In production: calls LLM with reconsolidation prompt.
        For now: performs metadata-only reconsolidation (emotion shift,
        confidence adjustment, decay rate adaptation).
        """
        # Shift emotion toward current state
        new_emotion = EmotionalField.emotion_shift(current_emotion,
            VADVector(atom.emotion_valence, atom.emotion_arousal, atom.emotion_dominance))

        # Confidence slightly adjusts (reinforced by recall)
        new_confidence = min(1.0, atom.confidence + 0.02)

        # Content "rewrite": for now, use existing summary or content
        # In production, this would be the LLM-generated rewrite
        new_summary = atom.summary or atom.content

        # Reduce decay rate (recalled memories decay slower)
        new_decay_rate = max(0.02, atom.decay_rate * 0.95)

        # Write new version
        atom.summary = new_summary
        atom.confidence = new_confidence
        atom.emotion_valence = new_emotion.valence
        atom.emotion_arousal = new_emotion.arousal
        atom.emotion_dominance = new_emotion.dominance
        atom.decay_rate = new_decay_rate
        atom.version += 1
        atom.version_chain = list(atom.version_chain) + [atom.id]
        atom.rewritten_at = datetime.now(timezone.utc)
        atom.retrieval_count += 1
        atom.last_accessed_at = datetime.now(timezone.utc)

        await self.store.update(atom)
