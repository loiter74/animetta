# Design: RAG Evaluation Loop

## Architecture

```
                         ┌──────────────────────────────────────┐
                         │        evaluations/rag/              │
                         │                                      │
                         │  configs.yaml ───► EvalRunner        │
                         │  dataset.jsonl ──► MetricsEngine     │
                         │  log.md ────────► ReportGenerator    │
                         │                                      │
                         │  Output: JSON + Markdown + PNG       │
                         └────────────────┬─────────────────────┘
                                          │
                     ┌────────────────────┼────────────────────┐
                     │                    │                    │
                     ▼                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ MemoryManager│    │ MemoryManager│    │ MemoryManager│
            │ vector_only  │    │ hybrid_70_30 │    │ bm25_only   │
            │              │    │              │    │              │
            │ Chroma ✓     │    │ Chroma ✓     │    │ Chroma ✗    │
            │ SQLite ✗     │    │ SQLite ✓     │    │ SQLite ✓    │
            └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
                   │                   │                    │
                   └─────────┬─────────┴────────────────────┘
                             │
                     ┌───────▼──────────┐
                     │  Isolated Temp   │
                     │  Workspace       │
                     │  ├── raw/        │  ← eval corpus (.md)
                     │  ├── wiki/       │  ← eval corpus (.md)
                     │  ├── chroma_db/  │  ← auto-built index
                     │  └── memory.sqlite│  ← auto-built index
                     └──────────────────┘
```

## Component Design

### 1. Metrics Engine (`metrics.py`)

纯函数，零依赖（除 scipy 用于 bootstrap CI）。

```python
def recall_at_k(retrieved: list[ChunkId], expected: list[ChunkId], k: int) -> float
def precision_at_k(retrieved: list[ChunkId], expected: list[ChunkId], k: int) -> float
def mrr(retrieved: list[ChunkId], expected: list[ChunkId]) -> float
def ndcg_at_k(retrieved: list[ChunkId], expected: list[ChunkId], k: int) -> float
def latency_percentiles(timings_ms: list[float]) -> dict[str, float]
def chunk_diversity(retrieved_chunks: list[dict]) -> float  # distinct_docs / total

# 工程深度：bootstrap 置信区间
def bootstrap_ci(metric_fn, samples, n_bootstrap=1000, ci=0.95) -> tuple[float, float, float]
```

**ChunkId 格式**：`(path: str, start_line: int, end_line: int)` —— 直接对应 `SearchResult` 的三元组定位。

**Edge cases 覆盖**：空召回（retrieved=[]）、完全命中、部分命中、expected 为空、k=0。

### 2. Eval Runner (`runner.py`)

核心原则：**绕过 ServiceContext，直接构造 MemoryConfig → MemoryManager**。不依赖 YAML 配置传递。

```python
@dataclass
class EvalConfig:
    """单个实验的完整配置快照"""
    name: str
    vector_weight: float
    keyword_weight: float
    embedding_model: str
    target_tokens: int
    overlap_tokens: int
    fuzzy_enabled: bool
    max_results: int

class EvalRunner:
    def __init__(self, workspace_dir: Path, config: EvalConfig):
        self.memory_config = MemoryConfig(
            workspace_dir=str(workspace_dir),
            search=SearchConfig(vector_weight=config.vector_weight, ...),
            chunk=ChunkConfig(target_tokens=config.target_tokens, ...),
            embedding=EmbeddingConfig(model_name=config.embedding_model),
        )
    
    def run(self, dataset: list[QueryItem], k: int = 5) -> EvalResult:
        manager = MemoryManager(config=self.memory_config)
        manager.sync()  # 索引测试语料
        metrics = []
        latencies = []
        for item in dataset:
            t0 = time.perf_counter()
            results = manager.search(item.query, max_results=k)
            latencies.append((time.perf_counter() - t0) * 1000)
            metrics.append(self._compute_item_metrics(results, item, k))
        manager.close()
        return self._aggregate(metrics, latencies)
```

**关键设计决策**：
- 每个实验配置创建一个新的 MemoryManager 实例 → 确保隔离
- `manager.sync()` 扫描 workspace 下的 raw/ 和 wiki/ 目录 → 自动建索引
- 不保留 Chroma 持久化（每次重建） → 保证实验可复现

