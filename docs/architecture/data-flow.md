# 数据流设计

Anima 的五层数据流架构。

---

## 架构概览

```
用户输入 (文本/音频)
    ↓
Layer 1: InputPipeline
    ├─ ASRStep - 音频转文本
    ├─ TextCleanStep - 文本清洗
    └─ EmotionExtractionStep - 情感提取
    ↓
Layer 2: Agent (LLM 对话)
    └─ chat_stream() 返回 AsyncIterator[str]
    ↓
Layer 3: OutputPipeline
    ├─ 累积 chunks 为句子
    ├─ 发射 sentence 事件
    └─ 触发 TTS 合成
    ↓
Layer 4: EventBus
    └─ 按优先级通知订阅者
    ↓
Layer 5: Handlers
    ├─ TextHandler - 发送文本
    ├─ AudioHandler - 发送音频
    └─ Live2DHandler - 发送表情
    ↓
前端实时渲染
```

---

## 数据结构

### PipelineContext
```python
raw_input: Union[str, np.ndarray]  # 原始输入
text: str                           # 处理后的文本
metadata: Dict[str, Any]           # 元数据（情感等）
```

### OutputEvent
```python
type: str          # 事件类型 (sentence, audio, expression, etc.)
data: Any          # 事件数据
seq: int           # 序号
metadata: Dict     # 元数据
```

---

## 性能指标

| 指标 | 数值 |
|------|------|
| 端到端延迟 | < 500ms |
| 首字延迟 | < 200ms |
| TTS 延迟 | < 300ms |
| 音量包络采样 | 50Hz |
| 嘴部参数更新 | 30fps |

---

## 相关文档

- [设计模式](./patterns.md) - Pipeline 和 EventBus 的设计模式
- [事件系统](./event-system.md) - EventBus 详细实现
