# Evaluation

## Standard protocol

Evaluate all 1,253 questions against their full source procedures. Give the model the final `question`, the four final `options`, and the video. The system prompt and answer-only instruction are provided by `medhorizon prepare`.

Use deterministic decoding where supported, and report model/checkpoint revision, software versions, sampling strategy, frame budget, spatial resolution/token cap, and generation settings. The test split is not a training or model-selection split.

For capped video inputs, sample across the entire procedure. A 1 FPS setting does not imply that every resulting frame reaches the model: the manuscript uses model-specific caps and uniform subsampling of the full candidate sequence. Fixed-frame rows use a specified frame count over the full video.

The optional `medhorizon.infer_swift` runner records requested settings and the input checksum beside predictions. Its `--max-frames`/`--fps` controls configure Qwen VL's processor through `FPS_MAX_FRAMES`/`FPS`. Other model families can have different controls; inspect the model's processor and record its effective frame count before reporting results. This is a reference inference path, not a guarantee of matching every model-specific experiment in the paper.

The source workspace's inference versions were ms-swift 4.0.1, Transformers 4.57.3, and qwen-vl-utils 0.0.14. The runner uses the `swift.infer_engine.TransformersEngine` interface. See [upstream inference documentation](https://github.com/modelscope/ms-swift/blob/main/docs/source_en/Instruction/Inference-and-deployment.md).

## Prediction format and scoring

```json
{"uid": "0", "prediction": "A"}
{"uid": "1", "prediction": "C"}
```

Use `uid` from the released annotations, not `uid_original` or a line number. Numeric and string IDs are both accepted. Rows may be in any order. `_meta.uid` is also supported for existing Swift outputs; if both IDs exist they must agree.

```bash
python -m medhorizon score \
  --predictions outputs/predictions.jsonl \
  --output outputs/metrics.json \
  --details outputs/per_question.jsonl
```

For a file whose model output is named `response`, add `--prediction-field response`. Files without question IDs must first be joined to their original inference manifest; the scorer never assumes row order.

Overall accuracy is `100 × correct / 1253` for the official release. Task, source, and capability accuracies use each group's question count. Invalid responses are incorrect. Missing predictions fail by default; `--allow-missing` counts them as incorrect while retaining the full denominator. Duplicate and unknown IDs always fail.

The **strict** parser accepts only A, B, C, or D after stripping whitespace and normalizing case. It does not infer a choice from prose. The opt-in **legacy** parser duplicates the original workspace behavior: use the first character if it is A–D, otherwise the first standalone A–D token. That parser can misread prose such as “Because…” as B, so always name the parser when comparing scores. Archived paper results were produced using the original experiment pipelines and have not been recomputed with the strict parser.

Task membership uses `natural_rewrite_v1_kind`, rather than guessing from question phrasing. The manifest records the exact 13 task counts. In this mapping, the 30 ultrasound examination questions belong to PR; lesion aggregation is LA (called LD in some older analysis files).

## Controls and evidence

Generate text-only input with:

```bash
python -m medhorizon prepare --text-only --output outputs/text_only.jsonl
```

Evidence windows are for audit and explicitly labeled oracle-evidence diagnostics. They must not be supplied to the standard full-video evaluation. Some support is global or proxy-based, and 10 questions have no resolved local window. Report how these cases are handled in any evidence-only experiment; do not silently drop them from ordinary QA accuracy.

The evidence files do not include decoded image crops or every historical analysis artifact. They preserve the available time/frame coordinates, provenance modes, and unresolved cases. See [evidence notes](data.md#evidence-metadata).

## Verification

```bash
python -m unittest discover -s tests -v
python -m medhorizon validate --manifest data/manifest.json --evidence data/evidence_windows.jsonl
python -m medhorizon prepare --text-only --output outputs/text_only.jsonl
python -m medhorizon.infer_swift --input outputs/text_only.jsonl \
  --model Qwen/Qwen3-VL-8B-Instruct --output outputs/dry_run.jsonl --dry-run
```

Validation covers all released records, checksums, task counts, and evidence alignment. The test suite exercises shuffled predictions, duplicate/unknown IDs, missing and invalid answers, and model-input isolation from gold labels. GPU model inference is an additional environment-dependent step and has not been rerun during this release preparation.
