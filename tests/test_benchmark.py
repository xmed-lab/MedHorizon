import copy
import json
import tempfile
import unittest
from pathlib import Path

from medhorizon.benchmark import (TASKS, dataset_summary, extract_answer, inference_rows,
                                  load_benchmark, score, sha256, validate_evidence, write_jsonl)
from medhorizon.infer_swift import check_requests


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.items = load_benchmark(ROOT / "data/medhorizon_test.jsonl")

    def test_release_manifest_and_taxonomy(self):
        manifest = json.loads((ROOT / "data/manifest.json").read_text())
        summary = dataset_summary(self.records, self.items)
        self.assertEqual(summary["questions"], 1253)
        self.assertEqual(summary["videos"], 340)
        self.assertEqual(summary["questions_by_task"], {k: v[2] for k, v in TASKS.items()})
        self.assertEqual(summary["questions_by_capability"],
                         {"Fine-grained Understanding": 908, "Semantic Reasoning": 345})
        self.assertEqual(sha256(ROOT / "data/medhorizon_test.jsonl"), manifest["annotations_sha256"])
        self.assertEqual(sha256(ROOT / "data/evidence_windows.jsonl"), manifest["evidence_sha256"])

    def test_evidence_alignment_and_unresolved_cases(self):
        summary = validate_evidence(ROOT / "data/evidence_windows.jsonl", self.items)
        self.assertEqual(summary["questions"], 1253)
        self.assertEqual(summary["without_local_windows"], 10)
        self.assertEqual(summary["support_modes"]["all_frames_global"], 69)

    def test_uid_alignment_is_independent_of_order(self):
        predictions = [{"uid": item["uid"], "prediction": item["answer"]} for item in reversed(self.items)]
        result, _ = score(self.items, predictions)
        self.assertEqual(result["overall"], {"correct": 1253, "total": 1253, "accuracy": 100})

    def test_wrong_predictions_and_missing_rows_keep_denominator(self):
        predictions = [{"uid": item["uid"], "prediction": "ABCD"[("ABCD".index(item["answer"]) + 1) % 4]}
                       for item in self.items]
        self.assertEqual(score(self.items, predictions)[0]["overall"]["accuracy"], 0)
        with self.assertRaisesRegex(ValueError, "Missing"):
            score(self.items, predictions[:-1])
        partial, _ = score(self.items, [], allow_missing=True)
        self.assertEqual(partial["overall"]["total"], 1253)
        self.assertEqual(partial["missing"], 1253)

    def test_duplicate_unknown_and_conflicting_ids_fail(self):
        for rows in ([{"uid": "0", "prediction": "A"}] * 2,
                     [{"uid": "nonexistent", "prediction": "A"}],
                     [{"uid": "0", "_meta": {"uid": "1"}, "prediction": "A"}]):
            with self.assertRaises(ValueError):
                score(self.items, rows, allow_missing=True)

    def test_swift_metadata_ids_and_explicit_response_field(self):
        item = self.items[0]
        rows = [{"_meta": {"uid": int(item["uid"])}, "response": item["answer"]}]
        self.assertEqual(score(self.items[:1], rows, field="response")[0]["overall"]["accuracy"], 100)
        with self.assertRaisesRegex(ValueError, "lacks field"):
            score(self.items[:1], rows)

    def test_strict_parser_does_not_guess_from_prose(self):
        for value in ("Because the video...", "Answer: B", "A or B", "", None, ["A"]):
            self.assertIsNone(extract_answer(value))
        self.assertEqual(extract_answer(" b\n"), "B")
        self.assertEqual(extract_answer("Because the video...", "legacy"), "B")
        result, _ = score(self.items[:1], [{"uid": "0", "prediction": "Answer: A"}])
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(result["overall"]["correct"], 0)

    def test_inference_input_omits_gold_history_and_evidence(self):
        for format in ("swift", "flat"):
            rows = list(inference_rows(self.items, text_only=True, format=format))
            self.assertEqual(len(rows), 1253)
            for row in rows:
                self.assertTrue(set(row).isdisjoint({"answer", "response", "solution", "gt_frames", "question_original"}))
                self.assertNotIn("videos", row)
                self.assertNotIn("video", row)
                if format == "swift":
                    self.assertEqual([m["role"] for m in row["messages"]], ["system", "user"])
                    self.assertNotIn("<video>", row["messages"][1]["content"])
                    self.assertIn("based on the question", row["messages"][0]["content"])
            if format == "swift":
                check_requests(rows)

    def test_video_root_and_missing_video(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Missing video"):
                list(inference_rows(self.items[:1], directory))
            video = Path(directory) / self.items[0]["video_path"]
            video.parent.mkdir(parents=True)
            video.touch()
            row = next(inference_rows(self.items[:1], directory))
            self.assertEqual(row["videos"], [str(video)])
            self.assertTrue(row["messages"][1]["content"].startswith("<video>"))

    def test_schema_rejects_corrupt_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            for change in ("duplicate_uid", "absolute_path", "traversal", "unknown_kind", "duplicate_option"):
                record = copy.deepcopy(self.records[0])
                if change == "duplicate_uid":
                    record["qa"].append(copy.deepcopy(record["qa"][0]))
                elif change == "absolute_path":
                    record["video_path"] = "/tmp/video.mp4"
                elif change == "traversal":
                    record["video_path"] = "../video.mp4"
                elif change == "unknown_kind":
                    record["qa"][0]["natural_rewrite_v1_kind"] = "unknown"
                else:
                    record["qa"][0]["options"][1] = "B." + record["qa"][0]["options"][0][2:]
                write_jsonl(path, [record])
                with self.assertRaises(ValueError, msg=change):
                    load_benchmark(path)


if __name__ == "__main__":
    unittest.main()
