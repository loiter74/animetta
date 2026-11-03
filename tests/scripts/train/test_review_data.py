from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

import scripts.train.review_data as review_data
from scripts.train.review_data import (
    ReviewStore,
    apply_review_run,
    create_review_run,
    organize_review_run,
)
from scripts.train.workspace import MANIFEST_COLUMNS


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_audio(path: Path, *, frames: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.zeros(frames, dtype=np.float32), 48_000, subtype="PCM_16")


def _project(tmp_path: Path, *, traversal: bool = False) -> Path:
    root = tmp_path / "songs"
    (root / "manifests").mkdir(parents=True)
    (root / "project.toml").write_text(
        """
schema_version = 1
project_id = "review-test"
display_name = "听审测试"

[data]
sample_rate = 48000
channels = 1
audio_format = "wav_pcm_s16le"
min_duration_s = 2.0
max_duration_s = 15.0

[qc]
silence_threshold_dbfs = -45.0
max_silence_ratio = 0.35
max_clipping_ratio = 0.001
min_snr_db = 18.0
f0_min_hz = 50.0
f0_max_hz = 1100.0
""".strip()
        + "\n",
        encoding="utf-8",
    )
    source_id = "tohsakarin_prepared"
    prepared_audio = root / "audio" / "processed" / f"{source_id}.wav"
    _write_audio(prepared_audio)
    source_relpath = "../escape.wav" if traversal else prepared_audio.relative_to(root).as_posix()
    _write_csv(
        root / "manifests" / "sources.csv",
        MANIFEST_COLUMNS["sources.csv"],
        [
            {
                "source_id": source_id,
                "audio_relpath": "audio/raw/TohsakaRin_CN/ogg/prepared.wav",
                "transcript": "原始文本",
                "source_reference": "StarRailVoice/TohsakaRin_CN/ogg/prepared.wav",
                "usage_rights": "local_research_only",
                "speaker": "TohsakaRin_CN",
                "scene": "archive",
                "notes": (
                    "transcript_source=game_text; match=fuzzy; "
                    "confidence=0.900; review_required=true"
                ),
            }
        ],
    )
    clip = dict.fromkeys(MANIFEST_COLUMNS["clips.csv"], "")
    clip.update(
        {
            "clip_id": source_id,
            "source_id": source_id,
            "audio_relpath": source_relpath,
            "transcript": "原始文本",
            "duration_s": "1801",
            "sample_rate": "48000",
            "channels": "1",
            "snr_db": "12",
            "silence_ratio": "0.4",
            "audio_sha256": "1" * 64,
            "review_status": "pending",
            "review_notes": "auto_flags=low_snr_proxy|excess_silence",
        }
    )
    _write_csv(
        root / "manifests" / "clips.csv",
        MANIFEST_COLUMNS["clips.csv"],
        [clip],
    )
    raw_root = root / "audio" / "raw" / "TohsakaRin_CN"
    raw_rows: list[dict[str, str]] = []
    for index in range(4):
        relative = f"ogg/missing-{index}.wav"
        _write_audio(raw_root / relative)
        raw_rows.append(
            {
                "wem_id": f"missing{index}",
                "source": f"voice/archive/tohsakarin/missing-{index}",
                "ogg": relative,
                "asr": "",
                "text": "",
                "match": "none",
                "confidence": "0.0",
            }
        )
    _write_csv(
        raw_root / "manifest.csv",
        ("wem_id", "source", "ogg", "asr", "text", "match", "confidence"),
        raw_rows,
    )
    return root


def _decide_all(store: ReviewStore, *, corrected: str = "修正后的文本") -> None:
    for index, item in enumerate(store.items):
        prepared = item["origin"] == "prepared"
        store.record_decision(
            request_id=f"request-{index:03d}",
            item_id=str(item["item_id"]),
            decision="accepted" if prepared else "rejected",
            reviewer="测试评审人",
            transcript=corrected if prepared else "",
            notes="人工结论" if prepared else "无文本，明确排除",
        )


