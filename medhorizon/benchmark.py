"""Dependency-free utilities for the released 1,253-question benchmark."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path, PurePosixPath


SYSTEM_PROMPT = (
    "You are a medical video analysis expert. Answer the multiple-choice question "
    "based on the video. Reply with only the option letter (A, B, C, or D)."
)

# The release's explicit rewrite kinds survive changes in question wording.
KIND_TO_TASK = {
    "surgical_phase": "PR", "ultrasound_contraction": "PR",
    "surgical_step": "SD", "gi_region": "RL", "bpq": "BPQ",
    "largest_lesion": "LLS", "lesion_site": "Site",
    "lesion_histology": "Hist", "lesion_size": "Size",
    "instrument_onset": "IR", "m11_instrument_coverage": "WR",
    "m11_rank_after": "WR", "m11_primary_step": "RSR",
    "m11_count": "CPR", "m11_fraction": "CPR",
    "lesion_distribution": "LA",
}
TASKS = {
    "PR": ("Phase / examination recognition", "Fine-grained Understanding", 517),
    "SD": ("Surgical step discrimination", "Fine-grained Understanding", 112),
    "RL": ("Region localization", "Fine-grained Understanding", 60),
    "BPQ": ("Bowel preparation quality", "Fine-grained Understanding", 39),
    "LLS": ("Largest lesion size", "Fine-grained Understanding", 39),
    "Site": ("Lesion site binding", "Fine-grained Understanding", 47),
    "Hist": ("Lesion histology binding", "Fine-grained Understanding", 47),
    "Size": ("Lesion size binding", "Fine-grained Understanding", 47),
    "IR": ("Instrument onset reasoning", "Semantic Reasoning", 235),
    "WR": ("Workload / instrument coverage ranking", "Semantic Reasoning", 26),
    "RSR": ("Rank-then-step retrieval", "Semantic Reasoning", 26),
    "CPR": ("Counting and proportion reasoning", "Semantic Reasoning", 26),
    "LA": ("Lesion site aggregation", "Semantic Reasoning", 32),
}


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(row)
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_uid(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise ValueError(f"Invalid question uid: {value!r}")
    return str(value)


def load_benchmark(path):
    """Validate video-grouped annotations and flatten them without renumbering IDs."""
    records = read_jsonl(path)
    if not records:
        raise ValueError("Benchmark is empty")
    items, uids, videos = [], set(), set()
    for record in records:
        for field in ("key", "dataset", "video_path", "qa"):
            if field not in record:
                raise ValueError(f"Video record is missing {field}")
        video_key = (record["dataset"], record["key"])
        if video_key in videos:
            raise ValueError(f"Duplicate video record: {video_key}")
        videos.add(video_key)
        video = record["video_path"]
        if not isinstance(video, str) or not video or "\\" in video:
            raise ValueError(f"Invalid video path: {video!r}")
        relative = PurePosixPath(video)
        if relative.is_absolute() or ".." in relative.parts or ":" in video:
            raise ValueError(f"Expected a safe relative video path: {video}")
        if record.get("split", "test") != "test":
            raise ValueError("MedHorizon is an evaluation-only test split")
        questions = record["qa"]
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"Video {video_key} has no QA list")
        for qa in questions:
            if not isinstance(qa, dict):
                raise ValueError(f"Invalid QA object for {video_key}")
            uid = normalize_uid(qa.get("uid"))
            if uid in uids:
                raise ValueError(f"Duplicate question uid: {uid}")
            uids.add(uid)
            if not isinstance(qa.get("question"), str) or not qa["question"].strip():
                raise ValueError(f"Question {uid}: missing question text")
            options = qa.get("options")
            if not isinstance(options, list) or len(options) != 4:
                raise ValueError(f"Question {uid}: expected four options")
            for letter, option in zip("ABCD", options):
                if not isinstance(option, str) or not re.match(rf"^{letter}\.\s+\S", option):
                    raise ValueError(f"Question {uid}: invalid {letter} option")
            if len({option[2:].strip().casefold() for option in options}) != 4:
                raise ValueError(f"Question {uid}: duplicate option text")
            if qa.get("answer") not in ("A", "B", "C", "D"):
                raise ValueError(f"Question {uid}: invalid gold answer")
            kind = qa.get("natural_rewrite_v1_kind")
            if kind not in KIND_TO_TASK:
                raise ValueError(f"Question {uid}: unknown release task kind {kind!r}")
            task = KIND_TO_TASK[kind]
            items.append({
                "uid": uid, "dataset": record["dataset"], "key": record["key"],
                "video_path": video, "question": qa["question"], "options": options,
                "answer": qa["answer"], "task_id": qa.get("task_id"), "task": task,
                "capability": TASKS[task][1],
            })
    return records, items


def dataset_summary(records, items):
    return {
        "videos": len(records), "questions": len(items),
        "sources": dict(sorted(Counter(r["dataset"] for r in records).items())),
        "questions_by_source": dict(sorted(Counter(i["dataset"] for i in items).items())),
        "questions_by_task": {task: sum(i["task"] == task for i in items) for task in TASKS},
        "questions_by_capability": dict(Counter(i["capability"] for i in items)),
        "answer_distribution": dict(sorted(Counter(i["answer"] for i in items).items())),
        "annotation_duration_hours": sum(float(r.get("duration_seconds", 0)) for r in records) / 3600,
    }


def validate_evidence(path, items):
    rows = read_jsonl(path)
    index = {item["uid"]: item for item in items}
    seen = set()
    for row in rows:
        uid = normalize_uid(row.get("uid"))
        if uid not in index or uid in seen:
            raise ValueError(f"Unknown or duplicate evidence uid: {uid}")
        seen.add(uid)
        if row.get("video_path") != index[uid]["video_path"] or row.get("task") != index[uid]["task"]:
            raise ValueError(f"Evidence identity mismatch for uid {uid}")
        for window in row.get("gt_frames", []):
            start, end = window["start"], window["end"]
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (start, end)):
                raise ValueError(f"Non-finite evidence window for uid {uid}")
            if start < 0 or end < start:
                raise ValueError(f"Invalid evidence window for uid {uid}")
    if seen != set(index):
        raise ValueError(f"Missing evidence records: {len(set(index) - seen)}")
    return {"questions": len(rows), "without_local_windows": sum(not r.get("gt_frames") for r in rows),
            "support_modes": dict(sorted(Counter(r["support_mode"] for r in rows).items()))}


def inference_rows(items, video_root=None, *, text_only=False, format="swift", check_videos=True):
    if not text_only and video_root is None:
        raise ValueError("--video-root is required for video input")
    root = Path(video_root).expanduser().resolve() if video_root else None
    checked = set()
    for item in items:
        video = str(root / item["video_path"]) if root else None
        if not text_only and check_videos and video not in checked:
            if not Path(video).is_file():
                raise ValueError(f"Missing video: {video}")
            checked.add(video)
        metadata = {key: item[key] for key in ("uid", "dataset", "key", "task_id", "task")}
        if format == "flat":
            row = {**metadata, "question": item["question"], "options": item["options"]}
            if not text_only:
                row["video"] = video
        else:
            prompt = "\n".join([item["question"], *item["options"], "Answer with the option letter only."])
            system = SYSTEM_PROMPT.replace("based on the video", "based on the question") if text_only else SYSTEM_PROMPT
            row = {"uid": item["uid"], "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": ("" if text_only else "<video>") + prompt},
            ], "_meta": metadata}
            if not text_only:
                row["videos"] = [video]
        yield row


def extract_answer(value, mode="strict"):
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if mode == "strict":
        return text if text in ("A", "B", "C", "D") else None
    # Explicit compatibility with the original workspace scoring scripts.
    if text and text[0] in "ABCD":
        return text[0]
    match = re.search(r"\b([A-D])\b", text)
    return match.group(1) if match else None


def prediction_uid(row):
    top = row.get("uid")
    meta = row.get("_meta", {})
    nested = meta.get("uid") if isinstance(meta, dict) else None
    if top is not None and nested is not None and normalize_uid(top) != normalize_uid(nested):
        raise ValueError("Conflicting uid and _meta.uid in prediction")
    return normalize_uid(top if top is not None else nested)


def score(items, predictions, *, field="prediction", mode="strict", allow_missing=False):
    gold = {item["uid"]: item for item in items}
    by_uid = {}
    for row in predictions:
        uid = prediction_uid(row)
        if uid not in gold:
            raise ValueError(f"Unknown prediction uid: {uid}")
        if uid in by_uid:
            raise ValueError(f"Duplicate prediction uid: {uid}")
        if field not in row:
            raise ValueError(f"Prediction {uid} lacks field {field!r}")
        by_uid[uid] = extract_answer(row[field], mode)
    missing = set(gold) - set(by_uid)
    if missing and not allow_missing:
        raise ValueError(f"Missing {len(missing)} predictions; use --allow-missing to count them as incorrect")
    details = [{**{k: item[k] for k in ("uid", "dataset", "key", "task", "capability")},
                "gold": item["answer"], "prediction": by_uid.get(item["uid"]),
                "missing": item["uid"] in missing,
                "correct": by_uid.get(item["uid"]) == item["answer"]} for item in items]

    def metric(rows):
        correct = sum(r["correct"] for r in rows)
        return {"correct": correct, "total": len(rows),
                "accuracy": 100 * correct / len(rows) if rows else None}

    result = {"answer_format": mode, "prediction_field": field,
              "overall": metric(details), "submitted": len(by_uid), "missing": len(missing),
              "invalid": sum(value is None for value in by_uid.values())}
    for dimension in ("task", "dataset", "capability"):
        values = TASKS if dimension == "task" else sorted({i[dimension] for i in items})
        result[f"by_{dimension}"] = {value: metric([r for r in details if r[dimension] == value]) for value in values}
    return result, details
