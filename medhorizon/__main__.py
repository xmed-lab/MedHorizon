from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import (dataset_summary, inference_rows, load_benchmark, read_jsonl,
                        score, sha256, validate_evidence, write_jsonl)


def main():
    parser = argparse.ArgumentParser(description="Prepare and evaluate the MedHorizon benchmark.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "prepare", "score"):
        command = commands.add_parser(name)
        command.add_argument("--annotations", type=Path, default=Path("data/medhorizon_test.jsonl"))
        if name == "validate":
            command.add_argument("--manifest", type=Path)
            command.add_argument("--evidence", type=Path)
            command.add_argument("--output", type=Path)
        elif name == "prepare":
            command.add_argument("--video-root", type=Path)
            command.add_argument("--text-only", action="store_true")
            command.add_argument("--format", choices=("swift", "flat"), default="swift")
            command.add_argument("--skip-video-check", action="store_true")
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--predictions", type=Path, required=True)
            command.add_argument("--prediction-field", default="prediction")
            command.add_argument("--answer-format", choices=("strict", "legacy"), default="strict")
            command.add_argument("--allow-missing", action="store_true")
            command.add_argument("--output", type=Path)
            command.add_argument("--details", type=Path)
    args = parser.parse_args()
    try:
        inputs = {args.annotations.resolve()}
        for name in ("manifest", "evidence"):
            path = getattr(args, name, None)
            if path:
                inputs.add(path.resolve())
        if args.command == "score":
            inputs.add(args.predictions.resolve())
        for name in ("output", "details"):
            path = getattr(args, name, None)
            if path and path.resolve() in inputs:
                raise ValueError("Output must not overwrite an input file")
        if getattr(args, "details", None) and args.output and args.details.resolve() == args.output.resolve():
            raise ValueError("Summary and details must use different output paths")
        records, items = load_benchmark(args.annotations)
        if args.command == "validate":
            result = dataset_summary(records, items)
            result["annotations_sha256"] = sha256(args.annotations)
            if args.manifest:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                if result["annotations_sha256"] != manifest["annotations_sha256"]:
                    raise ValueError("Annotation checksum differs from the release manifest")
                for key in ("videos", "questions", "questions_by_task"):
                    if result[key] != manifest[key]:
                        raise ValueError(f"Release manifest mismatch: {key}")
            if args.evidence:
                result["evidence"] = validate_evidence(args.evidence, items)
                if args.manifest and sha256(args.evidence) != manifest["evidence_sha256"]:
                    raise ValueError("Evidence checksum differs from the release manifest")
        elif args.command == "prepare":
            rows = list(inference_rows(items, args.video_root, text_only=args.text_only,
                        format=args.format, check_videos=not args.skip_video_check))
            write_jsonl(args.output, rows)
            print(f"Wrote {len(rows)} inference rows without gold answers to {args.output}")
            return
        else:
            result, details = score(items, read_jsonl(args.predictions), field=args.prediction_field,
                                    mode=args.answer_format, allow_missing=args.allow_missing)
            result["annotations_sha256"] = sha256(args.annotations)
            result["predictions_sha256"] = sha256(args.predictions)
            if args.details:
                write_jsonl(args.details, details)
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