### 3. 数据集构造 (`dataset_builder.py`)

**策略**：log.md 辅助 + LLM 生成 + 人工标注。

```
Step 1: 解析 memory_db/wiki/log.md → 提取 (fact, source_file) 元组
Step 2: LLM 将每个 fact 转为自然语言 query（per file 3-5 个候选）
Step 3: 自动填充 expected_chunks（已知 source_file）
Step 4: 人工 review：修正 expected_chunks、标注 category/difficulty
Step 5: 输出 dataset.jsonl
```

**类别分布**（50+ 条）：

| Category | 最少条数 | 示例 |
|----------|---------|------|
| factual | 10 | "我的猫叫什么名字？" |
| contextual | 10 | "刚才说的那个在团队里画内图的专家，他怎么看AI？" |
| temporal | 10 | "从3月到现在，我对AI说话的模式发生了什么变化？" |
| persona | 10 | "Aura 的金句是什么？她讨厌什么样的回答？" |
| multi_hop | 10 | "小明讨厌加班，他一般是怎么被问到这件事的？" |
| robustness | 5 | 故意包含拼写错误、口语化表达 |

### 4. 报告生成 (`reporter.py`)

双产出格式：
- **JSON** (`results.json`)：逐条 query 的 retrieved / expected / metrics
- **Markdown** (`report.md`)：Jinja2 模板驱动，含总指标表 + per-category breakdown + per-difficulty breakdown
- **Charts** (`charts/`)：matplotlib 生成 Recall@K 柱状图、延迟分布直方图、配置对比雷达图

### 5. FuzzyLayer 消融——特殊处理

FuzzyLayer 不是 retriever，它通过 `MemoryMiddleware.before_llm_call()` 注入 prompt。评估方式：

```
非Fuzzy实验：query → manager.search() → 比较 chunk IDs
Fuzzy实验：  query + session_context → FuzzyLayer.build_fuzzy_context()
               → 检查注入文本是否包含 expected_chunks 对应的内容
               → 指标：fact_coverage（注入文本中expected事实的覆盖率）
```

不需要 LLM-as-judge——直接检查 `expected_chunks` 中的关键文本是否出现在 FuzzyLayer 输出中。

## Data Flow

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ dataset  │───▶│ EvalRunner   │───▶│ MetricsEngine│───▶│ ReportGen    │
│ .jsonl   │    │ .run()       │    │ .compute()   │    │ .generate()  │
└──────────┘    └──────┬───────┘    └──────────────┘    └──────┬───────┘
                       │                                       │
                       ▼                                       ▼
              ┌────────────────┐                     ┌──────────────────┐
              │ MemoryManager  │                     │ results/{exp_id}/│
              │ .search()      │                     │ ├── results.json │
              │ .sync()        │                     │ ├── summary.json │
              └────────────────┘                     │ ├── report.md    │
                                                     │ └── charts/     │
                                                     └──────────────────┘
```

## Key Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| Retriever 接入方式 | 直接构造 MemoryConfig → MemoryManager | 绕过 ServiceContext 的配置断层 |
| 工作区策略 | tmp_path 默认，--keep-workspace flag | 隔离 + 可调试 |
| 嵌入模型 | 直接下载真实模型（bge-small-zh-v1.5） | 质量优先，不省资源 |
| 数据集范围 | 4月8日起 + 5条遗留数据 | 保证标注质量 + robustness test |
| FuzzyLayer 评估 | 检查注入文本事实覆盖率 | 符合"只评 retrieval"边界，无需 LLM judge |
| CI 策略 | 完整 50 条评估 + artifact 存档 | 不省时间，追踪趋势 |
| 消融实验数量 | 4 轮 | 比要求多 1 轮，体现深度 |

## CI Integration

```yaml
rag-eval:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install -r requirements.txt -r evaluations/rag/requirements.txt
    - name: Run baseline evaluation
      run: python evaluations/rag/runner.py --config hybrid_with_fuzzy --dataset evaluations/rag/dataset.jsonl --k 5 --output evaluations/rag/results/ci/
    - name: Regression check
      run: PYTHONPATH=src python -m pytest tests/eval/test_rag_quality.py -v
    - name: Archive results
      uses: actions/upload-artifact@v4
      with:
        name: rag-eval-${{ github.run_id }}
        path: evaluations/rag/results/ci/
```
