# 口语化记忆 Worker 使用指南

## 概述

`OralMemoryWorker` 是一个独立的异步后台服务，使用 LLM 将原始对话转换为口语化记忆版本。

## 架构

```
MemorySystem
    ├── LongTermMemory
    │     └── MemoryManager
    │           ├── _index_file() (同步)
    │           │     ├── 写入 Chroma (使用规则转换的 oral_version)
    │           │     └── 提交口语化任务到 OralMemoryWorker
    │           └── _create_oral_callback()
    │
    └── OralMemoryWorker (异步)
          ├── 队列接收任务
          ├── 批量处理
          ├── LLM 调用
          └── 回调更新 Chroma metadata
```

## 工作流程

1. **快速写入**: `MemoryManager._index_file` 使用规则转换快速生成 `oral_version`
2. **异步优化**: 同时提交任务到 `OralMemoryWorker`
3. **LLM 处理**: Worker 在后台使用 LLM 生成更自然的口语化版本
4. **自动更新**: 完成后通过回调自动更新 Chroma metadata

## 配置

```python
# 在创建 MemorySystem 时传入 LLM 客户端
memory_system = MemorySystem({
    "workspace_dir": "~/.anima/workspace",
    "llm_client": llm_instance,  # LLM 实例 (需实现 chat 方法)
    "oral_queue_size": 1000,      # 队列大小 (默认 1000)
    "oral_max_retries": 2,        # 失败重试次数 (默认 2)
    "oral_batch_size": 5,         # 批量处理大小 (默认 5)
})
```

## LLM 接口要求

LLM 客户端需实现 `chat` 方法：

```python
class MyLLM:
    async def chat(self, user_input: str, system_prompt: str = None) -> str:
        # 处理输入并返回响应
        return response
```

## 示例代码

```python
import asyncio
from anima.memory.system import MemorySystem
from anima.services.intelligence.llm.glm_llm import GLMLLM
from anima.config import GLMLLMConfig

async def main():
    # 1. 创建 LLM 实例
    llm_config = GLMLLMConfig(
        api_key="your-api-key",
        model="glm-4-flash",
        temperature=0.7,
    )
    llm = GLMLLM.from_config(llm_config)

    # 2. 创建 MemorySystem，传入 LLM
    memory_system = MemorySystem({
        "workspace_dir": "~/.anima/workspace",
        "llm_client": llm,
    })

    # 3. 启动系统（会自动启动 Worker）
    await memory_system.start()

    # 4. 写入记忆（会自动触发口语化处理）
    memory_system.write_daily_log("**User**: 我想学 Python")

    # 5. 等待处理完成（可选）
    await asyncio.sleep(2)

    # 6. 搜索记忆（会返回口语化版本）
    results = memory_system.search("Python")
    for result in results:
        print(result.text)  # 输出: "我记得你说过你想学 Python"

    # 7. 关闭系统
    await memory_system.stop()

asyncio.run(main())
```

## 特性

- **异步处理**: 不阻塞主流程
- **批量处理**: 提高吞吐量
- **自动重试**: 失败自动重试
- **结果缓存**: 相同内容复用结果
- **优雅降级**: LLM 不可用时使用规则转换

## 监控

```python
# 获取 Worker 统计信息
worker = memory_system.get_oral_worker()
if worker:
    print(f"队列大小: {worker.get_queue_size()}")
    print(f"追踪任务: {worker.get_task_count()}")
    print(f"统计: {worker.stats}")
    # {'total_received': 100, 'total_completed': 95, ...}
```

## 注意事项

1. **成本**: 每条记忆多一次 LLM 调用，注意 API 费用
2. **延迟**: LLM 处理需要时间，首次检索可能仍是规则转换结果
3. **兼容性**: 旧数据没有 `oral_version` 时会自动 fallback 到原始文本
4. **关闭**: 务必调用 `await memory_system.stop()` 确保 Worker 优雅退出

## 故障排查

| 问题 | 原因 | 解决方案 |
|-----|------|----------|
| 没有口语化效果 | LLM 未配置 | 检查 `llm_client` 是否传入 |
| 口语化不更新 | Worker 未启动 | 确保调用了 `await memory_system.start()` |
| 队列积压 | LLM 处理太慢 | 增加 `batch_size` 或使用更快的模型 |
| 总是规则转换 | LLM 调用失败 | 检查 API key、网络连接 |
