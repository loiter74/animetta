"""Consistent skill snapshot copy and bounded experience export."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from animetta.tools.minecraft.skill.ir import (
    SkillDefinition,
    SkillProgram,
    SkillRevision,
)
from animetta.tools.minecraft.skill.revision_store import (
    SkillRevisionStore,
    copy_skill_snapshot,
)
from animetta.tools.minecraft.skill.trust import (
    SkillEnvironmentTrust,
    TrustStatus,
    rank_trusted_revisions,
)
from animetta.tools.minecraft.voyager.budget import BudgetUsage

_OLD_ENV = "e" * 64
_NEW_ENV = "f" * 64


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision(name: str, *, command_id: str) -> tuple[SkillDefinition, SkillRevision]:
    program = SkillProgram.model_validate(
        {
            "name": name,
            "steps": [
                {
                    "kind": "action",
                    "step_id": "collect",
                    "capability": "collect",
                    "parameters": {"count": {"kind": "literal", "value": 1}},
                }
            ],
            "postconditions": [
                {
                    "op": "gte",
                    "left": {"kind": "observation", "path": "inventory.oak_log"},
                    "right": {"kind": "literal", "value": 1},
                }
            ],
        }
    )
    definition = SkillDefinition(definition_id=name, name=name, description="")
    revision = SkillRevision(
        definition_id=name,
        revision_hash=program.canonical_hash,
        program=program,
        static_cost=BudgetUsage(max_actions=1),
        source_command_id=command_id,
    )
    return definition, revision


async def _seed_source(path: Path) -> dict[str, SkillRevision]:
    """Persist one trusted pair, one candidate, and one demoted revision."""

    store = SkillRevisionStore(path)
    await store.connect()
    revisions: dict[str, SkillRevision] = {}
    try:
        for name, command_id in (
            ("trusted_skill", "command-trusted"),
            ("trusted_two", "command-trusted-two"),
            ("candidate_skill", "command-candidate"),
            ("failed_skill", "command-failed"),
        ):
            definition, revision = _revision(name, command_id=command_id)
            await store.save_revision(definition, revision)
            revisions[name] = revision
        await store.record_validation(
            SkillEnvironmentTrust.trusted(
                revisions["trusted_skill"].revision_hash,
                _OLD_ENV,
                successes=5,
                expected_cost=2,
                portable=True,
            ),
            policy_report={"valid": True, "source": "old_world"},
            learning_evidence=("a" * 64,),
            validation_evidence=("b" * 64,),
        )
        await store.record_validation(
            SkillEnvironmentTrust.trusted(
                revisions["trusted_two"].revision_hash,
                _OLD_ENV,
                successes=3,
            ),
            policy_report={"valid": True},
            learning_evidence=(),
            validation_evidence=(),
        )
        await store.record_validation(
            SkillEnvironmentTrust(
                revision_hash=revisions["candidate_skill"].revision_hash,
                environment_fingerprint=_OLD_ENV,
                status=TrustStatus.CANDIDATE,
            ),
            policy_report={"valid": False},
            learning_evidence=(),
            validation_evidence=(),
        )
        await store.record_validation(
            SkillEnvironmentTrust(
                revision_hash=revisions["failed_skill"].revision_hash,
                environment_fingerprint=_OLD_ENV,
                status=TrustStatus.DEMOTED,
                failures=3,
                consecutive_failures=3,
                demotion_reason="ordinary attributable failure threshold",
            ),
            policy_report={"valid": False, "failures": 3},
            learning_evidence=(),
            validation_evidence=("c" * 64,),
        )
    finally:
        await store.close()
    return revisions


async def test_snapshot_copy_preserves_source_and_old_environment_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "skills.db"
    revisions = await _seed_source(source)
    hash_before = _file_hash(source)

    wal_writer = sqlite3.connect(source)
    wal_writer.execute("PRAGMA journal_mode=WAL")
    wal_writer.execute(
        "UPDATE skill_definitions SET description='wal-committed'"
        " WHERE definition_id='trusted_skill'"
    )
    wal_writer.commit()
    try:
        destination = tmp_path / "nested" / "snapshot" / "skills-copy.db"
        await copy_skill_snapshot(source, destination)

        assert _file_hash(source) == hash_before
        assert [item.name for item in destination.parent.iterdir()] == ["skills-copy.db"]

        store = SkillRevisionStore(destination)
        await store.connect()
        try:
            exported = await store.export_experience()
            assert [entry["trust_status"] for entry in exported] == [
                "trusted",
                "trusted",
                "candidate",
                "demoted",
            ]
            trusted = exported[0]
            assert trusted["revision_hash"] == revisions["trusted_skill"].revision_hash
            assert trusted["source_command_id"] == "command-trusted"
            assert trusted["program"]["name"] == "trusted_skill"
            assert trusted["environment_fingerprint"] == _OLD_ENV
            assert trusted["successes"] == 5
            assert trusted["policy_report"] == {"valid": True, "source": "old_world"}
            assert trusted["learning_receipt_refs"] == ["a" * 64]
            assert trusted["validation_receipt_refs"] == ["b" * 64]
            demoted = exported[3]
            assert demoted["trust_status"] == "demoted"
            assert demoted["failures"] == 3

            old_revisions, old_trusts = await store.load_live_catalog(
                environment_fingerprint=_OLD_ENV
            )
            assert set(old_revisions) == {item.revision_hash for item in revisions.values()}
            assert [trust.revision_hash for trust in old_trusts] == sorted(
                trust.revision_hash for trust in old_trusts
            )
            ranked_old = rank_trusted_revisions(old_trusts, environment_fingerprint=_OLD_ENV)
            assert [trust.successes for trust in ranked_old] == [5, 3]

            new_revisions, new_trusts = await store.load_live_catalog(
                environment_fingerprint=_NEW_ENV
            )
            assert set(new_revisions) == set(old_revisions)
            assert new_trusts == []
            assert rank_trusted_revisions(new_trusts, environment_fingerprint=_NEW_ENV) == []
            assert all(trust.environment_fingerprint == _OLD_ENV for trust in old_trusts), (
                "copied trust must keep the original environment fingerprint"
            )
        finally:
            await store.close()

        live = sqlite3.connect(destination)
        try:
            committed = live.execute(
                "SELECT description FROM skill_definitions WHERE definition_id='trusted_skill'"
            ).fetchone()
        finally:
            live.close()
        assert committed is not None and committed[0] == "wal-committed"
    finally:
        wal_writer.close()
    # Closing the writer checkpoints its WAL into the source file (normal SQLite
    # behavior); the copy itself never rewrote the source, as asserted above.
    source_live = sqlite3.connect(source)
    try:
        checkpointed = source_live.execute(
            "SELECT description FROM skill_definitions WHERE definition_id='trusted_skill'"
        ).fetchone()
    finally:
        source_live.close()
    assert checkpointed is not None and checkpointed[0] == "wal-committed"


async def test_snapshot_copy_rejects_self_copy_and_existing_destination(
    tmp_path: Path,
) -> None:
    source = tmp_path / "skills.db"
    await _seed_source(source)
    hash_before = _file_hash(source)

    with pytest.raises(ValueError, match="SNAPSHOT_SELF_COPY_NOT_ALLOWED"):
        await copy_skill_snapshot(source, source)

    occupied = tmp_path / "occupied.db"
    occupied.write_bytes(b"existing")
    with pytest.raises(ValueError, match="SNAPSHOT_DESTINATION_ALREADY_EXISTS"):
        await copy_skill_snapshot(source, occupied)
    assert occupied.read_bytes() == b"existing"

    with pytest.raises(FileNotFoundError):
        await copy_skill_snapshot(tmp_path / "missing.db", tmp_path / "out.db")
    assert not (tmp_path / "out.db").exists()
    assert _file_hash(source) == hash_before


async def test_export_experience_limit_bounds_and_readonly_stability(
    tmp_path: Path,
) -> None:
    source = tmp_path / "skills.db"
    revisions = await _seed_source(source)
    store = SkillRevisionStore(source)
    await store.connect()
    try:
        _, trusts_before = await store.load_live_catalog(environment_fingerprint=_OLD_ENV)

        bounded = await store.export_experience(limit=2)
        assert len(bounded) == 2
        assert bounded == await store.export_experience(limit=2)
        assert [entry["revision_hash"] for entry in bounded] == [
            revisions["trusted_skill"].revision_hash,
            revisions["trusted_two"].revision_hash,
        ]
        full = await store.export_experience(limit=32)
        assert len(full) == 4
        assert full == await store.export_experience()

        for bad_limit in (0, -1, 33):
            with pytest.raises(ValueError, match="EXPORT_LIMIT_OUT_OF_RANGE"):
                await store.export_experience(limit=bad_limit)

        _, trusts_after = await store.load_live_catalog(environment_fingerprint=_OLD_ENV)
        assert trusts_after == trusts_before
    finally:
        await store.close()
