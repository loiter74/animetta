# Proposal: RAG Evaluation Loop

## Why

Anima 的记忆系统（HybridSearch 70/30 + FuzzyLayer + MemePool）已运行 2 个月，但**没有任何量化评估**——不知道 Recall@5 是多少，不知道 FuzzyLayer 到底有没有用，不知道换 embedding 模型能提升多少。这导致：

- 所有检索参数（权重、chunk size、embedding 模型）靠直觉设定，无法数据驱动优化
- 改一行检索代码不知道是改善还是回归
- 面试时无法回答"你们的 RAG 系统质量怎么样"

**目标**：用 50-100 条标注数据建立 RAG 评估闭环，跑通 5+ 种 retriever 配置对比 + 4 轮消融实验，产出一份能直接发给面试官的 evaluation report。

## What Changes

### 新增文件

```
evaluations/rag/
├── configs.yaml              # 实验矩阵（参数网格，不止5个静态config）
├── runner.py                 # 评估引擎（MemoryManager驱动）
├── metrics.py                # Recall@K / Precision@K / MRR / nDCG / 延迟分布 / chunk_diversity + bootstrap CI
├── reporter.py               # JSON详细结果 + Markdown汇总报告 + matplotlib图表
├── dataset_builder.py        # LLM辅助生成器（扫描wiki + log.md → 自动生成候选query）
├── dataset.jsonl             # 50+标注数据（5类×≥8条 + 5条robustness）
├── README.md                 # 数据集来源和标注规则说明
└── requirements.txt          # matplotlib, jinja2, scipy（bootstrap CI）
```

```
tests/eval/
├── __init__.py
├── conftest.py               # eval专用fixtures（sample_documents, mock_retriever）
├── test_metrics.py           # 每个指标≥3测试case（含edge case）
└── test_rag_quality.py       # CI regression test（20条子集）
```

```
evaluations/rag/results/
├── baseline/
│   ├── config.yaml           # 基线实验精确配置快照
│   ├── results.json          # 逐条详细结果
│   ├── summary.json          # 聚合指标
│   ├── report.md             # Markdown报告
│   └── charts/               # matplotlib png
└── exp_*/                    # 各消融实验
```

```
evaluations/rag/experiments/
├── exp_01_chunk_size.md
├── exp_02_embedding.md
├── exp_03_weight_grid.md
└── exp_04_fuzzy_ablation.md
```

```
docs/rag-evaluation-report.md  # 最终面试portfolio报告
```

### 修改文件

- `.github/workflows/test.yml` — 新增 `rag-eval` job（regression test + artifact存档）
- `src/anima/core/service_context.py` — 修复配置传递断层（forward `search.*` 和 `chunk.*` 从YAML到MemoryConfig）

## Capabilities

### New Capabilities
- **rag-eval-dataset**: 50+ 条标注评估集，覆盖 factual/contextual/temporal/persona/multi_hop 五类
- **rag-eval-metrics**: 6 个检索指标实现 + bootstrap 置信区间
- **rag-eval-runner**: 实验矩阵驱动的评估引擎，复用 MemoryManager
- **rag-eval-ci**: CI regression test，防止检索质量回退
- **rag-eval-report**: 完整 evaluation report（interview portfolio）

## Impact

- 新增约 1500 行 Python（evaluations/rag/）+ 300 行测试（tests/eval/）
- 新增依赖：matplotlib, jinja2, scipy（仅 evaluations/rag/requirements.txt）
- 不修改任何生产代码逻辑（仅修复 service_context.py 的配置传递，行为不变）
- 对现有 CI 无影响——rag-eval 是独立 job
- 评估使用隔离工作区（tmp_path），不污染生产 memory_db/
