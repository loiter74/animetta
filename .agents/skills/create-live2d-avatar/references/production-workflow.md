# Live2D 制作流程与现成能力复用

核实日期：2026-10-18。依据 Live2D 官方手册、教程和 PSD2Live 官方版本资料；以下是可核对的厂商制作基线与本项目决策，不代表所有工作室采用同一套层数、参数或验收数值。

## 先处理原画，再处理绑定

官方流程依次为素材准备、建模、动画和应用导出。素材准备包括按可动部位分离、补齐运动后会露出的区域；变形器、参数、Glue 在建模阶段使用。[官方制作流程](https://docs.live2d.com/en/cubism-editor-manual/workflow/)

保留两份 PSD：拆件母版保留分组、蒙版及补画层；导入版将每个部件合并成一个图层。补画在新图层完成，便于继续修改。[素材拆分](https://docs.live2d.com/en/cubism-editor-manual/divide-the-material/)

官方教程将头发拆为前、侧、后发及需要独立运动的左右束；脸底补全刘海后的皮肤，眼睛拆为睫毛、眼球和补齐的眼白；颈部留出充分遮挡余量。具体拆件量由动作需求决定。[原画处理教程及 Hiyori 参考入口](https://docs.live2d.com/en/cubism-editor-tutorials/psd/)

**项目入口条件：**隐藏相邻部件逐层检查后，皮肤、头发、衣领等不同运动责任可以分别编辑；重新组合仍保持已确认外观。若图层同时含随头运动的发丝与随身运动的衣料，先返工拆件与补画，不进入接缝参数拟合。

## 问题应返回哪一阶段

下表是结合鲸鱼女仆实际像素、UV 和姿势追踪得出的项目判断；官方资料不提供该角色的裁切轮廓。

| 已见现象 | 已确认的责任 | 下一步产物 |
| --- | --- | --- |
| 刘海中出现肤色竖条、蓝色硬边 | Face／Headwear 混有旧肤色，新原画的发际线又与旧图不同 | 连续脸底及干净发层；在拆件母版修复材质归属 |
| 闭眼出现旧肤色矩形 | 闭眼源图携带不匹配的背景 | 可连续闭合的眼睫／眼皮层；已通过近景的透明睫毛候选保留为可用素材 |
| 转头出现整条蓝发台阶 | Neck 横带和 Topwear 中混有固定衣料及头发，统一接身体会拉错发层 | 独立颈皮肤、衣领及发片，补齐相互遮挡区域 |
| 局部正确，组合姿态折叠 | 层级、网格或关键形态需要调整 | 在正确分层上修正父级、过渡网格和组合形态 |
| 编辑器正确、导出后错页或漂移 | 格式转换／导出链问题 | 最小导出复现与兼容性结论；不把导出补丁带回原画制作 |

皮肤填色本身是合法的遮挡方法；需要消除的是错位、残留旧背景和不匹配的边缘，不能把所有肤色遮挡层一概删掉。[官方口部遮挡说明](https://docs.live2d.com/en/cubism-editor-tutorials/psd/)

## 优先复用的现成功能

| 工作 | 已有能力与边界 |
| --- | --- |
| 拆件、补底 | 官方 Photoshop 拆件插件提供选区 Cut Out、填色、Transparency Fill 和保留蒙版的新图层；结果仍须检查发丝及遮挡区域。使用前核对本机 Photoshop 与插件可用性。[插件说明](https://docs.live2d.com/en/cubism-editor-manual/material-separation-ps-plugin-manual/) |
| 更换修好的原画 | Cubism 的 PSD 重导入可调整已有部件、添加新部件；保持层命名与顺序稳定。已有关键帧的网格需谨慎调整，官方推荐需要保护形态时手工编辑。[PSD 重导入](https://docs.live2d.com/en/cubism-editor-manual/psd-re-import/) |
| 复用绑定结构 | 模型模板可迁移变形器结构与动作，应用后检查 ArtMesh 对应、绘制顺序和父级；局部发模板仍要挂到正确头部层级。[应用模型模板](https://docs.live2d.com/en/cubism-editor-manual/applying-the-model-template/) |
| 常规绑定与检查 | 复用原生 Warp／Rotation Deformer、手工眼口网格和 Validate Deformer。父级影响子级；验证工具可定位越出父 Warp 的顶点。[层级组合](https://docs.live2d.com/en/cubism-editor-manual/combintion-of-parent-child-relation/) · [变形器检查](https://docs.live2d.com/en/cubism-editor-manual/convenient-function-deformer/) · [眼口网格](https://docs.live2d.com/en/cubism-editor-manual/mesh-edit-manual/) |
| 局部增量与组合 | 目标工具、导出版本及播放器支持时使用原生 Blend Shape；默认形稳定后再制作，避免继续修改默认形影响全部差分。[Blend Shape](https://docs.live2d.com/en/cubism-editor-manual/blend-shape/) |
| 接缝 | Glue 连接两个 ArtMesh 的重合顶点。先建立真实对应边界，再调权重；修改已胶合网格前先解绑，之后检查受影响参数。[Glue](https://docs.live2d.com/en/cubism-editor-manual/glue/) |
| 检查组合动作 | Random Pose 可选择参与的参数，用于发现多轴组合问题；与失败姿势的确定性复现配合使用。[随机姿势](https://docs.live2d.com/en/cubism-editor-manual/random-pose/) |
| 表情与物理 | 在模型中做好眼眉口形态，再用 exp3 参数组合与淡入淡出；核对 Add／Multiply／Overwrite 对眨眼和口型的影响。使用现有 SDK 物理阶段并核对 FPS 支持。[表情机制](https://docs.live2d.com/en/cubism-sdk-manual/expression/) · [物理与 FPS](https://docs.live2d.com/en/cubism-editor-manual/check-the-physics/) |
| Atlas 与运行导出 | 使用编辑器的 atlas 自动布局和间距设置，再导出与目标 SDK 兼容的资源；atlas 在素材和动作稳定后整理。[纹理图集](https://docs.live2d.com/en/cubism-editor-manual/texture-atlas-edit/) |

Glue 不能生成缺失画面，也不能改变一个纹理像素属于头发还是衣服。零三角不可见锚点是本任务尝试的自定义方案，查阅的官方教程没有将其列为通用建模步骤；其几何距离接近零也不能证明可见接缝正确。

## PSD2Live 的使用边界

PSD2Live 是独立工具，不是 Live2D 官方 Cubism Editor。项目声明具备分层 PSD 导入、自动绑定、网格／变形器、物理、动画及 CMO3／MOC3 导出；本机曾使用 3.4.5。能力声明不代表具体角色的精修质量或全部格式往返均已验证。[官方仓库固定版本](https://github.com/tsunehimatoi/psd2live/tree/v3.4.5) · [3.4.5 发布说明](https://github.com/tsunehimatoi/psd2live/releases/tag/v3.4.5)

该版本已有 `source_split_polygon`、`source_split_components` 和 `source_split_depth`，用于多边形、网格连通部件及前后层拆分，包含已有绑定的迁移路径。先核对当前运行构建暴露的 operation schema，再验证这些功能，不从自写三角形裁切器起步。拆分已有像素仍不能补出缺失原画。[拆分与拓扑](https://github.com/tsunehimatoi/psd2live/blob/v3.4.5/docs/zh/spec/MESH_TOPOLOGY_AND_SPLIT.md) · [MCP 能力发现](https://github.com/tsunehimatoi/psd2live/blob/v3.4.5/docs/zh/agent/MCP_AUTHORING.md)

**CMO3 重建的源层有边界：**该版本导入代码按当前网格 bounds 建立栅格，再将 atlas 按三角形绘回。网格外或原本缺失的遮挡内容不会因此恢复。因此 PSD 逐层 RGBA 往返一致，只能证明当前重建层保真；完整拆件母版仍需从原始立绘修复，不能把导回的 PSD 当作原始图层恢复。[重建实现](https://github.com/tsunehimatoi/psd2live/blob/v3.4.5/src/main/kotlin/io/github/psd2live/core/Cmo3ModelImport.kt#L310)

优先使用当前版本已提供的分层、网格、参数、素材替换与导出功能。精修若被工具兼容性阻挡，先做最小原生导出对照，再决定转到 Cubism Editor 完成相应阶段；不因已有自动化接口就继续增加 Java 转换器或二进制修补器。

本项目 3.4.5 中已复现的错页、局部坐标丢失及重复 atlas 槽，保留在 [PSD2Live 诊断附录](psd2live.md)。它们是版本限定的恢复经验，不能作为新角色的常规生产流程。

## 本项目采用的制作顺序

1. **确定交付动作与外观。**冻结角色、服饰、标准与特殊表情，以及目标播放器支持的格式；按所需运动决定拆件。
2. **修好拆件母版。**先清理脸／刘海、颈／衣领／侧后发的混合材质并补齐遮挡区；输出独立的导入 PSD。
3. **检查默认组合。**在原生编辑器确认单层与组合外观，分别检查标准、特殊表情；发现漏肤、硬边或错色就返回步骤 2。
4. **制作局部与头身运动。**复用模板和原生变形器、眼口参数及必要 Glue；先看单轴、过渡及已失败的少数姿势，再扩大组合范围。
5. **整理表情、动作与物理。**默认形稳定后增加差分；口型、眨眼、待机与物理明确写入责任，检查真实连续运动。
6. **导出并接入。**检查原生模型到 Core 的一致性、素材完整性和实际画面，再进入 `/live.html`；分别记录源图尺寸、贴图尺寸和实际 3840×2160 输出。

以上步骤的顺序、有限姿势优先和 Animetta 集成检查是本项目采用的流程，不宣称是厂商规定的统一商业级验收指标。零翻折、参数数量和 4K 输出均不能单独替代视觉验收。
