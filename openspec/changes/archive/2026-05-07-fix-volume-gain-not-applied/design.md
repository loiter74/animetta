## Context

`output_node.py` 中 `_compute_volumes` 调用 `AudioAnalyzer.compute_volume_envelope(audio_path, normalize=False, gain=3.5, use_peak=True)` 计算音量包络用于 Live2D 口型同步。分析器内部 gain 应用逻辑位于 `if normalize and volumes:` 条件块内，`normalize=False` 时整块跳过，`gain=3.5` 始终不生效。输出为原始 `segment.max / 32768.0` 裸值（范围 [0.000, 0.646]），口型驱动幅度过小。

## Goals / Non-Goals

**Goals:**
- `normalize=False` 时增益系数正常生效，音量值提升至合理范围
- 保持 `normalize=True` 行为不变（先归一化再加 gain）
- 不改动对外 API 签名

**Non-Goals:**
- 不引入新的参数或配置
- 不改变 normalize 的语义
- 不修改其他调用方

## Decisions

**决策：将 gain 应用移出 `if normalize` 块**

当前 `audio.py:94-103` 结构：
```python
if normalize and volumes:                    # ← gain 在这块里面
    max_volume = max(volumes)
    if max_volume > 0:
        volumes = [v / max_volume for v in volumes]
    if gain != 1.0:
        volumes = [min(1.0, v * gain) for v in volumes]
```

改为：
```python
if normalize and volumes:
    max_volume = max(volumes)
    if max_volume > 0:
        volumes = [v / max_volume for v in volumes]
    else:
        volumes = [0.0] * len(volumes)

if volumes and gain != 1.0:                  # ← gain 移到外面
    volumes = [min(1.0, v * gain) for v in volumes]
```

理由：
- `gain` 和 `normalize` 是两个独立概念：归一化解决动态范围问题，增益解决幅度绝对值问题
- 原代码将它们耦合在同一个条件块内，导致非归一化模式下 gain 失效
- 分离后，两种模式均可独立使用 gain

**不采用方案**：改为 `normalize=True` — 这会引入全局归一化，第一个响音会压制后续口型幅度，与注释"without global normalization"的原始意图冲突。

## Risks / Trade-offs

- [低风险] `gain` 在非归一化模式下可能导致部分帧 clip（`min(1.0, v * gain)` 的 clamp 保证了这一点在已有控制中）
- [无风险] `_compute_volumes` 中已有二次 clamp（`[min(1.0, v) for v in volumes]`），安全性双重保障
- 所有现有使用 `normalize=True` 的调用方不受影响
