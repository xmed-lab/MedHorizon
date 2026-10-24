# Construction and release provenance

MedHorizon grew from the working name MLV-Bench / MedVidBench. The published release combines the curated 1,223-question medical-procedure set with 30 ultrasound study questions. Earlier workspace files include a 1,304-question candidate set and other intermediate counts; they are not the release used here.

The construction workflow normalizes source annotations and video identifiers, builds questions tied to source evidence, constructs plausible distractors, filters invalid/ambiguous candidates, rewrites questions into natural language, and performs the human review described in the [paper](https://arxiv.org/abs/2605.06537).

The final language-rewrite audit records 1,253 retained questions, unchanged IDs and answer letters, and 132 cleaned option texts. The public annotation includes provenance fields such as `uid_original`, `question_original`, `question_before_natural_rewrite`, and `natural_rewrite_v1_kind`. These fields are useful for audit and are excluded from generated model input.

## Published artifacts

| Release artifact | Workspace source | Processing |
| --- | --- | --- |
| `data/medhorizon_test.jsonl` | `hf_release_medhorizon/medhorizon_test.jsonl` | Byte-for-byte copy; checked against the public Hugging Face file |
| `data/evidence_windows.jsonl` | `analysis/analysis_experiment/sparse/question_evidence_windows_plus_us.json` | Joined on UID; verified answers, source identities, and all task assignments; exported relative paths and evidence/provenance fields |
| `results/paper_results.csv` | `paper/NIPS_Paper_0503/tables/main_results.tex` | Extracted the reported 25 rows and 13 task columns without changing values |
| `docs/site/` | `project_page/` | Retained the benchmark figures and layout; updated paper/citation links and release descriptions |
| Data preparation and scoring | `hard_eval/`, `gpt4o_trans/`, `key_frame_eval/` | Consolidated into a dependency-free interface with UID matching and explicit parser modes |

`data/manifest.json` records annotation/evidence checksums and the evidence source checksum. Historical experiment numbers in `results/` are archived reports and are not validation results from this cleanup.

## Workspace organization

The source workspace also contains initial dataset processors (`MLV-Bench/`), multi-hop construction (`add_mutli_hop/`), question rewriting (`gpt4o_trans/`), ultrasound integration (`add_US_0325/`), raw/model-specific evaluation (`hard_eval/`, `key_frame_eval/`), diagnostic experiments (`analysis/`), and several paper revisions (`paper/`). Those historical paths explain the release's provenance; the current public entry points are documented in this repository.

Raw videos, model weights, machine environments, logs, caches, course assignments, and duplicate manuscript archives remain workspace assets. The repository focuses on the frozen benchmark release and its usable evaluation interface.
