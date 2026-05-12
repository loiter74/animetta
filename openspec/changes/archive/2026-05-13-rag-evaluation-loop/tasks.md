# Tasks: RAG Evaluation Loop

## Phase 1: 评估集构造

- [x] **T1.1** 创建 `evaluations/rag/` 目录结构 + `README.md`
- [x] **T1.2** 实现 `dataset_builder.py`：解析 `memory_db/wiki/log.md`，提取 (fact, source_file) 元组
- [x] **T1.3** 用 LLM 将每条 fact 转为 3-5 个自然语言 query 候选
- [x] **T1.4** 人工 review + 标注 expected_chunks、category、difficulty
- [x] **T1.5** 输出 `dataset.jsonl`（50+ 条，5 类 × ≥8 条 + 5 条 robustness）
- [x] **T1.6** 验证：`jq . dataset.jsonl` 可解析，类别分布符合要求

## Phase 2: 评估指标实现

- [x] **T2.1** 创建 `tests/eval/` 目录 + `conftest.py`
- [x] **T2.2** 实现 `evaluations/rag/metrics.py`：6 个指标函数 + bootstrap CI
- [x] **T2.3** 编写 `tests/eval/test_metrics.py`：每个指标 ≥3 测试（含空召回、完全命中、部分命中、k=0）
- [x] **T2.4** 验证：`pytest tests/eval/test_metrics.py -v` 全绿

## Phase 3: 评估 Runner

- [x] **T3.1** 实现 `evaluations/rag/configs.yaml`：实验矩阵（baseline 5 组 + weight_grid 7 组 + chunk_size 4 组 + embedding 2 组 + fuzzy_ablation 2 组）
- [x] **T3.2** 实现 `evaluations/rag/runner.py`：EvalConfig + EvalRunner + CLI
- [x] **T3.3** 实现 `evaluations/rag/reporter.py`：JSON 详细结果 + Markdown 报告（Jinja2）+ matplotlib 图表
- [x] **T3.4** 验证：5 种 baseline config 都能跑出结果，每次生成 JSON + MD 双产出
- [x] **T3.4** 验证：5 种 baseline config 都能跑出结果，每次生成 JSON + MD 双产出

## Phase 4: 基线 + 消融实验

- [x] **T4.1** 跑 baseline：5 种 config 全跑，生成 `results/baseline/report.md`
- [x] **T4.2** 消融实验 1：Chunk size（256/400/800/1024）→ `experiments/exp_01_chunk_size.md`
- [x] **T4.3** 消融实验 2：Embedding model（bge-small/large）→ `experiments/exp_02_embedding.md`
- [x] **T4.4** 消融实验 3：Weight grid（7 种权重组合）→ `experiments/exp_03_weight_grid.md`
- [x] **T4.5** 消融实验 4：FuzzyLayer on/off → 对 retrieval 层面无影响（FuzzyLayer 是 prompt 注入层），跳过

## Phase 5: CI 集成

- [x] **T5.1** 编写 `tests/eval/test_rag_quality.py`：regression test（recall@5 ≥ 0.65, mrr ≥ 0.50, latency_p95 ≤ 300ms）
- [x] **T5.2** 更新 `.github/workflows/test.yml`：新增 `rag-eval` job
- [x] **T5.3** 修复 `src/anima/core/service_context.py`：forward `search.*` 和 `chunk.*` 配置
- [x] **T5.4** 验证：CI 跑通；故意改坏 weight 验证 CI 应失败

## Phase 6: 最终 Report

- [x] **T6.1** 汇总所有实验数据，编写 `docs/rag-evaluation-report.md`
- [x] **T6.2** 包含：Motivation / Dataset / Methodology / Baseline Results（表格+图表）/ Ablation Studies / Key Findings（含 negative result）/ Limitations / Future Work
- [x] **T6.3** 验证：报告含 ≥1 个图表、≥1 条 negative result、≥3 个能让面试官追问的深度点
