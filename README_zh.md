# MedHorizon

面向真实场景下长时医疗视频理解的评测基准。

[论文](https://arxiv.org/abs/2605.06537) · [数据集](https://huggingface.co/datasets/DBD123/MedHorizon) · [English README](README.md)

正式测试集包含 **340 段完整流程视频、1,253 道四选一问题、8 个数据来源、13 类任务**，覆盖手术、内镜、结肠镜和超声。基准关注稀疏证据检索、细粒度理解和跨时间片段的临床推理。

## 使用

在仓库根目录使用 Python 3.10+，无需额外依赖即可检查数据和计算分数：

```bash
python -m medhorizon validate --manifest data/manifest.json --evidence data/evidence_windows.jsonl
python -m medhorizon prepare --video-root /path/to/videos --output outputs/input.jsonl
python -m medhorizon score --predictions outputs/predictions.jsonl --output outputs/metrics.json
```

预测文件每行格式为 `{"uid": "0", "prediction": "A"}`。评分按题目 ID 对齐，报告总体、子任务、来源数据集和能力维度的准确率。默认要求完整的 1,253 条预测；重复或未知 ID 会报错。

模型推理示例及依赖见 [英文说明](README.md#run-a-model)。视频从 [Hugging Face 和原始数据来源](docs/data.md#video-access) 获取，按标注中的相对路径存放。`prepare` 生成的模型输入不包含正确答案、证据窗口或历史改写文本。

## 数据说明

- 标注文件与已发布的 Hugging Face 版本逐字节一致。
- 证据文件覆盖全部题目，保留代理窗口、全视频支持和未解析窗口的原始标记。其中 10 题没有可解析的局部证据窗口。
- 论文报告的 759 小时与标注时长字段累计约 977.58 小时不同；仓库保留原始标注并记录这项差异。
- `results/` 为论文中已报告的 25 个模型/方法结果，不代表此次重新运行了所有模型。

数据字段、来源与限制详见 [数据文档](docs/data.md)，评分规则见 [评测文档](docs/evaluation.md)。