def test_create_prioritizes_four_unresolved_items_without_touching_manifests(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    before_sources = (root / "manifests" / "sources.csv").read_bytes()
    before_clips = (root / "manifests" / "clips.csv").read_bytes()

    status = create_review_run(root, run_id="voice-review-test", batch_size=2)
    store = ReviewStore(root, "voice-review-test")

    assert status["total_items"] == 5
    assert status["batch_count"] == 3
    assert [item["origin"] for item in store.items[:4]] == ["unresolved"] * 4
    assert status["queue_statistics"]["unresolved_items"] == 4
    assert store.metadata["snapshots"] == {
        "tool": "tool-snapshot.py",
        "ui": "ui-snapshot.html",
    }
    assert (store.run_root / "tool-snapshot.py").is_file()
    assert (store.run_root / "ui-snapshot.html").is_file()
    assert status["decision_counts"] == {
        "accepted": 0,
        "rejected": 0,
        "deferred": 0,
        "pending": 5,
    }
    assert (root / "manifests" / "sources.csv").read_bytes() == before_sources
    assert (root / "manifests" / "clips.csv").read_bytes() == before_clips


def test_event_journal_recovers_and_repeated_requests_are_idempotent(tmp_path: Path) -> None:
    root = _project(tmp_path)
    create_review_run(root, run_id="voice-review-events")
    store = ReviewStore(root, "voice-review-events")
    item = next(item for item in store.items if item["origin"] == "prepared")

    first, duplicate = store.record_decision(
        request_id="request-first",
        item_id=str(item["item_id"]),
        decision="accepted",
        reviewer="评审甲",
        transcript="第一版文本",
        notes="第一次",
    )
    repeated, repeated_duplicate = store.record_decision(
        request_id="request-first",
        item_id=str(item["item_id"]),
        decision="rejected",
        reviewer="评审甲",
        transcript="不应覆盖",
        notes="浏览器重试",
    )
    second, second_duplicate = store.record_decision(
        request_id="request-second",
        item_id=str(item["item_id"]),
        decision="rejected",
        reviewer="评审甲",
        transcript="第二版文本",
        notes="复核后改判",
    )

    assert duplicate is False
    assert repeated_duplicate is True
    assert second_duplicate is False
    assert repeated["event_hash"] == first["event_hash"]
    assert second["previous_transcript"] == "第一版文本"
    assert len((store.run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    (store.run_root / "status.json").unlink()
    recovered = ReviewStore(root, "voice-review-events").status()
    assert recovered["decision_counts"]["rejected"] == 1
    assert recovered["event_count"] == 2


def test_apply_syncs_text_and_keeps_original_in_audit_log(tmp_path: Path) -> None:
    root = _project(tmp_path)
    create_review_run(root, run_id="voice-review-apply")
    store = ReviewStore(root, "voice-review-apply")
    _decide_all(store)

    receipt = apply_review_run(
        root,
        run_id="voice-review-apply",
        confirm_run_id="voice-review-apply",
    )
    _, sources = review_data._read_csv(root / "manifests" / "sources.csv")
    _, clips = review_data._read_csv(root / "manifests" / "clips.csv")
    prepared_source = next(row for row in sources if row["source_id"] == "tohsakarin_prepared")
    prepared_clip = next(row for row in clips if row["clip_id"] == "tohsakarin_prepared")
    events = store._events()

    assert receipt["accepted"] == 1
    assert receipt["excluded_unresolved"] == 4
    assert prepared_source["transcript"] == "修正后的文本"
    assert prepared_clip["transcript"] == "修正后的文本"
    assert prepared_clip["review_status"] == "accepted"
    assert prepared_clip["reviewer"] == "测试评审人"
    assert (
        next(event for event in events if event["origin"] == "prepared")["original_transcript"]
        == "原始文本"
    )
    assert not list((root / "manifests").glob("*.tmp"))


def test_apply_can_add_one_manually_transcribed_unresolved_source(tmp_path: Path) -> None:
    root = _project(tmp_path)
    create_review_run(root, run_id="voice-review-unresolved")
    store = ReviewStore(root, "voice-review-unresolved")
    unresolved_seen = False
    for index, item in enumerate(store.items):
        if item["origin"] == "prepared":
            decision, transcript = "accepted", "已复核文本"
        elif not unresolved_seen:
            unresolved_seen = True
            decision, transcript = "accepted", "补写的无文本语音"
        else:
            decision, transcript = "rejected", ""
        store.record_decision(
            request_id=f"unresolved-{index:03d}",
            item_id=str(item["item_id"]),
            decision=decision,
            reviewer="测试评审人",
            transcript=transcript,
            notes="",
        )

    receipt = apply_review_run(
        root,
        run_id="voice-review-unresolved",
        confirm_run_id="voice-review-unresolved",
    )
    _, sources = review_data._read_csv(root / "manifests" / "sources.csv")
    _, clips = review_data._read_csv(root / "manifests" / "clips.csv")

    assert receipt["added_sources"] == 1
    assert receipt["excluded_unresolved"] == 3
    assert len(sources) == 2
    assert len(clips) == 2
    assert any(row["transcript"] == "补写的无文本语音" for row in sources)
    assert any(
        row["transcript"] == "补写的无文本语音" and row["review_status"] == "accepted"
        for row in clips
    )


def test_create_rejects_audio_path_outside_project(tmp_path: Path) -> None:
    root = _project(tmp_path, traversal=True)

    with pytest.raises(ValueError, match="路径越出工作区"):
        create_review_run(root, run_id="voice-review-traversal")


def test_apply_rolls_back_both_manifests_when_second_atomic_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    create_review_run(root, run_id="voice-review-rollback")
    store = ReviewStore(root, "voice-review-rollback")
    _decide_all(store)
    source_path = root / "manifests" / "sources.csv"
    clip_path = root / "manifests" / "clips.csv"
    before_sources = source_path.read_bytes()
    before_clips = clip_path.read_bytes()
    real_write = review_data._atomic_write_csv
    calls = 0

    def fail_second(
        path: Path,
        columns: tuple[str, ...],
        rows: list[dict[str, str]],
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second replace failure")
        real_write(path, columns, rows)

    monkeypatch.setattr(review_data, "_atomic_write_csv", fail_second)

    with pytest.raises(OSError, match="simulated"):
        apply_review_run(
            root,
            run_id="voice-review-rollback",
            confirm_run_id="voice-review-rollback",
        )

    assert source_path.read_bytes() == before_sources
    assert clip_path.read_bytes() == before_clips
    assert not (store.run_root / "apply-receipt.json").exists()


def test_organize_archives_only_redundant_post_decision_drafts(tmp_path: Path) -> None:
    root = _project(tmp_path)
    create_review_run(root, run_id="voice-review-organize")
    store = ReviewStore(root, "voice-review-organize")
    prepared = next(item for item in store.items if item["origin"] == "prepared")
    unresolved = next(item for item in store.items if item["origin"] == "unresolved")
    store.record_decision(
        request_id="organize-prepared",
        item_id=str(prepared["item_id"]),
        decision="accepted",
        reviewer="评审人",
        transcript="修正文本",
        notes="人工备注",
    )
    store.save_draft(
        str(prepared["item_id"]),
        reviewer="评审人",
        transcript="修正文本",
        notes="人工备注",
    )
    store.record_decision(
        request_id="organize-unresolved",
        item_id=str(unresolved["item_id"]),
        decision="rejected",
        reviewer="评审人",
        transcript="",
        notes="气息声音",
    )
    store.save_draft(
        str(unresolved["item_id"]),
        reviewer="评审人",
        transcript="",
        notes="准备再次复核",
    )
    events_before = (store.run_root / "events.jsonl").read_bytes()
    sources_before = (root / "manifests" / "sources.csv").read_bytes()
    clips_before = (root / "manifests" / "clips.csv").read_bytes()

    summary = organize_review_run(
        root,
        run_id="voice-review-organize",
        reconcile_redundant_drafts=True,
    )
    report_root = store.run_root / "reports" / summary["report_revision"]
    _, decisions = review_data._read_csv(report_root / "review-decisions.csv")
    _, revisions = review_data._read_csv(report_root / "text-revisions.csv")

    assert summary["redundant_drafts_archived"] == 1
    assert summary["remaining_active_drafts"] == 1
    assert summary["superseded_events"] == 0
    assert set(store.drafts()) == {unresolved["item_id"]}
    assert len(decisions) == 5
    assert len(revisions) == 1
    assert (store.run_root / "draft-archive.jsonl").is_file()
    assert (report_root / "event-history.csv").is_file()
    assert (report_root / "review-summary.md").is_file()
    assert (store.run_root / "events.jsonl").read_bytes() == events_before
    assert (root / "manifests" / "sources.csv").read_bytes() == sources_before
    assert (root / "manifests" / "clips.csv").read_bytes() == clips_before


def test_review_ui_contains_required_controls_and_no_authored_long_dash() -> None:
    content = Path("scripts/train/review_ui.html").read_text(encoding="utf-8")

    assert "__REVIEW_TOKEN__" in content
    assert "自动保存草稿" in content
    assert all(label in content for label in ("对话文本", "评审备注", "接受", "拒绝", "暂缓"))
    assert "—" not in content
    assert "–" not in content


def test_review_ui_orders_inflight_draft_before_decision() -> None:
    content = Path("scripts/train/review_ui.html").read_text(encoding="utf-8")
    decision_start = content.index("async function decide(decision)")
    decision_request = content.index('api("/api/decisions"', decision_start)
    clear_timer = content.index("window.clearTimeout(state.draftTimer)", decision_start)
    await_draft = content.index("if (state.draftPromise) await state.draftPromise", decision_start)

    assert decision_start < clear_timer < await_draft < decision_request


def test_review_ui_crosses_batch_boundaries() -> None:
    content = Path("scripts/train/review_ui.html").read_text(encoding="utf-8")

    assert "await loadBatch(state.batch + 1)" in content
    assert "await loadBatch(state.batch - 1)" in content
