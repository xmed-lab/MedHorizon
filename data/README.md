# MedHorizon data

`medhorizon_test.jsonl` contains 340 video records and 1,253 QA items. Its bytes match the [published Hugging Face annotation](https://huggingface.co/datasets/DBD123/MedHorizon/blob/main/medhorizon_test.jsonl). `evidence_windows.jsonl` is a portable export of the workspace's strict evidence metadata, joined by question UID. See [data documentation](../docs/data.md).

The [dataset card](https://huggingface.co/datasets/DBD123/MedHorizon) specifies the [Creative Commons Attribution-NonCommercial 4.0 International license](https://creativecommons.org/licenses/by-nc/4.0/) for the derived benchmark data. Attribute MedHorizon and the original datasets. Raw source videos retain their own terms; this notice does not grant new rights to those videos or apply a blanket license to third-party software.

The evidence export normalizes video paths and removes duplicate question/answer text and original machine paths. It preserves the evidence coordinates, task IDs, support modes, and support details. The complete annotation file is unchanged.
