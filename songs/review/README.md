# 本地人工听审

评审工具把不可覆盖的候选 run 保存在 `runs/<run_id>/`。该目录只保存本机音频索引、工具与
页面快照、草稿、追加式决定日志、派生状态和截图，不纳入版本控制。

从仓库根目录执行：

```powershell
py -3.13 -m scripts.train.review_data --project songs create --run-id voice-review-r001
py -3.13 -m scripts.train.review_data --project songs serve --run-id voice-review-r001
py -3.13 -m scripts.train.review_data --project songs status --run-id voice-review-r001
py -3.13 -m scripts.train.review_data --project songs organize --run-id voice-review-r001
```

`organize` 会按当前事件头生成不可覆盖的决定、完整事件历史、文本修订和汇总报告。确认是决定
按钮与自动保存竞态产生的逐字相同草稿时，可额外传入 `--reconcile-redundant-drafts`，原草稿会
先进入 `draft-archive.jsonl`，不会直接丢弃。

听审决定不会直接修改 `manifests/sources.csv` 或 `manifests/clips.csv`。完成全部条目并通过
接受时长门禁后，仍需明确确认同一个 run ID 才能应用：

```powershell
py -3.13 -m scripts.train.review_data --project songs apply `
  --run-id voice-review-r001 `
  --confirm-run-id voice-review-r001
```
