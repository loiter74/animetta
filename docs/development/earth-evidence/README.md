# 地球探索验证证据

这是用户明确要求保留的交付数据，不是运行时自动产物。仅包含上海、青浦、淀山湖固定公开路线与设备/源码版本信息，不含用户住址、账号、密钥或真实对话。

`manifest.json` 保存冻结预测、来源 SHA256、每组原始文件 SHA256、统计口径和局限。四个 `*-raw.json` 文件保留未经舍入的 `runs[].steps[].frames`、`elapsedMs`、取消前后视图与耗时。移除了冗余瓦片响应列表和机器绝对路径，完整原始文件仍在报告列出的可视化目录。

组别：

- 改造前：`perf-baseline-isolated-raw.json` 的第 1–3 轮，以及 `perf-baseline-resume-raw.json` 的第 4–5 轮。
- 共享角色改造后：`perf-post-renderer-raw.json` 的第 1–2 轮，以及 `perf-post-renderer-resume-raw.json` 的第 3–5 轮。
- 每组各五条成功路线；首批文件中的后续失败照实保留，不能解释为第五轮成功率为 100%。

## 复核统计

在本目录运行下面的独立 Node.js 代码即可复算每组 RAF 和取消最近秩 p95；它只读 JSON，不启动浏览器、服务或模型。

```javascript
const fs = require('node:fs');
const p95 = values => [...values].sort((a, b) => a - b)[Math.ceil(values.length * 0.95) - 1];
for (const files of [
  ['perf-baseline-isolated-raw.json', 'perf-baseline-resume-raw.json'],
  ['perf-post-renderer-raw.json', 'perf-post-renderer-resume-raw.json'],
]) {
  const runs = files.flatMap(file => JSON.parse(fs.readFileSync(file, 'utf8')).runs);
  const frames = runs.flatMap(run => run.steps.flatMap(step => step.frames));
  console.log(files[0], {
    successfulRoutes: runs.length,
    frameSamples: frames.length,
    frameP95Ms: p95(frames),
    cancelNextFrameP95Ms: p95(runs.map(run => run.cancel.nextFrameMs)),
  });
}
```

## 复现采样条件

Chrome headless，1600×1000、DPR 1，真实 Cesium 和 Mao Live2D。原始版本为 `bcbc6727`，从已提交前端隔离导出；后版源码哈希见 manifest。每轮依次调用脚本原型 `focus(1..5)`，等待每段进入解释阶段后暂停，记录导航期间 RAF 间隔。每轮末尾再次发起 `focus(1)`，经过两帧调用暂停，分别记录同步调用和下一帧观察时间，并再观察十帧位置。

完整采样脚本位于 [验证报告](../earth-exploration-verification.md) 列出的可视化目录。再次采样应新建输出批次，保留既有失败与预测；与正式 Dashboard 的数据分开，不能替代正式地图、真实对话、语音播放或视觉授权验收。

RAF 不等于实际呈现 FPS；取消仅五次样本；缓存与并行开发负载未完全隔离。此次观测没有证明性能提升。

## 正式 Dashboard 与共享播放验证

新增的正式入口证据与上述原型数据分开保存，原始 manifest 和冻结预测未修改。

- `formal-acceptance.json`：真实正式入口分批结果、成功步骤、失败批次说明、无敏感载荷的 Socket 元数据、实际播放状态转换、三次进入退出、三个窗口的布局与部署/源码验证指纹。
- `formal-map-timing.json`：Chrome 153 / NVIDIA RTX 5090 D v2 的五次约一秒运镜接管原始 RAF 间隔、输入/取消/下一帧时间、取消前后相机位置。不是原型完整路线对照，也不是 GPU 呈现 FPS。
- `formal-manifest.json`：上述两份文件的 SHA256、大小与脱敏口径。真实公开测试音频与完整模型对话不纳入仓库。

最终文本批次 `formal-1790010777784` 通过上海、青浦行政区、淀山湖、完整“杭州西湖”输入；此前失败批次没有覆盖。语音输入仍因 MiMo 返回 401 未通过，图像分析未授权。正式运行报告保存其限制，不能从其他成功步骤推断这些能力可用。

复算正式时序：读取 `formal-map-timing.json` 的 `samples`，展开 `intervals` 得到 663 个 RAF 间隔；对 `inputToCancelMs`、`cancelMs`、`nextFrameMs` 分别取上文最近秩 p95。五次 p95 即该小样本最大值，不能外推为长期生产尾延迟。
