"""创建、托管并应用角色语音的本地人工听审记录。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import tomllib
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import soundfile as sf
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from scripts.train.prepare_data import _process_source
from scripts.train.workspace import MANIFEST_COLUMNS, load_project

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
DECISIONS = frozenset({"accepted", "rejected", "deferred"})
MINIMUM_ACCEPTED_DURATION_S = 30 * 60
DEFAULT_BATCH_SIZE = 50
EVENT_SCHEMA_VERSION = 1
RUN_SCHEMA_VERSION = 1
EMPTY_EVENT_HASH = "0" * 64
DECISION_EXPORT_COLUMNS = (
    "item_id",
    "source_id",
    "origin",
    "queue_index",
    "batch",
    "scene",
    "priority_reason",
    "duration_s",
    "decision",
    "reviewer",
    "original_transcript",
    "final_transcript",
    "transcript_changed",
    "notes",
    "decision_sequence",
    "decision_event_id",
    "decided_at",
    "audio_sha256",
)
EVENT_EXPORT_COLUMNS = (
    "sequence",
    "event_id",
    "item_id",
    "source_id",
    "origin",
    "decision",
    "reviewer",
    "original_transcript",
    "previous_transcript",
    "transcript",
    "notes",
    "occurred_at",
    "previous_event_hash",
    "event_hash",
)
TEXT_REVISION_COLUMNS = (
    "item_id",
    "source_id",
    "decision",
    "reviewer",
    "original_transcript",
    "final_transcript",
    "decision_event_id",
    "decided_at",
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_inside(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"路径越出工作区：{relative}") from error
    return candidate


def _review_root(project_root: Path) -> Path:
    return project_root / "review" / "runs"


def _run_root(project_root: Path, run_id: str) -> Path:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id 只能使用字母、数字、点、下划线和连字符，长度为 3-80")
    return _resolve_inside(_review_root(project_root), run_id)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV 缺少表头：{path}")
        return list(reader.fieldnames), list(reader)


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write_bytes(path, encoded)


def _atomic_write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    encoded = "".join(_canonical_json(row) + "\n" for row in rows).encode("utf-8")
    _atomic_write_bytes(path, encoded)


def _append_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_canonical_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_notes(notes: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in notes.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator:
            values[key.strip()] = value.strip()
    return values


def _parse_auto_flags(notes: str) -> list[str]:
    match = re.search(r"(?:^|;\s*)auto_flags=([^;]*)", notes)
    if match is None or match.group(1).strip() in {"", "none"}:
        return []
    return [value for value in match.group(1).split("|") if value]


def _audio_duration(path: Path) -> float:
    info = sf.info(path)
    return float(info.frames / info.samplerate) if info.samplerate else 0.0


def _prepared_item(
    project_root: Path,
    clip: Mapping[str, str],
    source: Mapping[str, str],
) -> dict[str, Any]:
    audio_relpath = clip.get("audio_relpath", "").strip()
    audio_path = _resolve_inside(project_root, audio_relpath)
    if not audio_path.is_file():
        raise FileNotFoundError(f"评审音频不存在：{audio_path}")
    source_notes = _parse_notes(source.get("notes", ""))
    qc_flags = _parse_auto_flags(clip.get("review_notes", ""))
    transcript_review_required = source_notes.get("review_required", "").lower() == "true"
    if qc_flags and transcript_review_required:
        priority = 1
        priority_reason = "qc_and_transcript"
    elif qc_flags:
        priority = 2
        priority_reason = "qc"
    elif transcript_review_required:
        priority = 3
        priority_reason = "transcript"
    else:
        priority = 4
        priority_reason = "clean"
    return {
        "item_id": clip["clip_id"].strip(),
        "source_id": clip["source_id"].strip(),
        "origin": "prepared",
        "audio_relpath": audio_relpath,
        "audio_sha256": clip.get("audio_sha256", "").strip().lower(),
        "transcript": clip.get("transcript", "").strip(),
        "duration_s": float(clip.get("duration_s", "0") or 0),
        "scene": source.get("scene", "").strip(),
        "source_reference": source.get("source_reference", "").strip(),
        "usage_rights": source.get("usage_rights", "").strip(),
        "speaker": source.get("speaker", "").strip(),
        "source_notes": source.get("notes", "").strip(),
        "automatic_review_notes": clip.get("review_notes", "").strip(),
        "qc_flags": qc_flags,
        "transcript_review_required": transcript_review_required,
        "transcript_source": source_notes.get("transcript_source", ""),
        "match": source_notes.get("match", ""),
        "confidence": source_notes.get("confidence", ""),
        "priority": priority,
        "priority_reason": priority_reason,
        "metrics": {
            field: clip.get(field, "").strip()
            for field in (
                "sample_rate",
                "channels",
                "peak_dbfs",
                "noise_floor_dbfs",
                "snr_db",
                "silence_ratio",
                "clipping_ratio",
                "voiced_ratio",
                "f0_min_hz",
                "f0_median_hz",
                "f0_max_hz",
            )
        },
    }


def _raw_manifest_path(project_root: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        candidate = explicit.resolve()
        candidate.relative_to(project_root.resolve())
        if not candidate.is_file():
            raise FileNotFoundError(f"原始清单不存在：{candidate}")
        return candidate
    candidates = sorted((project_root / "audio" / "raw").glob("*/manifest.csv"))
    if len(candidates) > 1:
        raise ValueError("发现多个原始清单，请使用 --raw-manifest 明确指定")
    return candidates[0] if candidates else None


def _source_reference_prefix(sources: Sequence[Mapping[str, str]], package_name: str) -> str:
    for source in sources:
        reference = source.get("source_reference", "")
        marker = reference.find("ogg/")
        if marker >= 0:
            return reference[:marker]
    return f"StarRailVoice/{package_name}/"


def _unresolved_items(
    project_root: Path,
    sources: Sequence[Mapping[str, str]],
    raw_manifest: Path | None,
) -> list[dict[str, Any]]:
    if raw_manifest is None:
        return []
    header, raw_rows = _read_csv(raw_manifest)
    required = {"wem_id", "source", "ogg", "asr", "text"}
    if missing := sorted(required.difference(header)):
        raise ValueError(f"原始清单缺少列：{', '.join(missing)}")
    registered = {row["source_id"].strip() for row in sources}
    raw_root = raw_manifest.parent
    package_name = raw_root.name
    reference_prefix = _source_reference_prefix(sources, package_name)
    items: list[dict[str, Any]] = []
    for raw in raw_rows:
        source_id = f"tohsakarin_{raw['wem_id'].strip()}"
        if source_id in registered or raw.get("asr", "").strip() or raw.get("text", "").strip():
            continue
        audio_path = _resolve_inside(raw_root, raw["ogg"].strip())
        if not audio_path.is_file():
            raise FileNotFoundError(f"无文本音频不存在：{audio_path}")
        audio_relpath = audio_path.relative_to(project_root).as_posix()
        source_parts = Path(raw.get("source", "")).parts
        scene = source_parts[1] if len(source_parts) > 1 else "unresolved"
        items.append(
            {
                "item_id": source_id,
                "source_id": source_id,
                "origin": "unresolved",
                "audio_relpath": audio_relpath,
                "audio_sha256": _sha256_file(audio_path),
                "transcript": "",
                "duration_s": _audio_duration(audio_path),
                "scene": scene,
                "source_reference": f"{reference_prefix}{raw['ogg'].strip()}",
                "usage_rights": "local_research_only; game_asset; do_not_redistribute",
                "speaker": package_name,
                "source_notes": (
                    "transcript_source=manual_review; match=unresolved; "
                    "confidence=0.000; review_required=true"
                ),
                "automatic_review_notes": "auto_flags=not_processed",
                "qc_flags": ["not_processed"],
                "transcript_review_required": True,
                "transcript_source": "missing",
                "match": "unresolved",
                "confidence": "0.000",
                "priority": 0,
                "priority_reason": "missing_transcript",
                "metrics": {},
            }
        )
    return items


def _queue_statistics(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    priority_counts: dict[str, int] = {}
    scene_counts: dict[str, int] = {}
    for item in items:
        reason = str(item["priority_reason"])
        priority_counts[reason] = priority_counts.get(reason, 0) + 1
        scene = str(item.get("scene") or "unknown")
        scene_counts[scene] = scene_counts.get(scene, 0) + 1
    return {
        "total_items": len(items),
        "prepared_items": sum(item["origin"] == "prepared" for item in items),
        "unresolved_items": sum(item["origin"] == "unresolved" for item in items),
        "priority_counts": priority_counts,
        "scene_counts": dict(sorted(scene_counts.items())),
    }


def _load_project_identity(project_root: Path) -> tuple[str, str]:
    with (project_root / "project.toml").open("rb") as handle:
        project = tomllib.load(handle)
    return str(project["project_id"]), str(project["display_name"])


def create_review_run(
    project_root: Path,
    *,
    run_id: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    raw_manifest: Path | None = None,
) -> dict[str, Any]:
    """冻结一份不修改主清单的听审候选队列。"""
    project_root = project_root.resolve()
    if batch_size < 1 or batch_size > 200:
        raise ValueError("batch_size 必须在 1-200 之间")
    run_root = _run_root(project_root, run_id)
    if run_root.exists():
        raise FileExistsError(f"评审 run 已存在且不可覆盖：{run_root}")
    source_path = project_root / "manifests" / "sources.csv"
    clip_path = project_root / "manifests" / "clips.csv"
    source_header, sources = _read_csv(source_path)
    clip_header, clips = _read_csv(clip_path)
    if tuple(source_header) != MANIFEST_COLUMNS["sources.csv"]:
        raise ValueError("sources.csv 表头与工作区契约不一致")
    if tuple(clip_header) != MANIFEST_COLUMNS["clips.csv"]:
        raise ValueError("clips.csv 表头与工作区契约不一致")
    sources_by_id = {row["source_id"].strip(): row for row in sources}
    if len(sources_by_id) != len(sources):
        raise ValueError("sources.csv 存在重复 source_id")
    items: list[dict[str, Any]] = []
    for clip in clips:
        source_id = clip["source_id"].strip()
        if source_id not in sources_by_id:
            raise ValueError(f"clips.csv 引用了不存在的 source_id：{source_id}")
        items.append(_prepared_item(project_root, clip, sources_by_id[source_id]))
    raw_path = _raw_manifest_path(project_root, raw_manifest)
    items.extend(_unresolved_items(project_root, sources, raw_path))
    if len({str(item["item_id"]) for item in items}) != len(items):
        raise ValueError("评审队列存在重复 item_id")
    items.sort(key=lambda item: (int(item["priority"]), str(item["scene"]), str(item["item_id"])))
    for queue_index, item in enumerate(items):
        item["queue_index"] = queue_index
        item["batch"] = queue_index // batch_size + 1

    run_root.mkdir(parents=True, exist_ok=False)
    queue_path = run_root / "queue.jsonl"
    _atomic_write_jsonl(queue_path, items)
    (run_root / "events.jsonl").write_bytes(b"")
    _atomic_write_json(run_root / "drafts.json", {"schema_version": 1, "drafts": {}})
    project_id, display_name = _load_project_identity(project_root)
    tool_path = Path(__file__)
    ui_path = Path(__file__).with_name("review_ui.html")
    tool_snapshot = run_root / "tool-snapshot.py"
    ui_snapshot = run_root / "ui-snapshot.html"
    _atomic_write_bytes(tool_snapshot, tool_path.read_bytes())
    _atomic_write_bytes(ui_snapshot, ui_path.read_bytes())
    metadata = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "project_id": project_id,
        "display_name": display_name,
        "created_at": _utc_now(),
        "batch_size": batch_size,
        "item_count": len(items),
        "queue_sha256": _sha256_file(queue_path),
        "tool_sha256": _sha256_file(tool_path),
        "ui_sha256": _sha256_file(ui_path),
        "snapshots": {
            "tool": tool_snapshot.name,
            "ui": ui_snapshot.name,
        },
        "raw_manifest_relpath": (
            raw_path.relative_to(project_root).as_posix() if raw_path is not None else ""
        ),
        "base_manifests": {
            "sources.csv": _sha256_file(source_path),
            "clips.csv": _sha256_file(clip_path),
        },
        "queue_statistics": _queue_statistics(items),
    }
    _atomic_write_json(run_root / "run.json", metadata)
    store = ReviewStore(project_root, run_id)
    status = store.status()
    _write_stage_summary(run_root, metadata, status)
    return status


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取评审文件：{path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"评审文件必须是 JSON 对象：{path}")
    return value


class ReviewStore:
    """一个不可覆盖队列上的追加式决策存储。"""

    def __init__(self, project_root: Path, run_id: str) -> None:
        self.project_root = project_root.resolve()
        self.run_id = run_id
        self.run_root = _run_root(self.project_root, run_id)
        if not self.run_root.is_dir():
            raise FileNotFoundError(f"评审 run 不存在：{self.run_root}")
        self.metadata = _read_json(self.run_root / "run.json")
        if self.metadata.get("run_id") != run_id:
            raise ValueError("run.json 的 run_id 不匹配")
        self.items = self._load_queue()
        self.items_by_id = {str(item["item_id"]): item for item in self.items}
        self._lock = threading.Lock()

    def _load_queue(self) -> list[dict[str, Any]]:
        queue_path = self.run_root / "queue.jsonl"
        if _sha256_file(queue_path) != self.metadata["queue_sha256"]:
            raise ValueError("queue.jsonl 已偏离冻结哈希")
        rows: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(
            queue_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise ValueError(f"queue.jsonl:{line_number} 不是有效 JSON") from error
            if not isinstance(row, dict):
                raise ValueError(f"queue.jsonl:{line_number} 必须是对象")
            rows.append(row)
        if len(rows) != int(self.metadata["item_count"]):
            raise ValueError("queue.jsonl 数量与 run.json 不一致")
        return rows

    def _events(self) -> list[dict[str, Any]]:
        path = self.run_root / "events.jsonl"
        events: list[dict[str, Any]] = []
        previous_hash = EMPTY_EVENT_HASH
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as error:
                raise ValueError(f"events.jsonl:{line_number} 不是有效 JSON") from error
            if not isinstance(event, dict):
                raise ValueError(f"events.jsonl:{line_number} 必须是对象")
            event_hash = str(event.get("event_hash", ""))
            unsigned = {key: value for key, value in event.items() if key != "event_hash"}
            expected_hash = _sha256_bytes(_canonical_json(unsigned).encode("utf-8"))
            if event.get("sequence") != line_number:
                raise ValueError(f"events.jsonl:{line_number} sequence 不连续")
            if event.get("previous_event_hash") != previous_hash or event_hash != expected_hash:
                raise ValueError(f"events.jsonl:{line_number} 哈希链校验失败")
            previous_hash = event_hash
            events.append(event)
        return events

    def _latest(self, events: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for event in events:
            latest[str(event["item_id"])] = dict(event)
        return latest

    def drafts(self) -> dict[str, dict[str, Any]]:
        payload = _read_json(self.run_root / "drafts.json")
        drafts = payload.get("drafts", {})
        if not isinstance(drafts, dict):
            raise ValueError("drafts.json 的 drafts 必须是对象")
        return {str(key): dict(value) for key, value in drafts.items() if isinstance(value, dict)}

    def save_draft(
        self,
        item_id: str,
        *,
        reviewer: str,
        transcript: str,
        notes: str,
    ) -> dict[str, Any]:
        self._validate_fields(item_id, reviewer, transcript, notes)
        with self._lock:
            drafts = self.drafts()
            draft = {
                "item_id": item_id,
                "reviewer": reviewer.strip(),
                "transcript": transcript.strip(),
                "notes": notes.strip(),
                "updated_at": _utc_now(),
            }
            drafts[item_id] = draft
            _atomic_write_json(
                self.run_root / "drafts.json",
                {"schema_version": 1, "drafts": drafts},
            )
            return draft

    def _validate_fields(self, item_id: str, reviewer: str, transcript: str, notes: str) -> None:
        if item_id not in self.items_by_id:
            raise KeyError(f"未知评审条目：{item_id}")
        if not reviewer.strip() or len(reviewer.strip()) > 120:
            raise ValueError("reviewer 必填且不能超过 120 个字符")
        if len(transcript) > 10_000:
            raise ValueError("transcript 不能超过 10000 个字符")
        if len(notes) > 2_000:
            raise ValueError("notes 不能超过 2000 个字符")

    def record_decision(
        self,
        *,
        request_id: str,
        item_id: str,
        decision: str,
        reviewer: str,
        transcript: str,
        notes: str,
    ) -> tuple[dict[str, Any], bool]:
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise ValueError("request_id 格式无效")
        if decision not in DECISIONS:
            raise ValueError("decision 必须是 accepted/rejected/deferred")
        self._validate_fields(item_id, reviewer, transcript, notes)
        item = self.items_by_id[item_id]
        if decision == "accepted" and not transcript.strip():
            raise ValueError("接受条目时 transcript 不能为空")
        with self._lock:
            events = self._events()
            duplicate = next(
                (event for event in events if event.get("request_id") == request_id), None
            )
            if duplicate is not None:
                return duplicate, True
            latest = self._latest(events)
            previous = latest.get(item_id)
            event: dict[str, Any] = {
                "schema_version": EVENT_SCHEMA_VERSION,
                "sequence": len(events) + 1,
                "event_id": uuid.uuid4().hex,
                "request_id": request_id,
                "run_id": self.run_id,
                "item_id": item_id,
                "source_id": item["source_id"],
                "origin": item["origin"],
                "decision": decision,
                "reviewer": reviewer.strip(),
                "original_transcript": str(item.get("transcript", "")),
                "previous_transcript": (
                    str(previous["transcript"]) if previous is not None else str(item["transcript"])
                ),
                "transcript": transcript.strip(),
                "notes": notes.strip(),
                "audio_sha256": item["audio_sha256"],
                "occurred_at": _utc_now(),
                "previous_event_hash": events[-1]["event_hash"] if events else EMPTY_EVENT_HASH,
            }
            event["event_hash"] = _sha256_bytes(_canonical_json(event).encode("utf-8"))
            event_path = self.run_root / "events.jsonl"
            with event_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(event) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            drafts = self.drafts()
            drafts.pop(item_id, None)
            _atomic_write_json(
                self.run_root / "drafts.json",
                {"schema_version": 1, "drafts": drafts},
            )
            status = self._status_from_events([*events, event])
            _atomic_write_json(self.run_root / "status.json", status)
            return event, False

    def _status_from_events(self, events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        latest = self._latest(events)
        counts = {"accepted": 0, "rejected": 0, "deferred": 0, "pending": 0}
        accepted_duration_s = 0.0
        transcript_changes = 0
        for item in self.items:
            event = latest.get(str(item["item_id"]))
            if event is None:
                counts["pending"] += 1
                continue
            decision = str(event["decision"])
            counts[decision] += 1
            if decision == "accepted":
                accepted_duration_s += float(item.get("duration_s", 0))
            if str(event["transcript"]) != str(item.get("transcript", "")):
                transcript_changes += 1
        blockers: list[str] = []
        if counts["pending"]:
            blockers.append(f"仍有 {counts['pending']} 条未处理")
        if counts["deferred"]:
            blockers.append(f"仍有 {counts['deferred']} 条暂缓")
        if accepted_duration_s < MINIMUM_ACCEPTED_DURATION_S:
            blockers.append(
                f"接受时长 {accepted_duration_s:.3f} 秒，少于 {MINIMUM_ACCEPTED_DURATION_S} 秒"
            )
        resolved = counts["accepted"] + counts["rejected"]
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "updated_at": _utc_now(),
            "total_items": len(self.items),
            "batch_size": int(self.metadata["batch_size"]),
            "batch_count": (
                (len(self.items) + int(self.metadata["batch_size"]) - 1)
                // int(self.metadata["batch_size"])
            ),
            "decision_counts": counts,
            "resolved_items": resolved,
            "remaining_items": len(self.items) - resolved,
            "accepted_duration_s": round(accepted_duration_s, 6),
            "accepted_duration_minutes": round(accepted_duration_s / 60, 3),
            "minimum_accepted_duration_s": MINIMUM_ACCEPTED_DURATION_S,
            "transcript_changes": transcript_changes,
            "event_count": len(events),
            "event_head_sha256": events[-1]["event_hash"] if events else EMPTY_EVENT_HASH,
            "queue_statistics": self.metadata["queue_statistics"],
            "ready_to_apply": not blockers,
            "blockers": blockers,
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            status = self._status_from_events(self._events())
            _atomic_write_json(self.run_root / "status.json", status)
            return status

    def page(self, batch: int) -> dict[str, Any]:
        if batch < 1:
            raise ValueError("batch 必须大于等于 1")
        size = int(self.metadata["batch_size"])
        start = (batch - 1) * size
        selected = self.items[start : start + size]
        events = self._events()
        latest = self._latest(events)
        drafts = self.drafts()
        enriched: list[dict[str, Any]] = []
        for item in selected:
            item_id = str(item["item_id"])
            enriched.append(
                {**item, "latest_decision": latest.get(item_id), "draft": drafts.get(item_id)}
            )
        return {
            "run": self.metadata,
            "status": self._status_from_events(events),
            "batch": batch,
            "items": enriched,
        }

    def audio_path(self, item_id: str) -> Path:
        if item_id not in self.items_by_id:
            raise KeyError(item_id)
        path = _resolve_inside(self.project_root, str(self.items_by_id[item_id]["audio_relpath"]))
        if not path.is_file():
            raise FileNotFoundError(path)
        return path


def _write_stage_summary(
    run_root: Path,
    metadata: Mapping[str, Any],
    status: Mapping[str, Any],
) -> None:
    statistics = metadata["queue_statistics"]
    priority = statistics["priority_counts"]
    lines = [
        f"# {metadata['run_id']} 听审候选",
        "",
        f"- 创建时间：{metadata['created_at']}",
        f"- 总条目：{status['total_items']}",
        f"- 已处理音频：{statistics['prepared_items']}",
        f"- 无文本补录：{statistics['unresolved_items']}",
        f"- 每批：{status['batch_size']}",
        f"- 批次数：{status['batch_count']}",
        f"- 队列哈希：`{metadata['queue_sha256']}`",
        "",
        "## 优先队列",
        "",
    ]
    for key in ("missing_transcript", "qc_and_transcript", "qc", "transcript", "clean"):
        lines.append(f"- {key}: {priority.get(key, 0)}")
    lines.extend(
        [
            "",
            "主清单尚未修改。人工决定写入 events.jsonl，只有显式执行 apply 才会回写。",
        ]
    )
    _atomic_write_bytes(run_root / "stage-1-summary.md", ("\n".join(lines) + "\n").encode("utf-8"))


def _reconcile_redundant_drafts(
    store: ReviewStore,
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    latest = store._latest(events)
    drafts = store.drafts()
    redundant: list[dict[str, Any]] = []
    for item_id, draft in tuple(drafts.items()):
        event = latest.get(item_id)
        if event is None:
            continue
        same_content = all(
            str(draft.get(field, "")) == str(event.get(field, ""))
            for field in ("reviewer", "transcript", "notes")
        )
        written_after_decision = str(draft.get("updated_at", "")) >= str(
            event.get("occurred_at", "")
        )
        if not same_content or not written_after_decision:
            continue
        redundant.append(
            {
                "schema_version": 1,
                "archived_at": _utc_now(),
                "reason": "byte_identical_draft_written_after_decision",
                "item_id": item_id,
                "draft": draft,
                "decision_event_id": event["event_id"],
                "decision_event_hash": event["event_hash"],
            }
        )
        del drafts[item_id]
    if redundant:
        _append_jsonl(store.run_root / "draft-archive.jsonl", redundant)
        _atomic_write_json(
            store.run_root / "drafts.json",
            {"schema_version": 1, "drafts": drafts},
        )
    return redundant


def _decision_export_rows(
    store: ReviewStore,
    latest: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in store.items:
        item_id = str(item["item_id"])
        event = latest.get(item_id)
        original = str(item.get("transcript", ""))
        final = str(event["transcript"]) if event is not None else original
        rows.append(
            {
                "item_id": item_id,
                "source_id": str(item["source_id"]),
                "origin": str(item["origin"]),
                "queue_index": str(item["queue_index"]),
                "batch": str(item["batch"]),
                "scene": str(item.get("scene", "")),
                "priority_reason": str(item["priority_reason"]),
                "duration_s": str(item.get("duration_s", "")),
                "decision": str(event["decision"]) if event is not None else "pending",
                "reviewer": str(event["reviewer"]) if event is not None else "",
                "original_transcript": original,
                "final_transcript": final,
                "transcript_changed": str(final != original).lower(),
                "notes": str(event["notes"]) if event is not None else "",
                "decision_sequence": str(event["sequence"]) if event is not None else "",
                "decision_event_id": str(event["event_id"]) if event is not None else "",
                "decided_at": str(event["occurred_at"]) if event is not None else "",
                "audio_sha256": str(item["audio_sha256"]),
            }
        )
    return rows


def _event_export_rows(events: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {column: str(event.get(column, "")) for column in EVENT_EXPORT_COLUMNS} for event in events
    ]


def _text_revision_rows(
    decision_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    return [
        {
            "item_id": row["item_id"],
            "source_id": row["source_id"],
            "decision": row["decision"],
            "reviewer": row["reviewer"],
            "original_transcript": row["original_transcript"],
            "final_transcript": row["final_transcript"],
            "decision_event_id": row["decision_event_id"],
            "decided_at": row["decided_at"],
        }
        for row in decision_rows
        if row["transcript_changed"] == "true"
    ]


def _review_report_markdown(summary: Mapping[str, Any]) -> str:
    counts = summary["decision_counts"]
    lines = [
        f"# {summary['run_id']} 人工听审整理",
        "",
        f"- 报告 revision：`{summary['report_revision']}`",
        f"- 事件头哈希：`{summary['event_head_sha256']}`",
        f"- 唯一已决定条目：{summary['decided_items']} / {summary['total_items']}",
        f"- 接受：{counts['accepted']}",
        f"- 拒绝：{counts['rejected']}",
        f"- 暂缓：{counts['deferred']}",
        f"- 未处理：{counts['pending']}",
        f"- 接受时长：{summary['accepted_duration_minutes']:.3f} 分钟",
        f"- 文本修订：{summary['transcript_changes']}",
        f"- 重复决定事件：{summary['superseded_events']}",
        f"- 归档冗余草稿：{summary['redundant_drafts_archived']}",
        "",
        "## 场景分布",
        "",
    ]
    for scene, scene_counts in summary["scene_distribution"].items():
        lines.append(
            f"- {scene}: 接受 {scene_counts.get('accepted', 0)}，"
            f"拒绝 {scene_counts.get('rejected', 0)}，"
            f"暂缓 {scene_counts.get('deferred', 0)}，"
            f"未处理 {scene_counts.get('pending', 0)}"
        )
    lines.extend(["", "## 当前阻塞", ""])
    if summary["blockers"]:
        lines.extend(f"- {blocker}" for blocker in summary["blockers"])
    else:
        lines.append("- 无，可进入 apply 审批。")
    return "\n".join(lines) + "\n"


def organize_review_run(
    project_root: Path,
    *,
    run_id: str,
    reconcile_redundant_drafts: bool = False,
) -> dict[str, Any]:
    """把当前事件头对应的最新决定整理为不可覆盖报告。"""
    store = ReviewStore(project_root, run_id)
    events = store._events()
    archived = _reconcile_redundant_drafts(store, events) if reconcile_redundant_drafts else []
    status = store.status()
    latest = store._latest(events)
    decision_rows = _decision_export_rows(store, latest)
    event_counts = Counter(str(event["item_id"]) for event in events)
    superseded = sum(max(0, count - 1) for count in event_counts.values())
    scene_distribution: dict[str, dict[str, int]] = {}
    for row in decision_rows:
        scene = row["scene"] or "unknown"
        scene_counts = scene_distribution.setdefault(
            scene,
            dict.fromkeys((*DECISIONS, "pending"), 0),
        )
        scene_counts[row["decision"]] += 1
    rejection_reasons = Counter(
        row["notes"] or "未填写原因" for row in decision_rows if row["decision"] == "rejected"
    )
    revision = f"review-report-{status['event_head_sha256'][:12]}"
    report_root = store.run_root / "reports" / revision
    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "report_revision": revision,
        "organized_at": _utc_now(),
        "event_head_sha256": status["event_head_sha256"],
        "event_count": status["event_count"],
        "decided_items": len(latest),
        "total_items": status["total_items"],
        "decision_counts": status["decision_counts"],
        "accepted_duration_s": status["accepted_duration_s"],
        "accepted_duration_minutes": status["accepted_duration_minutes"],
        "transcript_changes": status["transcript_changes"],
        "superseded_events": superseded,
        "items_with_multiple_decisions": {
            item_id: count for item_id, count in sorted(event_counts.items()) if count > 1
        },
        "redundant_drafts_archived": len(archived),
        "remaining_active_drafts": len(store.drafts()),
        "rejection_reasons": dict(sorted(rejection_reasons.items())),
        "scene_distribution": dict(sorted(scene_distribution.items())),
        "ready_to_apply": status["ready_to_apply"],
        "blockers": status["blockers"],
        "primary_manifests_modified": False,
    }
    if report_root.exists():
        existing = _read_json(report_root / "review-summary.json")
        if existing.get("event_head_sha256") != status["event_head_sha256"]:
            raise ValueError(f"报告 revision 冲突：{report_root}")
        return existing
    report_root.mkdir(parents=True, exist_ok=False)
    _atomic_write_csv(
        report_root / "review-decisions.csv",
        DECISION_EXPORT_COLUMNS,
        decision_rows,
    )
    _atomic_write_csv(
        report_root / "event-history.csv",
        EVENT_EXPORT_COLUMNS,
        _event_export_rows(events),
    )
    _atomic_write_csv(
        report_root / "text-revisions.csv",
        TEXT_REVISION_COLUMNS,
        _text_revision_rows(decision_rows),
    )
    _atomic_write_json(report_root / "review-summary.json", summary)
    _atomic_write_bytes(
        report_root / "review-summary.md",
        _review_report_markdown(summary).encode("utf-8"),
    )
    if archived:
        _atomic_write_jsonl(report_root / "archived-redundant-drafts.jsonl", archived)
    return summary


def _human_review_notes(automatic: str, human: str) -> str:
    if not human:
        return automatic
    return f"{automatic}; human_note={human}" if automatic else f"human_note={human}"


def apply_review_run(project_root: Path, *, run_id: str, confirm_run_id: str) -> dict[str, Any]:
    """在完整性门禁通过后，将最新人工决定一次性同步到主清单。"""
    if confirm_run_id != run_id:
        raise ValueError("--confirm-run-id 必须与 run_id 完全一致")
    store = ReviewStore(project_root, run_id)
    receipt_path = store.run_root / "apply-receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"该 run 已应用：{receipt_path}")
    status = store.status()
    if not status["ready_to_apply"]:
        raise ValueError("评审结果尚不能应用：" + "；".join(status["blockers"]))
    source_path = store.project_root / "manifests" / "sources.csv"
    clip_path = store.project_root / "manifests" / "clips.csv"
    for name, path in (("sources.csv", source_path), ("clips.csv", clip_path)):
        expected = store.metadata["base_manifests"][name]
        if _sha256_file(path) != expected:
            raise ValueError(f"{name} 已在评审创建后变化，拒绝回写")

    _, source_rows = _read_csv(source_path)
    _, clip_rows = _read_csv(clip_path)
    sources_by_id = {row["source_id"].strip(): row for row in source_rows}
    clips_by_id = {row["clip_id"].strip(): row for row in clip_rows}
    events = store._events()
    latest = store._latest(events)
    project = load_project(store.project_root)
    added_sources = 0
    excluded_unresolved = 0
    transcript_updates = 0
    for item in store.items:
        item_id = str(item["item_id"])
        event = latest[item_id]
        transcript = str(event["transcript"]).strip()
        if transcript != str(item.get("transcript", "")):
            transcript_updates += 1
        if item["origin"] == "unresolved":
            if event["decision"] == "rejected":
                excluded_unresolved += 1
                continue
            source_row = dict.fromkeys(MANIFEST_COLUMNS["sources.csv"], "")
            source_row.update(
                {
                    "source_id": item_id,
                    "audio_relpath": str(item["audio_relpath"]),
                    "transcript": transcript,
                    "source_reference": str(item["source_reference"]),
                    "usage_rights": str(item["usage_rights"]),
                    "speaker": str(item["speaker"]),
                    "scene": str(item["scene"]),
                    "notes": str(item["source_notes"]),
                }
            )
            clip_row = _process_source(
                store.project_root,
                source_row,
                project=project,
                existing=None,
            )
            clip_row.update(
                {
                    "review_status": "accepted",
                    "reviewer": str(event["reviewer"]),
                    "review_notes": _human_review_notes(
                        clip_row["review_notes"], str(event["notes"])
                    ),
                }
            )
            source_rows.append(source_row)
            clip_rows.append(clip_row)
            sources_by_id[item_id] = source_row
            clips_by_id[item_id] = clip_row
            added_sources += 1
            continue
        source_row = sources_by_id[str(item["source_id"])]
        clip_row = clips_by_id[item_id]
        source_row["transcript"] = transcript
        clip_row.update(
            {
                "transcript": transcript,
                "review_status": str(event["decision"]),
                "reviewer": str(event["reviewer"]),
                "review_notes": _human_review_notes(
                    str(item["automatic_review_notes"]), str(event["notes"])
                ),
            }
        )

    before = {"sources.csv": source_path.read_bytes(), "clips.csv": clip_path.read_bytes()}
    try:
        _atomic_write_csv(source_path, MANIFEST_COLUMNS["sources.csv"], source_rows)
        _atomic_write_csv(
            clip_path,
            MANIFEST_COLUMNS["clips.csv"],
            sorted(clip_rows, key=lambda row: row["clip_id"]),
        )
    except BaseException:
        _atomic_write_bytes(source_path, before["sources.csv"])
        _atomic_write_bytes(clip_path, before["clips.csv"])
        raise
    receipt = {
        "schema_version": 1,
        "run_id": run_id,
        "applied_at": _utc_now(),
        "event_count": status["event_count"],
        "event_head_sha256": status["event_head_sha256"],
        "accepted": status["decision_counts"]["accepted"],
        "rejected": status["decision_counts"]["rejected"],
        "accepted_duration_s": status["accepted_duration_s"],
        "transcript_updates": transcript_updates,
        "added_sources": added_sources,
        "excluded_unresolved": excluded_unresolved,
        "manifests": {
            "sources.csv": _sha256_file(source_path),
            "clips.csv": _sha256_file(clip_path),
        },
    }
    _atomic_write_json(receipt_path, receipt)
    return receipt


def _authorized(request: Request, token: str) -> bool:
    return secrets.compare_digest(request.headers.get("x-review-token", ""), token)


def _json_error(message: str, *, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


def create_review_app(store: ReviewStore, *, token: str) -> Starlette:
    """创建只面向本机浏览器的有界评审应用。"""
    ui_path = Path(__file__).with_name("review_ui.html")

    async def index(request: Request) -> Response:
        del request
        content = ui_path.read_text(encoding="utf-8").replace("__REVIEW_TOKEN__", token)
        return HTMLResponse(content, headers={"Cache-Control": "no-store"})

    async def health(request: Request) -> Response:
        del request
        return JSONResponse({"status": "ok", "service": "voice-review", "run_id": store.run_id})

    async def page(request: Request) -> Response:
        if not _authorized(request, token):
            return _json_error("unauthorized", status_code=401)
        try:
            batch = int(request.query_params.get("batch", "1"))
            return JSONResponse(store.page(batch))
        except (KeyError, OSError, ValueError) as error:
            return _json_error(str(error))

    async def status(request: Request) -> Response:
        if not _authorized(request, token):
            return _json_error("unauthorized", status_code=401)
        try:
            return JSONResponse(store.status())
        except (OSError, ValueError) as error:
            return _json_error(str(error), status_code=409)

    async def save_draft(request: Request) -> Response:
        if not _authorized(request, token):
            return _json_error("unauthorized", status_code=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是 JSON 对象")
            item_id = str(request.path_params["item_id"])
            draft = store.save_draft(
                item_id,
                reviewer=str(payload.get("reviewer", "")),
                transcript=str(payload.get("transcript", "")),
                notes=str(payload.get("notes", "")),
            )
            return JSONResponse({"ok": True, "draft": draft})
        except (KeyError, OSError, TypeError, ValueError) as error:
            return _json_error(str(error))

    async def decide(request: Request) -> Response:
        if not _authorized(request, token):
            return _json_error("unauthorized", status_code=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是 JSON 对象")
            event, duplicate = store.record_decision(
                request_id=str(payload.get("request_id", "")),
                item_id=str(payload.get("item_id", "")),
                decision=str(payload.get("decision", "")),
                reviewer=str(payload.get("reviewer", "")),
                transcript=str(payload.get("transcript", "")),
                notes=str(payload.get("notes", "")),
            )
            return JSONResponse(
                {"ok": True, "duplicate": duplicate, "event": event, "status": store.status()}
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            return _json_error(str(error))

    async def audio(request: Request) -> Response:
        try:
            item_id = str(request.path_params["item_id"])
            path = store.audio_path(item_id)
        except (KeyError, FileNotFoundError, ValueError):
            return _json_error("audio_not_found", status_code=404)
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-store"})

    return Starlette(
        routes=[
            Route("/", index, methods=["GET"]),
            Route("/health", health, methods=["GET"]),
            Route("/api/page", page, methods=["GET"]),
            Route("/api/status", status, methods=["GET"]),
            Route("/api/drafts/{item_id:str}", save_draft, methods=["PUT"]),
            Route("/api/decisions", decide, methods=["POST"]),
            Route("/audio/{item_id:str}", audio, methods=["GET"]),
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="角色语音本地人工听审")
    parser.add_argument("--project", type=Path, default=Path("songs"))
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="创建不可覆盖的评审候选 run")
    create.add_argument("--run-id", required=True)
    create.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    create.add_argument("--raw-manifest", type=Path)

    serve = commands.add_parser("serve", help="在 127.0.0.1 托管听审页")
    serve.add_argument("--run-id", required=True)
    serve.add_argument("--port", type=int, default=8771)

    status = commands.add_parser("status", help="重建并输出评审状态")
    status.add_argument("--run-id", required=True)

    organize = commands.add_parser("organize", help="整理当前事件头的决定与文本修订报告")
    organize.add_argument("--run-id", required=True)
    organize.add_argument("--reconcile-redundant-drafts", action="store_true")

    apply = commands.add_parser("apply", help="通过完整性门禁后回写主清单")
    apply.add_argument("--run-id", required=True)
    apply.add_argument("--confirm-run-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_root = args.project.resolve()
    try:
        if args.command == "create":
            payload = create_review_run(
                project_root,
                run_id=args.run_id,
                batch_size=args.batch_size,
                raw_manifest=args.raw_manifest,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status":
            print(
                json.dumps(
                    ReviewStore(project_root, args.run_id).status(), ensure_ascii=False, indent=2
                )
            )
            return 0
        if args.command == "organize":
            payload = organize_review_run(
                project_root,
                run_id=args.run_id,
                reconcile_redundant_drafts=args.reconcile_redundant_drafts,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "apply":
            payload = apply_review_run(
                project_root,
                run_id=args.run_id,
                confirm_run_id=args.confirm_run_id,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if not 1 <= args.port <= 65535:
            raise ValueError("port 必须在 1-65535 之间")
        store = ReviewStore(project_root, args.run_id)
        token = secrets.token_urlsafe(32)
        app = create_review_app(store, token=token)
        print(f"听审页：http://127.0.0.1:{args.port}/", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
        return 0
    except (FileExistsError, FileNotFoundError, KeyError, OSError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
