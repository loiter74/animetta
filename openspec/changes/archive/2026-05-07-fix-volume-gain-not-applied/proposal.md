## Why

Live2D 口型同步音量（volume envelope）值偏低，导致角色嘴巴张不开。根因是 `output_node.py` 调用 `compute_volume_envelope` 时传 `normalize=False, gain=3.5`，但 `gain` 仅在 `if normalize` 条件块内生效，非归一化模式下被静默跳过，口型驱动音量始终为原始峰值（最大仅 0.646）。

## What Changes

- 将 `src/anima/avatar/analyzers/audio.py` 中 `AudioAnalyzer.compute_volume_envelope` 方法的 gain 应用逻辑移出 `if normalize` 条件块
- `normalize=False` 时依然对音量应用 `gain` 系数并 clamp 至 `[0, 1]` 区间
- 不改变 `normalize=True` 时的行为（先归一化再加 gain）

## Capabilities

### New Capabilities
无新能力引入，纯 bug 修复。

### Modified Capabilities
无 spec 级别的行为变化，`compute_volume_envelope` 的 API 签名不变。

## Impact

- `src/anima/avatar/analyzers/audio.py`：gain 逻辑位置调整
- 下游调用不受影响（API 不变，仅非归一化模式下 gain 从"不生效"变为"生效"）
- Live2D 口型幅度提升至合理范围
