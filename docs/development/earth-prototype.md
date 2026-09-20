# 地球探索原型

这是用于评审探索节奏的临时原型。真实 Cesium 三维地球与 Esri 卫星影像已经接入，引导对话使用固定脚本，尚未接入 Anima 的 LangGraph、视觉模型、ASR 或宿主 TTS。它不属于正式产品入口，也不进入生产构建。

## 启动与操作

在 `frontend/` 执行 `pnpm earth:prototype`，浏览器打开 <http://127.0.0.1:3011/earth-prototype.html>。首次拉取代码后先执行 `pnpm install --frozen-lockfile`。端口被占用时先核对进程，不终止其他任务。

1. 点击“好像是在上海”：镜头用约 5 秒靠近上海，等影像就绪后解释。
2. 默认留 7 秒阅读解释，再等待 5 秒反馈，随后在同一城市内移动到区域概览。
3. 区域概览不自动选择行政区。点击“大概是青浦区”后，再点击“我记得淀山湖”。
4. 湖泊整体视图解释后，可自动靠近同一湖区的东侧观察点。该点只是观察起点，不是用户住址推断。
5. 点击“这条路我经常走”或“指认这里”，再点击地图。标记保留当前镜头，仅记录用户选择的经纬度，不声称识别道路名称。
6. 拖动、滚轮、开始输入或“暂停”立即取消当前飞行、朗读和倒计时。点击“继续观察”后重新解释当前观察层级。选中“朗读解释”使用浏览器系统语音，倒计时从朗读结束后开始。

支持的输入为上海、青浦、淀山湖、这条路、暂停、继续。其他输入会说明脚本边界。任意全球位置可以手动拖动探索，但暂不支持任意地点的自然语言搜索。

## 软件与接口

| 能力 | 准备状态 | 限制 |
| --- | --- | --- |
| CesiumJS 1.133.0 | 开发依赖已锁定，本地加载 JS、Worker 与静态资源 | Apache-2.0；需要支持 WebGL 的浏览器 |
| Esri World Imagery | 默认真实卫星底图，保留 Cesium 数据归属提示 | 需要联网，分辨率因地区不同；公开服务可访问不等于开放数据或无限商用授权 |
| Google Photorealistic 3D Tiles | 页面“地图接口”中有真实连接入口 | 尚无用户密钥，未验证实景调用；需要 Map Tiles API、计费和受限密钥，覆盖非全球 |
| 地形与三维建筑 | 默认椭球地球加卫星纹理 | 未配置高程服务；不能把默认底图称为三维实景或地形起伏 |
| 地点与行政边界 | 上海示例的人工观察坐标与标签 | 无行政边界数据，无 Places API，道路名称未解析 |
| Anima 模型与语音 | 浏览器内工具接口已定义 | 尚未注册产品工具，不连接正式 Socket，不调用宿主模型 |

Cesium 的 protobufjs 依赖安装脚本只用于版本提示，本项目通过 `allowBuilds.protobufjs: false` 明确禁用。无需执行 `pnpm approve-builds`。

Google 设置：在自己的 Google Cloud 项目启用 Map Tiles API 与计费，创建浏览器 API key，限制 API 为 Map Tiles API，允许来源为 `http://127.0.0.1:3011/*`，在原型界面输入。密钥不写入源码、磁盘或浏览器存储；连接后清空输入框，但请求期间仍由浏览器持有。账户开通、费用与上海实景覆盖尚未验证。

## 原型控制接口

页面就绪后，浏览器内提供 `window.earthPrototype`：

```javascript
await window.earthPrototype.focus(1) // 0 地球 / 1 上海 / 2 区域 / 3 青浦 / 4 湖泊 / 5 湖岸
window.earthPrototype.pause()
window.earthPrototype.getView() // 位置、朝向、层级、阶段、所选点、瓦片就绪状态
window.earthPrototype.capture() // 当前地图 canvas 的 PNG data URL
```

这是同页面的原型接口，不是已部署的 MCP 或后端 HTTP API。后续正式接入时，由 LangGraph 的产品工具发出语义动作，前端回传视图及用户指认；视觉模型收到画面后再决定下一步。模型不能因为用户沉默而确认住址或任意选择行政区。

当前已识别的局限：语音为系统可选能力，未验证宿主声音；地图加载最多等 20 秒，超时暂停；交互针对桌面；原型保留渲染缓冲用于截图，正式接入时需重新评估开销；Google 请求失败会保持底图。

## 来源

- [CesiumJS 快速开始](https://cesium.com/learn/cesiumjs-learn/cesiumjs-quickstart/)
- [Cesium 影像接口](https://cesium.com/learn/cesiumjs-learn/cesiumjs-imagery/)
- [Google 三维实景覆盖](https://developers.google.com/maps/documentation/javascript/3d/coverage)
- [Google 三维渲染接入](https://developers.google.com/maps/documentation/tile/use-renderer)
- [Esri World Imagery 服务](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer)
- [Esri 归属显示要求](https://doc.arcgis.com/en/arcgis-online/reference/display-copyrights.htm)
