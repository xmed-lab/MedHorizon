# Data and access

## Video access

The [Hugging Face release](https://huggingface.co/datasets/DBD123/MedHorizon/tree/main) contains the benchmark metadata and available release assets. Follow the original providers for full video access and their applicable terms. Source pointers below come from the workspace's data-provenance metadata.

| Source / folder | Videos | Questions | Original source |
| --- | ---: | ---: | --- |
| AutoLaparo (`autolaparo/`) | 20 | 44 | [AutoLaparo](https://autolaparo.github.io/) |
| Galar (`galar/`) | 44 | 60 | [Galar](https://plus.figshare.com/articles/dataset/Galar_-_a_large_multi-label_video_capsule_endoscopy_dataset/25304616) |
| GraSP (`grasp/`) | 13 | 112 | [GraSP](https://github.com/BCV-Uniandes/GraSP) |
| MultiBypass (`multibypass/`) | 125 | 403 | [MultiBypass](https://github.com/CAMMA-public/MultiBypass140) |
| PitVQA (`pitvqa/`) | 10 | 13 | [PitVQA](https://doi.org/10.1007/978-3-031-72089-5_46) |
| REAL-Colon (`real_colon/`) | 39 | 251 | [REAL-Colon](https://plus.figshare.com/articles/media/REAL-colon_dataset/22202866) |
| TMVP (`tmvp/`) | 59 | 340 | [TMVP](https://github.com/xmed-lab/SurgFormer) |
| US-Study (`us_study/`) | 30 | 30 | [US-Study](https://data.mendeley.com/datasets/s27zfxgbpj/1) |

Store files under a common video root using the exact `video_path` in the annotation. The benchmark export does not download all videos automatically. This avoids substituting a different version or silently changing the procedure's time base.

```text
/path/to/videos/
  autolaparo/15.mp4
  galar/15.mp4
  grasp/CASE014.mp4
  multibypass/SBP12.mp4
  pitvqa/video_09.mp4
  real_colon/003-007.mp4
  tmvp/087.mp4
  us_study/01-lus.mp4
```

`medhorizon prepare` checks that referenced files exist. It does not decode them or claim that their media metadata match the historical export. Confirm decodability and effective duration in your inference pipeline; different source encodings can have different FPS or time bases.

## Annotation schema

Each line of `data/medhorizon_test.jsonl` is a video record with:

- `key`, `dataset`, `organ`, `scene_type`, `duration_tier`: source identity and context.
- `video_path`: relative video path; `num_frames`, `fps`, `duration_seconds`: inherited metadata.
- `qa`: question objects containing the stable `uid`, final `question`, four labeled `options`, and `answer` (A–D).
- `task_id`, `task_name`, `task_class`, `category`, and `natural_rewrite_v1_kind`: original task metadata inside each QA object.
- `uid_original` and historical question/option variants: provenance inside the QA object.
- `split`: `test`. The ultrasound records also retain the public source's study metadata.

Use `uid` for matching predictions. Do not use `uid_original`, which refers to earlier source pools. Generate inference inputs with the provided prepare command instead of submitting the raw annotation object to a model.

## Task taxonomy

| Task | Description | Capability | Questions |
| --- | --- | --- | ---: |
| PR | Phase / examination recognition | Fine-grained Understanding | 517 |
| SD | Surgical step discrimination | Fine-grained Understanding | 112 |
| RL | Region localization | Fine-grained Understanding | 60 |
| BPQ | Bowel preparation quality | Fine-grained Understanding | 39 |
| LLS | Largest lesion size | Fine-grained Understanding | 39 |
| Site | Lesion site binding | Fine-grained Understanding | 47 |
| Hist | Lesion histology binding | Fine-grained Understanding | 47 |
| Size | Lesion size binding | Fine-grained Understanding | 47 |
| IR | Instrument onset reasoning | Semantic Reasoning | 235 |
| WR | Workload / instrument coverage ranking | Semantic Reasoning | 26 |
| RSR | Rank-then-step retrieval | Semantic Reasoning | 26 |
| CPR | Counting and proportion reasoning | Semantic Reasoning | 26 |
| LA | Lesion site aggregation | Semantic Reasoning | 32 |

The 30 ultrasound questions are included in PR. The release's explicit task-kind metadata gives 908 fine-grained understanding questions and 345 semantic reasoning questions. The older capability-summary table lists 940/313; the scorer uses the actual per-task membership above. LA is called LD in some historical evidence exports and is normalized to LA here.

## Evidence metadata

`data/evidence_windows.jsonl` contains one row for every question. It uses the same `uid` and relative video path as the annotation, together with `leaf_task_id`, the normalized `task`, source FPS/frame count, `gt_frames`, `gt_frame_count`, `support_mode`, `support_detail`, and a temporal evidence category.

Each `gt_frames` entry has inclusive `start_frame`/`end_frame` indices and second-based `start`/`end` timestamps. Coordinates refer to the source encoding used by the evidence exporter. Re-encoding or resampling a video requires mapping its coordinates rather than blindly reusing frame indices.

The source export is heterogeneous: exact phase/step/instrument matches coexist with proxy lesion windows and global supports. It includes 69 `all_frames_global` questions. REAL-Colon lesion support includes 141 `benchmark_proxy` records, 32 proxy site unions, and 29 proxy largest-lesion unions; 10 questions have no resolved local support (`unresolved_real_colon`). Preserve these flags in evidence-quality analyses. These windows are not all independent manual frame annotations.

Evidence was generated before the final natural-language rewrite. During this release, every evidence UID, gold answer, source video identity, and leaf-task assignment was matched to the final annotation. Duplicate old question text and gold answer text were omitted from the evidence export. The original mode labels and support details were retained.

Use evidence only for audit or explicitly labeled oracle diagnostics. Standard full-video model input contains the final question/options and video, not these windows.

## Duration metadata

The manuscript and dataset card report **759 decoded hours**. Summing the frozen annotation's `duration_seconds` fields gives **977.576943 hours**. The evidence metadata also use the inherited duration fields. These totals have not been reconciled by a fresh decoding pass during publication preparation.

The annotation file is preserved byte for byte to keep question IDs, labels, and published checksums stable. The manifest distinguishes `paper_reported_hours` from `annotation_duration_hours`. Treat these as different reported quantities and validate media time bases when reproducing duration-sensitive analyses.

## Integrity and terms

Run `python -m medhorizon validate --manifest data/manifest.json --evidence data/evidence_windows.jsonl` to verify the frozen annotations, task counts, evidence alignment, and checksums. See [data terms](../data/README.md) for attribution and the dataset card's CC BY-NC 4.0 designation.
