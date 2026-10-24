# Reported benchmark results

[`paper_results.csv`](paper_results.csv) transcribes 25 rows from the benchmark manuscript table in the source workspace (`paper/NIPS_Paper_0503/tables/main_results.tex`). Columns contain model family, parameter size, visual input protocol, overall accuracy, and the 13 task accuracies. Values are percentages rounded to one decimal place as in the table.

These are reported historical results, not new evaluations performed during repository preparation. See the [paper](https://arxiv.org/abs/2605.06537) for interpretation and [evaluation notes](../docs/evaluation.md) for the scoring contract of the released tools. Model families use different frame/token budgets; `1 FPS` includes model-specific caps and is not a fixed common budget.

The table's denominators are 1,253 overall, then PR 517, SD 112, RL 60, BPQ 39, LLS 39, Site 47, Hist 47, Size 47, IR 235, WR 26, RSR 26, CPR 26, and LA 32.
