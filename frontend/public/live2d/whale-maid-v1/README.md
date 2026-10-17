# 鲸鱼女仆 Live2D 第一版

全身、长发、深蓝长袖女仆服。保留 `standard`（标准微笑）和 `goofy`（傻笑）两种表情。

预览地址：`/live.html?review=1&scene=empty&avatar=whale-maid-v1`。左下角可切换表情和运行有界口型演示；普通直播页面不显示这些控件。当前默认模型仍由模型配置选择。

## 文件

- `whale-maid-v1.model3.json`：运行入口；同目录包含真实 Cubism `.moc3`、贴图、物理、动作及两份表情文件。
- `source/whale-maid-v1.psd`：14 个实际素材图层，可继续修画。
- `source/whale-maid-v1.cmo3`：包含第一版网格、参数、形变和层级的可编辑工程。
- `source/standard.png` / `goofy.png`：用户确认的完整立绘。
- `source/face-underpaint.png` / `blink.png`：补画来源。面部底色仅取脸部区域，外圈半透明像素不用于成品。

## 生成与绑定

原画及局部编辑使用内置 image_gen：成年等身全身、蓝青渐变长发、鲸鳍耳和鲸尾、收腰深蓝长袖女仆裙、白围裙、金色袖饰和蓝色菱形胸针。标准版为闭嘴微笑；傻笑版保留相同造型，使用半眯眼和张口笑；另外补画无五官面部底色及闭眼睫毛。

使用 [PSD2Live 3.4.5](https://github.com/tsunehimatoi/psd2live/releases/tag/v3.4.5) 原生素材分割、PSD 导出、网格生成和工程编辑。先从分层 PSD 干净编译，再恢复绘制层级并添加 `ParamTailAngle`。PSD2Live 3.4.5 重新导出导入工程时会丢失 MOC 的贴图页索引，因此成品保留干净编译的七张贴图，并按 `source/texture-pages.json` 恢复各 ArtMesh 的页号。重新导出后可运行 `node source/restore-texture-pages.cjs` 恢复并校验 MOC。七页 2048 贴图、网格间距 24px、头部强度 0.35、身体强度 0.3。生成工具本身不作为 Animetta 的依赖。

`ParamMouthOpenY` 驱动嘴型；`ParamEyeLOpen` / `ParamEyeROpen` 驱动睁闭眼。Idle 包含呼吸、眨眼、身体和鲸尾轻摆；背发使用物理参数。Nod / Shake 用于语义动作。

Animetta 的模型配置将傻笑静息口型设为 0.82，并继续叠加说话开合。`.exp3.json` 保留眼神差异；其他播放器若只加载表情文件，需要同时设置静息口型才能得到同样的张口傻笑。

## 第一版范围

已拆分头、躯干、背发、鲸尾、眉、双眼、闭眼和两种嘴型。眼白、虹膜、睫毛尚未逐件拆分，视线跟随暂未绑定；肩颈接缝和大角度转头仍需要下一轮精修。此版用于确认完整外观与基础动作。
