"""Optional ms-swift 4.0.1 inference runner that preserves benchmark UIDs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .benchmark import prediction_uid, read_jsonl, sha256


def check_requests(rows):
    seen = set()
    for row in rows:
        uid = prediction_uid(row)
        if uid in seen:
            raise ValueError(f"Duplicate input uid: {uid}")
        seen.add(uid)
        if any(key in row for key in ("answer", "response", "solution", "label")):
            raise ValueError("Inference input contains gold labels; run medhorizon prepare first")
        messages = row.get("messages", [])
        if not messages or any(m.get("role") not in ("system", "user") for m in messages):
            raise ValueError(f"Question {uid}: inference input must contain only system/user messages")
        for path in row.get("videos", []):
            if not Path(path).is_file():
                raise ValueError(f"Missing video: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-type")
    parser.add_argument("--revision")
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--attn-impl", default="sdpa")
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--max-frames", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without loading a model")
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Output must differ from input")
        if args.max_frames < 4 or args.max_tokens < 1 or args.fps <= 0:
            raise ValueError("Use at least four frames and positive fps/max-tokens")
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        rows = read_jsonl(args.input)
        if args.limit is not None:
            rows = rows[:args.limit]
        if not rows:
            raise ValueError("Inference input is empty")
        check_requests(rows)
        if args.dry_run:
            print(f"Validated {len(rows)} requests; no model was loaded.")
            return
        manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
        manifest = {k: v for k, v in vars(args).items() if k not in ("resume", "dry_run")}
        manifest = {k: str(v) if isinstance(v, Path) else v for k, v in manifest.items()}
        manifest["input_sha256"] = sha256(args.input)
        done = set()
        if args.output.exists():
            if not args.resume:
                raise ValueError("Output exists; choose a new file or use --resume")
            if not manifest_path.exists() or json.loads(manifest_path.read_text()) != manifest:
                raise ValueError("Resume requires an identical input file and inference configuration")
            expected = {prediction_uid(row) for row in rows}
            for row in read_jsonl(args.output):
                uid = prediction_uid(row)
                if uid in done or uid not in expected or not isinstance(row.get("prediction"), str):
                    raise ValueError(f"Invalid existing prediction: {uid}")
                done.add(uid)
        pending = [row for row in rows if prediction_uid(row) not in done]
        if not pending:
            print("All requests already have predictions.")
            return
        # Set before importing video processors. These controls apply to Qwen VL;
        # other model families may use their own frame-budget settings.
        os.environ["FPS"] = str(args.fps)
        os.environ["FPS_MAX_FRAMES"] = str(args.max_frames)
        os.environ["FPS_MIN_FRAMES"] = "4"
        os.environ["FORCE_QWENVL_VIDEO_READER"] = "decord"
        from swift.infer_engine import InferRequest, RequestConfig, TransformersEngine

        engine = TransformersEngine(
            args.model, model_type=args.model_type, revision=args.revision,
            device_map=args.device_map, attn_impl=args.attn_impl,
            max_batch_size=1, use_hf=True,
        )
        request_config = RequestConfig(max_tokens=args.max_tokens, temperature=0)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with args.output.open("a" if args.resume else "x", encoding="utf-8") as stream:
            for count, row in enumerate(pending, len(done) + 1):
                # Explicit allowlist: neither gold answers nor evidence enter the model request.
                request = InferRequest(messages=row["messages"], videos=row.get("videos", []))
                response = engine.infer([request], request_config)[0]
                if isinstance(response, Exception):
                    raise response
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError(f"Question {prediction_uid(row)}: model returned no text")
                result = {"uid": prediction_uid(row), "prediction": content}
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                print(f"{count}/{len(rows)} uid={result['uid']}", flush=True)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
