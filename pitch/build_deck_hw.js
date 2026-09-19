// Animetta 投资汇报 · 华为胶片风格版 — 14 页
// 方法论依据：Obsidian《华为入职学习/如何制作周报与胶片？》
// 标题=结论式一句话；结尾=红色字总结；中间=字体一致、讲数据、一页一主题、讲逻辑
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Animetta";
pres.title = "Animetta 投资汇报（华为胶片风格版）";

// ---------- 设计令牌：白底 · 黑字 · 华为红 ----------
const W = 13.33, H = 7.5, M = 0.5;
const INK = "1F1F1F";
const GREY = "595959";
const LGREY = "F2F2F2";
const HAIR = "D9D9D9";
const MID = "8C8C8C";
const RED = "C8102E";      // 华为红（仅用于重点与结论）
const PINK = "FDEBEE";     // Animetta 列淡红底
const WHITE = "FFFFFF";
const F = "微软雅黑";       // 字体一致
const TOTAL = 14;

function hw(s, sec, title) {
  s.addText(sec, { x: M, y: 0.4, w: 9, h: 0.3, fontFace: F, fontSize: 11, bold: true, color: MID, charSpacing: 1, margin: 0 });
  s.addText(title, { x: M, y: 0.7, w: W - 2 * M, h: 0.82, fontFace: F, fontSize: 20.5, bold: true, color: INK, lineSpacingMultiple: 1.12, margin: 0 });
}
function pageNum(s, n) {
  s.addText(`${String(n).padStart(2, "0")} / ${TOTAL}`, { x: 11.9, y: 7.12, w: 0.95, h: 0.3, fontFace: F, fontSize: 10, color: MID, align: "right", margin: 0 });
}
function srcLine(s, txt) {
  s.addText(txt, { x: M, y: 6.98, w: 11.2, h: 0.48, fontFace: F, fontSize: 10, color: GREY, valign: "top", margin: 0 });
}
function redConclusion(s, txt, y) {
  s.addText(txt, { x: M, y: y || 6.4, w: 12.33, h: 0.5, fontFace: F, fontSize: 14.5, bold: true, color: RED, margin: 0 });
}
function box(s, x, y, w, h, fill, line, red) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: line ? { color: line, width: red ? 1.5 : 1 } : { type: "none" }, rectRadius: 0.05 });
}
function vline(s, x, y, h) { s.addShape(pres.shapes.LINE, { x, y, w: 0, h, line: { color: HAIR, width: 0.75 } }); }
function hline(s, x, y, w) { s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: HAIR, width: 0.75 } }); }

// ============ H1 封面：华为四段式结论标题 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText("投资汇报 · 2026 年 9 月 · 机密", { x: 1.2, y: 0.85, w: 8, h: 0.35, fontFace: F, fontSize: 13, color: GREY, charSpacing: 1, margin: 0 });
  s.addText("Animetta", { x: 1.2, y: 1.25, w: 10.9, h: 0.95, fontFace: F, fontSize: 46, bold: true, color: INK, margin: 0 });
  s.addText("开源全栈 AI 伙伴与虚拟主播框架", { x: 1.2, y: 2.25, w: 10.9, h: 0.5, fontFace: F, fontSize: 20, color: GREY, margin: 0 });
  hline(s, 1.2, 2.95, 10.9);
  const lines = [
    ["基于", " AI 陪伴市场高速增长与 Neuro-sama 商业闭环验证的产业机会，"],
    ["结合", " 创作者对「开源自托管 · 全栈能力」AI 伙伴的核心诉求，"],
    ["借鉴", " AIRI 与 Open-LLM-VTuner 的开源社区实践，"],
    ["制定", " Animetta 全栈 AI 伙伴与虚拟主播框架的投资与共建方案。"]
  ];
  lines.forEach((ln, i) => {
    const y = 3.25 + i * 0.62;
    s.addText(ln[0], { x: 1.2, y, w: 0.65, h: 0.55, fontFace: F, fontSize: 18, bold: true, color: RED, margin: 0 });
    s.addText(ln[1], { x: 1.88, y, w: 10.5, h: 0.55, fontFace: F, fontSize: 18, color: INK, margin: 0 });
  });
  s.addText("把下一个 Neuro-sama，交给每个人。", { x: 1.2, y: 6.05, w: 10.9, h: 0.5, fontFace: F, fontSize: 18, bold: true, color: RED, margin: 0 });
  s.addText("汇报人：Animetta 团队", { x: 1.2, y: 6.75, w: 8, h: 0.35, fontFace: F, fontSize: 12, color: GREY, margin: 0 });
  s.addNotes("华为胶片式封面：标题即结论，四段式（基于/结合/借鉴/制定）概括整份汇报的逻辑链。");
})();

// ============ H2 汇报提纲 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "汇报提纲", "看市场、看竞品、看方案、看回报");
  const items = [
    ["一", "市场与机会", "全球市场十年量级增长 · Neuro-sama 验证 AI 主播天花板"],
    ["二", "竞品分析", "四类玩家格局 · 五项能力矩阵 · C 端与 B 端付费验证"],
    ["三", "方案与卖点", "全栈一体化 · 混合记忆 · 企业级工程骨架"],
    ["四", "规划与回报", "四阶段路线 · 四层变现 · 结论与建议"]
  ];
  items.forEach((it, i) => {
    const y = 1.95 + i * 1.2;
    s.addText(it[0], { x: M, y: y + 0.02, w: 0.7, h: 0.75, fontFace: F, fontSize: 26, bold: true, color: RED, margin: 0 });
    s.addText(it[1], { x: 1.4, y, w: 2.9, h: 0.75, fontFace: F, fontSize: 19, bold: true, color: INK, valign: "middle", margin: 0 });
    s.addText(it[2], { x: 4.4, y, w: 8.4, h: 0.75, fontFace: F, fontSize: 13.5, color: GREY, valign: "middle", margin: 0 });
    if (i < 3) hline(s, M, y + 0.95, 12.33);
  });
  pageNum(s, 2);
  s.addNotes("提纲页：四段汇报逻辑——先证明市场与天花板，再证明竞争空缺，然后给方案，最后谈回报。");
})();

// ============ H3 市场机会 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "一、市场与机会", "全球 AI 陪伴市场六年增长四倍（CAGR 30.8%），中国虚拟数字人核心规模 480.6 亿元");
  s.addText("全球 AI 陪伴市场规模（亿美元）", { x: M, y: 1.72, w: 6.4, h: 0.34, fontFace: F, fontSize: 13.5, bold: true, color: INK, margin: 0 });
  s.addChart(pres.charts.BAR, [{
    name: "市场规模", labels: ["2024", "2025", "2030E", "2033E"], values: [28.2, 36.8, 140.8, 318.0]
  }], {
    x: M, y: 2.15, w: 6.4, h: 4.2, barDir: "col", barGapWidthPct: 45,
    varyColors: true, chartColors: ["C9C9C9", "A6A6A6", "7F7F7F", RED],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11.5, dataLabelFontFace: F, dataLabelFormatCode: "#,##0.#",
    catAxisLabelColor: INK, catAxisLabelFontSize: 12, catAxisLabelFontFace: F, catAxisLabelFontBold: true,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false, chartArea: { fill: { color: WHITE } }
  });
  const stats = [
    ["30.8%", "全球 AI 陪伴市场 CAGR（2024–2030，Grand View Research）", RED],
    ["480.6 亿元", "2025 中国虚拟数字人核心市场规模（艾媒咨询，带动市场 6,402.7 亿元）", INK],
    ["+64%", "2025H1 AI 陪伴 App 消费支出同比（8,200 万美元，Appfigures）", INK]
  ];
  stats.forEach((st, i) => {
    const y = 1.95 + i * 1.42;
    s.addText(st[0], { x: 7.3, y, w: 2.5, h: 0.62, fontFace: F, fontSize: 28, bold: true, color: st[2], margin: 0 });
    s.addText(st[1], { x: 7.3, y: y + 0.62, w: 5.5, h: 0.62, fontFace: F, fontSize: 12, color: GREY, lineSpacingMultiple: 1.2, margin: 0 });
    if (i < 2) hline(s, 7.3, y + 1.28, 5.53);
  });
  redConclusion(s, "定性判断：C 端付费行为已经发生，供给端缺少「开源自托管 × 全栈交互」的产品。", 6.42);
  srcLine(s, "来源：Grand View Research（2024–2030 及 2026 年更新版预测）；艾媒咨询《中国虚拟数字人产业白皮书》；Appfigures（2025-08）");
  pageNum(s, 3);
  s.addNotes("定量：三个规模数字；定性判断用红字给出——供给空缺是后面所有论证的起点。");
})();

// ============ H4 天花板验证 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "一、市场与机会", "Neuro-sama 登顶 Twitch 订阅第一：AI 主播的订阅、打赏、传播闭环已被完整验证");
  const th = (t) => ({ text: t, options: { fill: { color: INK }, color: WHITE, bold: true, fontSize: 12.5, align: "center", valign: "middle", fontFace: F } });
  const c1 = (t) => ({ text: t, options: { color: INK, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const c2 = (t) => ({ text: t, options: { color: RED, bold: true, fontSize: 13, align: "center", valign: "middle", fontFace: F } });
  const c3 = (t) => ({ text: t, options: { color: GREY, fontSize: 11.5, align: "center", valign: "middle", fontFace: F } });
  const c4 = (t) => ({ text: t, options: { color: GREY, fontSize: 12, align: "left", valign: "middle", fontFace: F } });
  s.addTable([
    [th("指标"), th("数值"), th("时间"), th("含义")],
    [c1("Twitch 活跃订阅"), c2("16.2 万 · 全站第一"), c3("2026-01"), c4("超越全部真人主播频道")],
    [c1("单场直播峰值观众"), c2("45,605"), c3("2025-01"), c4("AI VTuber 历史纪录")],
    [c1("Subathon 累计付费订阅"), c2("26.2 万"), c3("2025-12"), c4("订阅与打赏收入持续验证")],
    [c1("YouTube 订阅 / 累计播放"), c2("91.6 万 / 4.09 亿"), c3("2026-09"), c4("切片内容的二次传播效应")]
  ], { x: M, y: 1.78, w: 12.33, colW: [3.2, 2.6, 1.4, 5.13], rowH: [0.5, 0.68, 0.68, 0.68, 0.68], border: { pt: 0.5, color: HAIR }, valign: "middle", margin: 0.06, fontFace: F });
  s.addText("补充事实：Neuro-sama 由开发者 Vedal 近乎独立运营，自研约 20 亿参数 LLM —— 单人 + 一套框架即可达到头部真人主播产能，但其能力闭源、单人设、不可复用。", { x: M, y: 5.55, w: 12.33, h: 0.7, fontFace: F, fontSize: 13, color: GREY, lineSpacingMultiple: 1.25, margin: 0 });
  redConclusion(s, "结论：天花板已被验证，稀缺的是「人人可用」的产品化框架。", 6.42);
  srcLine(s, "来源：Twitch / Streams Charts；Netinfluencer、Tubefilter（2026-01）；Social Blade（2026-09）；Wikipedia");
  pageNum(s, 4);
  s.addNotes("华为式数据页：表格讲定量，红字给结论。核心信息：闭源单人作坊验证了天花板，产品化机会留给我们。");
})();

// ============ H5 竞争格局 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "二、竞品分析", "四类玩家各占一角，「开源自托管 × 全栈交互」象限无人占据");
  s.addShape(pres.shapes.LINE, { x: 1.55, y: 4.05, w: 7.35, h: 0, line: { color: MID, width: 1.25, endArrowType: "triangle" } });
  s.addShape(pres.shapes.LINE, { x: 5.2, y: 1.72, w: 0, h: 4.78, line: { color: MID, width: 1.25, beginArrowType: "triangle" } });
  s.addText("闭源 SaaS", { x: 1.55, y: 6.58, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, color: GREY, margin: 0 });
  s.addText("开源自托管", { x: 7.3, y: 6.58, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: INK, align: "right", margin: 0 });
  s.addText("纯对话  ⟶  全栈具身交互（唱 · 播 · 玩）", { x: -0.75, y: 3.9, w: 2.9, h: 0.32, fontFace: F, fontSize: 11, color: GREY, align: "center", rotate: 270, margin: 0 });
  box(s, 6.4, 2.12, 2.3, 1.12, RED, null, true);
  s.addText([
    { text: "Animetta", options: { fontSize: 16, bold: true, color: WHITE, breakLine: true } },
    { text: "开源自托管 · 五项全栈", options: { fontSize: 11, color: PINK } }
  ], { x: 6.4, y: 2.12, w: 2.3, h: 1.12, fontFace: F, align: "center", valign: "middle", margin: 0 });
  box(s, 2.0, 2.12, 2.5, 0.95, WHITE, HAIR);
  s.addText([
    { text: "Neuro-sama", options: { fontSize: 13.5, bold: true, color: INK, breakLine: true } },
    { text: "闭源 · 单人设 · Twitch", options: { fontSize: 11, color: GREY } }
  ], { x: 2.0, y: 2.12, w: 2.5, h: 0.95, fontFace: F, align: "center", valign: "middle", margin: 0 });
  box(s, 5.95, 4.4, 2.85, 1.32, WHITE, HAIR);
  s.addText([
    { text: "AIRI · 4.9 万 ★", options: { fontSize: 11.5, color: INK, breakLine: true } },
    { text: "Open-LLM-VTuber · 1.4 万 ★", options: { fontSize: 11.5, color: INK, breakLine: true } },
    { text: "Amica · 0.2 万 ★（停更）", options: { fontSize: 11.5, color: GREY } }
  ], { x: 6.1, y: 4.48, w: 2.6, h: 1.16, fontFace: F, valign: "middle", paraSpaceAfter: 4, margin: 0 });
  box(s, 1.7, 4.3, 3.05, 0.95, WHITE, HAIR);
  s.addText([
    { text: "Character.AI · Replika", options: { fontSize: 11.5, color: INK, breakLine: true } },
    { text: "星野 · 猫箱 · X Eva", options: { fontSize: 11.5, color: INK } }
  ], { x: 1.7, y: 4.3, w: 3.05, h: 0.95, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  box(s, 1.7, 5.42, 3.05, 0.85, WHITE, HAIR);
  s.addText([
    { text: "硅基智能 · 腾讯智影", options: { fontSize: 11.5, color: INK, breakLine: true } },
    { text: "B 端播报型 · 非实时交互", options: { fontSize: 11, color: GREY } }
  ], { x: 1.7, y: 5.42, w: 3.05, h: 0.85, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  s.addText("为什么右上象限空缺", { x: 9.35, y: 1.72, w: 3.48, h: 0.4, fontFace: F, fontSize: 15, bold: true, color: INK, margin: 0 });
  const why = [
    ["闭源 App", "体验好，但记忆与关系锁死在云端，用户无法带走"],
    ["开源框架", "可自托管，却止步于「桌面聊天」，缺直播与歌唱"],
    ["B 端数字人", "念稿播报为主，不是能对话的实时智能体"]
  ];
  why.forEach((r, i) => {
    const y = 2.25 + i * 1.16;
    s.addShape(pres.shapes.RECTANGLE, { x: 9.38, y: y + 0.09, w: 0.12, h: 0.12, fill: { color: RED }, line: { type: "none" } });
    s.addText([
      { text: r[0], options: { fontSize: 13.5, bold: true, color: INK, breakLine: true } },
      { text: r[1], options: { fontSize: 11.5, color: GREY } }
    ], { x: 9.66, y, w: 3.2, h: 1.05, fontFace: F, paraSpaceAfter: 4, lineSpacingMultiple: 1.15, margin: 0 });
  });
  box(s, 9.35, 5.9, 3.48, 0.62, INK);
  s.addText("右上象限 = Animetta 独占卡位", { x: 9.35, y: 5.9, w: 3.48, h: 0.62, fontFace: F, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  srcLine(s, "★ 为 GitHub 星标数，来源：GitHub API 实测（2026-09-19）；其余为各公司公开资料");
  pageNum(s, 5);
  s.addNotes("格局图：灰框为现有玩家，红框为 Animetta 卡位。右侧三条定性解释空缺原因。");
})();

// ============ H6 能力矩阵 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "二、竞品分析", "五项能力对比：仅 Animetta 全覆盖，且是唯一开源自托管的全栈框架");
  const th = (t, isA) => ({ text: t, options: { fill: { color: isA ? RED : INK }, color: WHITE, bold: true, fontSize: isA ? 12.5 : 11.5, align: "center", valign: "middle", fontFace: F } });
  const lab = (t) => ({ text: t, options: { fill: { color: LGREY }, color: INK, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const ok = (t) => ({ text: t, options: { color: INK, bold: true, fontSize: 11.5, align: "center", valign: "middle", fontFace: F } });
  const midc = (t) => ({ text: t || "部分", options: { color: GREY, fontSize: 11, align: "center", valign: "middle", fontFace: F } });
  const no = { text: "—", options: { color: "BFBFBF", fontSize: 11.5, align: "center", valign: "middle", fontFace: F } };
  const aok = (t) => ({ text: t, options: { fill: { color: PINK }, color: RED, bold: true, fontSize: 11.5, align: "center", valign: "middle", fontFace: F } });
  const rows = [
    [th("能力维度"), th("Neuro-sama"), th("AIRI"), th("Open-LLM-VTuber"), th("商业陪伴 App"), th("B 端数字人"), th("Animetta", true)],
    [lab("实时语音对话"), ok("✓"), ok("✓"), ok("✓"), ok("✓"), midc("念稿播报"), aok("✓ 可打断")],
    [lab("Live2D / 虚拟形象"), ok("✓ Live2D"), ok("✓ VRM"), ok("✓ Live2D"), midc("2D 头像"), ok("✓ 视频分身"), aok("✓ Live2D")],
    [lab("长期记忆"), midc(), no, midc("会话级"), ok("✓ 锁在云端"), no, aok("✓ 混合检索")],
    [lab("AI 歌唱"), ok("✓"), no, no, midc("少数内置"), no, aok("✓ RVC 声线")],
    [lab("直播实时互动"), ok("✓ Twitch"), no, no, no, midc("带货话术"), aok("✓ B 站弹幕")],
    [lab("游戏游玩"), ok("✓"), ok("✓ MC"), no, no, no, aok("✓ MC")],
    [lab("开源自托管"), no, ok("✓"), ok("✓"), no, no, aok("✓")]
  ];
  s.addTable(rows, {
    x: M, y: 1.72, w: 12.33, colW: [2.3, 1.55, 1.55, 1.85, 1.85, 1.75, 1.48],
    rowH: [0.6, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55],
    border: { pt: 0.5, color: HAIR }, valign: "middle", margin: 0.04, fontFace: F
  });
  srcLine(s, "✓ 支持 · 部分 = 有限支持 · — 不支持。Animetta 歌唱与游戏为原型级能力（见第 12 页规划）。来源：各项目 GitHub 仓库与官方产品页（2026-09）");
  pageNum(s, 6);
  s.addNotes("矩阵是本汇报的核心证据页：一页看清——闭源最强者不可复用，可复用者不全栈，全栈且开源只有 Animetta。");
})();

// ============ H7 付费验证 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "二、竞品分析", "付费意愿双端验证：C 端千万级月活与亿美元收入，B 端亿元级营收");
  s.addText("头部 AI 陪伴产品月活（百万，2025）", { x: M, y: 1.72, w: 6.3, h: 0.34, fontFace: F, fontSize: 13.5, bold: true, color: INK, margin: 0 });
  s.addChart(pres.charts.BAR, [{
    name: "月活", labels: ["猫箱", "Talkie+星野", "Replika", "Character.AI"], values: [4.5, 20.1, 40, 45]
  }], {
    x: M, y: 2.15, w: 6.3, h: 4.15, barDir: "bar", barGapWidthPct: 50,
    varyColors: true, chartColors: ["C9C9C9", "A6A6A6", "7F7F7F", RED],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11.5, dataLabelFontFace: F, dataLabelFormatCode: "#,##0.#",
    catAxisLabelColor: INK, catAxisLabelFontSize: 12.5, catAxisLabelFontFace: F, catAxisLabelFontBold: true,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false, chartArea: { fill: { color: WHITE } }
  });
  const fc = (t) => ({ text: t, options: { color: INK, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const fv = (t) => ({ text: t, options: { color: GREY, fontSize: 11.5, align: "left", valign: "middle", fontFace: F } });
  s.addTable([
    [fc("Character.AI"), fv("2025 年收入约 5,000 万美元（+66%）；获 Google 约 27 亿美元技术授权")],
    [fc("小冰公司"), fv("投后估值约 20 亿美元；2024 年以 140 亿元列胡润独角兽榜")],
    [fc("硅基智能"), fv("数字人营收 2022 年 2.23 亿 → 2024 年 6.55 亿元，已递交港股招股书")],
    [fc("定价锚点"), fv("闪剪 2,980 元/年；腾讯智影 2,000 元/形象、AI 直播间算力 1 万+/月")]
  ], { x: 7.15, y: 2.15, w: 5.68, colW: [1.55, 4.13], rowH: [0.95, 0.95, 0.95, 0.95], border: { pt: 0.5, color: HAIR }, valign: "middle", margin: 0.08, fontFace: F });
  srcLine(s, "来源：Business of Apps / WSJ；财新、胡润研究院；硅基智能招股书（财联社）；MiniMax 招股书（虎嗅转述）；点点数据（2024–2026）");
  pageNum(s, 7);
  s.addNotes("左图 C 端规模，右表 B 端与定价锚点——为第 13 页商业模式的价格带提供依据。");
})();

// ============ H8 方案总述 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "三、方案与卖点", "Animetta 以 LangGraph 状态图编排全栈链路：一条链路驱动表情、语音与工具三路输出");
  s.addText("从观众输入到三路实时输出 —— 链路每一步可插拔、可观测", { x: M, y: 1.56, w: 11, h: 0.36, fontFace: F, fontSize: 13, color: GREY, margin: 0 });
  box(s, 0.5, 3.15, 1.45, 1.3, INK);
  s.addText([
    { text: "观众", options: { fontSize: 15, bold: true, color: WHITE, breakLine: true } },
    { text: "语音 · 弹幕", options: { fontSize: 11, color: "C9C9C9" } }
  ], { x: 0.5, y: 3.15, w: 1.45, h: 1.3, fontFace: F, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 1.97, y: 3.8, w: 0.25, h: 0, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
  const chain = [["ASR 语音识别", 2.25, 1.6], ["人格 · 记忆注入", 4.15, 1.75], ["LLM 推理", 6.25, 1.45], ["情感理解", 8.05, 1.45]];
  chain.forEach((b) => {
    box(s, b[1], 3.3, b[2], 1.0, WHITE, HAIR);
    s.addText(b[0], { x: b[1], y: 3.3, w: b[2], h: 1.0, fontFace: F, fontSize: 13, bold: true, color: INK, align: "center", valign: "middle", margin: 0 });
  });
  [[3.87, 4.12], [5.92, 6.17], [7.72, 7.97]].forEach((g) => s.addShape(pres.shapes.LINE, { x: g[0], y: 3.8, w: g[1] - g[0], h: 0, line: { color: MID, width: 1.75, endArrowType: "triangle" } }));
  s.addShape(pres.shapes.LINE, { x: 9.5, y: 3.8, w: 0.22, h: 0, line: { color: MID, width: 1.75 } });
  s.addShape(pres.shapes.LINE, { x: 9.72, y: 2.75, w: 0, h: 2.1, line: { color: MID, width: 1.75 } });
  const outs = [["Live2D 表情动作", 2.3, WHITE, INK, HAIR, false], ["TTS 语音 · RVC 歌声", 3.35, WHITE, INK, HAIR, false], ["工具调用：Minecraft · 直播互动", 4.4, RED, WHITE, null, true]];
  outs.forEach((o) => {
    const yc = o[1] + 0.45;
    s.addShape(pres.shapes.LINE, { x: 9.72, y: yc, w: 0.26, h: 0, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
    box(s, 10.0, o[1], 2.83, 0.9, o[2], o[4], o[5]);
    s.addText(o[0], { x: 10.08, y: o[1], w: 2.67, h: 0.9, fontFace: F, fontSize: o[0].length > 12 ? 11.5 : 12.5, bold: true, color: o[3], align: "center", valign: "middle", margin: 0 });
  });
  const plat = [["前端", "Vue 3 · Electron · Live2D"], ["实时通道", "Socket.IO 实时会话"], ["Provider 插件制", "LLM / ASR / TTS / VAD 一键切换"], ["可观测", "OTel · Prometheus · Stats 面板"]];
  plat.forEach((p, i) => {
    const x = M + i * 3.13, w = 2.94;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 5.55, w, h: 1.0, fill: { color: LGREY }, line: { type: "none" } });
    s.addText([
      { text: p[0], options: { fontSize: 12.5, bold: true, color: INK, breakLine: true } },
      { text: p[1], options: { fontSize: 11, color: GREY } }
    ], { x: x + 0.18, y: 5.63, w: w - 0.36, h: 0.85, fontFace: F, paraSpaceAfter: 3, margin: 0 });
  });
  srcLine(s, "ASR → 人格 → LLM → 情感 → 输出的编排链路、Provider 插件与记忆系统均已实现并经测试覆盖（11 项 ADR）；歌唱与游戏工具为原型级");
  pageNum(s, 8);
  s.addNotes("方案页：一条 LangGraph 状态图串起全栈，红色输出框是差异化的第三路——工具调用（玩游戏、直播互动）。");
})();

// ============ H9 卖点一：全栈 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "三、方案与卖点", "卖点一：五项能力一体，同一人格与记忆贯穿全部场景，竞品平均覆盖不到两项");
  const caps = [
    ["说", "多模型大脑", "DeepSeek / Qwen / MIMO\nProvider 插件化切换"],
    ["听", "实时听觉", "流式 ASR 识别\n用户可随时打断"],
    ["唱", "AI 歌唱", "RVC 声线推理\n弹幕点歌开唱（原型）"],
    ["播", "直播营业", "B 站弹幕实时互动\nOBS 推流直播"],
    ["玩", "自主游玩", "Minecraft 世界交互\n弹幕点名互动（原型）"]
  ];
  caps.forEach((c, i) => {
    const x = M + i * 2.52, w = 2.27;
    if (i > 0) vline(s, x - 0.13, 1.95, 3.1);
    s.addText(c[0], { x: x, y: 1.95, w: w, h: 0.8, fontFace: F, fontSize: 30, bold: true, color: i === 4 ? RED : INK, margin: 0 });
    s.addText(c[1], { x: x, y: 2.85, w: w, h: 0.42, fontFace: F, fontSize: 15.5, bold: true, color: INK, margin: 0 });
    s.addText(c[2], { x: x, y: 3.35, w: w, h: 1.6, fontFace: F, fontSize: 11.5, color: GREY, lineSpacingMultiple: 1.3, margin: 0 });
  });
  hline(s, M, 5.25, 12.33);
  s.addText("覆盖对比", { x: M, y: 5.42, w: 2, h: 0.35, fontFace: F, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  const cov = [["AIRI", "●●●○○  3/5", INK], ["Open-LLM-VTuber", "●●○○○  2/5", INK], ["商业陪伴 App", "●●○○○  2/5", INK], ["Animetta", "●●●●●  5/5", RED]];
  cov.forEach((r, i) => {
    const x = 2.6 + i * 2.62;
    s.addText([
      { text: r[0], options: { fontSize: 12, bold: true, color: r[2], breakLine: true } },
      { text: r[1], options: { fontSize: 12, color: r[2] } }
    ], { x, y: 5.36, w: 2.5, h: 0.75, fontFace: F, paraSpaceAfter: 3, margin: 0 });
  });
  redConclusion(s, "结论：一体化不是五个功能的拼凑 —— 她记得的、她唱的、她玩的，是同一个「人」。", 6.42);
  srcLine(s, "覆盖统计口径见第 6 页矩阵；● 为支持项");
  pageNum(s, 9);
  s.addNotes("五列以细分隔线代替卡片（华为胶片更素）；覆盖对比给出量化差距；红字收束定性感。");
})();

// ============ H10 卖点二：记忆 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "三、方案与卖点", "卖点二：混合记忆让角色「不失忆、不变脸」，数据资产归用户所有");
  box(s, 2.55, 1.7, 2.5, 0.5, WHITE, HAIR);
  s.addText("每一轮对话", { x: 2.55, y: 1.7, w: 2.5, h: 0.5, fontFace: F, fontSize: 12.5, color: GREY, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 2.2, w: 0, h: 0.24, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
  const stores = [["Chroma 向量库", "语义记忆", 0.5], ["SQLite FTS5", "关键词记忆", 3.0], ["Markdown Wiki", "人格档案 · 兴趣画像", 5.5]];
  stores.forEach((st) => {
    box(s, st[2], 2.48, 2.2, 1.1, WHITE, HAIR);
    s.addText([
      { text: st[0], options: { fontSize: 13, bold: true, color: INK, breakLine: true } },
      { text: st[1], options: { fontSize: 11, color: GREY } }
    ], { x: st[2] + 0.15, y: 2.48, w: 1.9, h: 1.1, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 3.58, w: 0, h: 0.24, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
  box(s, 0.5, 3.86, 7.2, 0.68, WHITE, HAIR);
  s.addText("B 站梗库 —— 流行梗与直播语境持续学习（ADR-010）", { x: 0.5, y: 3.86, w: 7.2, h: 0.68, fontFace: F, fontSize: 12.5, color: INK, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 4.54, w: 0, h: 0.24, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
  box(s, 0.5, 4.82, 7.2, 0.75, INK);
  s.addText("检索融合 · 向量 70% + 关键词 30% 混合权重", { x: 0.5, y: 4.82, w: 7.2, h: 0.75, fontFace: F, fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 5.57, w: 0, h: 0.24, line: { color: MID, width: 1.75, endArrowType: "triangle" } });
  box(s, 0.5, 5.85, 7.2, 0.75, WHITE, RED, true);
  s.addText("注入下一轮对话 —— 她记得你说过的每一句话", { x: 0.5, y: 5.85, w: 7.2, h: 0.75, fontFace: F, fontSize: 13.5, bold: true, color: RED, align: "center", valign: "middle", margin: 0 });
  const vals = [
    ["数据主权", "商业 App 的记忆锁死在云端、无法迁移；自托管让用户真正拥有这段「关系」"],
    ["召回质量", "向量 + 关键词混合检索（ADR-002），比单一向量记忆召回更准"],
    ["人格一致", "Wiki 档案 + 梗库让角色不失忆、不变脸（ADR-005 / 010），长期陪伴成立"]
  ];
  vals.forEach((v, i) => {
    const y = 1.78 + i * 1.62;
    s.addText([
      { text: v[0], options: { fontSize: 14.5, bold: true, color: INK, breakLine: true } },
      { text: v[1], options: { fontSize: 12, color: GREY } }
    ], { x: 8.1, y, w: 4.75, h: 1.45, fontFace: F, paraSpaceAfter: 5, lineSpacingMultiple: 1.25, margin: 0 });
    if (i < 2) hline(s, 8.1, y + 1.44, 4.73);
  });
  srcLine(s, "混合权重 70/30 为默认配置，可调；架构见仓库 ADR-002 / ADR-005 / ADR-010");
  pageNum(s, 10);
  s.addNotes("纵向数据流：三层存储 + 梗库 → 黑色融合条 → 红框结论（注入对话）。右侧三条价值定性。");
})();

// ============ H11 卖点三：工程 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "三、方案与卖点", "卖点三：企业级工程骨架就绪 —— 商业化是叠加，不是重构");
  const stats = [["11 项", "架构决策记录（ADR）"], ["15 个", "架构分层模块"], ["63 个", "LangGraph 编排图节点"], ["OTel", "全链路分布式追踪"]];
  stats.forEach((st, i) => {
    const x = M + i * 3.13, w = 2.94;
    s.addText(st[0], { x, y: 1.7, w, h: 0.62, fontFace: F, fontSize: 30, bold: true, color: INK, margin: 0 });
    s.addText(st[1], { x, y: 2.36, w, h: 0.4, fontFace: F, fontSize: 12, color: GREY, margin: 0 });
  });
  hline(s, M, 2.95, 12.33);
  const th = (t) => ({ text: t, options: { fill: { color: INK }, color: WHITE, bold: true, fontSize: 12.5, align: "center", valign: "middle", fontFace: F } });
  const c1 = (t) => ({ text: t, options: { color: INK, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const c2 = (t) => ({ text: t, options: { color: GREY, fontSize: 12, align: "left", valign: "middle", fontFace: F } });
  const c3 = (t) => ({ text: t, options: { color: INK, fontSize: 12, align: "left", valign: "middle", fontFace: F } });
  s.addTable([
    [th("机制"), th("说明"), th("价值")],
    [c1("Provider 注册制"), c2("interface → 实现 → 工厂 → 导出"), c3("新增模型供应商零侵入核心")],
    [c1("影响感知验证"), c2("tooling.quality 按改动范围自动圈定测试组"), c3("重构有安全网，质量可回归")],
    [c1("可观测栈"), c2("OTel 追踪 + Prometheus 指标 + Stats 面板"), c3("线上问题分钟级定位")],
    [c1("一键部署"), c2("Docker Compose / Zeabur"), c3("个人版一条命令拉起全栈")]
  ], { x: M, y: 3.2, w: 12.33, colW: [2.6, 5.4, 4.33], rowH: [0.48, 0.62, 0.62, 0.62, 0.62], border: { pt: 0.5, color: HAIR }, valign: "middle", margin: 0.06, fontFace: F });
  redConclusion(s, "结论：融资将投入产品与市场，而非偿还架构债务 —— 小团队做大产品的唯一路径。", 6.42);
  srcLine(s, "数据来源：仓库 docs/adrs/（11 项 ADR）、架构知识图谱统计（15 分层 / 63 编排节点）、tooling/quality 组件映射");
  pageNum(s, 11);
  s.addNotes("四个量化数字 + 机制/说明/价值三列表：华为式工程论证。红字结论回应投资人最关心的钱花在哪。");
})();

// ============ H12 规划 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "四、规划与回报", "四阶段规划：2026Q4 公开直播验证「有人看」，2027 年形成商业闭环「有人付」");
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 2.32, w: 11.5, h: 0, line: { color: MID, width: 1.5, endArrowType: "triangle" } });
  const stages = [
    ["2026 Q3", "已达成", ["语音对话全链路闭环", "B 站直播与弹幕接入", "混合记忆 v2 落地", "歌唱 · Minecraft 原型跑通"], "solid"],
    ["2026 Q4", "规划", ["公开测试直播 30 分钟不中断", "沉淀 10 条传播切片", "观众反馈驱动人格迭代"], "hollow"],
    ["2027 H1", "规划", ["Anima Cloud 云托管 Beta", "形象 · 人格市场上线", "抖音 / YouTube 多平台"], "hollow"],
    ["2027 H2", "规划", ["企业虚拟主播私有化部署", "MCN 内容合作与分成"], "red"]
  ];
  stages.forEach((st, i) => {
    const x = M + i * 3.16, w = 2.86, cx = x + w / 2;
    const fill = st[3] === "solid" ? INK : (st[3] === "red" ? RED : WHITE);
    const lineC = st[3] === "solid" ? INK : (st[3] === "red" ? RED : MID);
    s.addShape(pres.shapes.OVAL, { x: cx - 0.14, y: 2.18, w: 0.28, h: 0.28, fill: { color: fill }, line: { color: lineC, width: 2 } });
    s.addText(st[0], { x, y: 1.62, w, h: 0.42, fontFace: F, fontSize: 16, bold: true, color: INK, align: "center", margin: 0 });
    const bw = 0.95, bx = x + 0.22;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 2.98, w: bw, h: 0.4, fill: { color: st[3] === "solid" ? INK : WHITE }, line: st[3] === "solid" ? { type: "none" } : { color: st[3] === "red" ? RED : MID, width: 1 }, rectRadius: 0.2 });
    s.addText(st[1], { x: bx, y: 2.98, w: bw, h: 0.4, fontFace: F, fontSize: 11.5, bold: true, color: st[3] === "solid" ? WHITE : (st[3] === "red" ? RED : INK), align: "center", valign: "middle", margin: 0 });
    s.addText(st[2].map((t) => ({ text: t, options: { breakLine: true } })), { x: x + 0.22, y: 3.55, w: w - 0.44, h: 1.9, fontFace: F, fontSize: 12, color: GREY, paraSpaceAfter: 8, lineSpacingMultiple: 1.1, margin: 0 });
    if (i > 0) vline(s, x - 0.15, 2.85, 2.9);
  });
  s.addText("节奏原则：每一步以上一步的公开反馈为输入，先验证「有人愿意看」，再验证「有人愿意付」。", { x: M, y: 5.95, w: 12.33, h: 0.4, fontFace: F, fontSize: 13, color: INK, align: "center", margin: 0 });
  srcLine(s, "「已达成」以仓库当前实现为准；「规划」为承诺目标（招标口径），非当前实现，详见仓库 roadmap");
  pageNum(s, 12);
  s.addNotes("时间轴：黑点=已达成，空心=规划，红点=商业闭环终点。口径诚实标注，防止尽调风险。");
})();

// ============ H13 商业模式 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  hw(s, "四、规划与回报", "开源获客、四层变现，两端定价锚点均已被市场验证");
  const th = (t) => ({ text: t, options: { fill: { color: INK }, color: WHITE, bold: true, fontSize: 12.5, align: "center", valign: "middle", fontFace: F } });
  const n = (t) => ({ text: t, options: { color: RED, bold: true, fontSize: 14, align: "center", valign: "middle", fontFace: F } });
  const c1 = (t) => ({ text: t, options: { color: INK, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const c2 = (t) => ({ text: t, options: { color: INK, fontSize: 12, align: "left", valign: "middle", fontFace: F } });
  const c3 = (t) => ({ text: t, options: { color: GREY, fontSize: 11.5, align: "left", valign: "middle", fontFace: F } });
  s.addTable([
    [th("层级"), th("产品"), th("定价 / 模式"), th("市场锚点")],
    [n("01"), c1("开源核心"), c2("免费 · MIT 自托管"), c3("AIRI 4.9 万 ★ 已验证社区需求")],
    [n("02"), c1("Anima Cloud"), c2("订阅 ¥99–399 / 月"), c3("闪剪 298 元/月；腾讯智影 AI 直播间算力 1 万+/月")],
    [n("03"), c1("形象 · 人格市场"), c2("交易抽成 30%"), c3("Live2D 模型单品市场已是成熟供给")],
    [n("04"), c1("企业方案"), c2("私有化部署 · 客单 10 万+"), c3("硅基智能 2024 年营收 6.55 亿元")]
  ], { x: M, y: 1.78, w: 12.33, colW: [1.0, 2.6, 3.6, 5.13], rowH: [0.5, 0.85, 0.85, 0.85, 0.85], border: { pt: 0.5, color: HAIR }, valign: "middle", margin: 0.06, fontFace: F });
  s.addText("单位经济参照：Character.AI 2025 年收入约 5,000 万美元、AI 陪伴 App 半年消费 8,200 万美元 —— 开源生态占据中间层后，四层收入结构可交叉验证。", { x: M, y: 5.75, w: 12.33, h: 0.65, fontFace: F, fontSize: 13, color: GREY, lineSpacingMultiple: 1.25, margin: 0 });
  redConclusion(s, "结论：先生态、后变现 —— 每一层定价都有现成市场的价格带作为锚点，不赌定价权。", 6.45);
  srcLine(s, "锚点数据来源：GitHub、闪剪 / 腾讯智影公开定价、硅基智能招股书、Business of Apps / Appfigures");
  pageNum(s, 13);
  s.addNotes("四层变现表：层级红字编号，定价与锚点同列对照——华为式「有据定价」。");
})();

// ============ H14 总结：红色字总结（华为胶片结尾） ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText("四、规划与回报 · 总结与建议", { x: M, y: 0.55, w: 9, h: 0.3, fontFace: F, fontSize: 11, bold: true, color: MID, charSpacing: 1, margin: 0 });
  const recap = [
    ["时机", "实时语音与推理成本快速下降，复制 Neuro-sama 的窗口刚刚打开；市场以 30%+ 复合增速扩张"],
    ["卡位", "开源框架无人覆盖「记忆 + 歌唱 + 直播 + 游戏」组合；商业 App 闭源锁定，反向衬托自托管价值"],
    ["壁垒", "企业级工程骨架已就绪；记忆与人格资产随使用持续沉淀，形成数据复利"]
  ];
  recap.forEach((r, i) => {
    const y = 1.35 + i * 0.98;
    s.addText(r[0], { x: M, y, w: 1.0, h: 0.5, fontFace: F, fontSize: 17, bold: true, color: INK, margin: 0 });
    s.addText(r[1], { x: 1.7, y: y + 0.02, w: 11.1, h: 0.85, fontFace: F, fontSize: 13.5, color: GREY, lineSpacingMultiple: 1.25, margin: 0 });
    if (i < 2) hline(s, M, y + 0.82, 12.33);
  });
  hline(s, M, 4.45, 12.33);
  s.addText("总结与建议", { x: M, y: 4.7, w: 4, h: 0.4, fontFace: F, fontSize: 15, bold: true, color: INK, margin: 0 });
  s.addText("建议把握技术成本下降与市场高增的窗口期，投资 Animetta ——\n把下一个 Neuro-sama，交给每个人。", { x: M, y: 5.15, w: 12.33, h: 1.3, fontFace: F, fontSize: 21, bold: true, color: RED, lineSpacingMultiple: 1.35, margin: 0 });
  s.addText("Animetta · 投资汇报 · 2026.09 · 机密", { x: M, y: 7.05, w: 6, h: 0.32, fontFace: F, fontSize: 10.5, color: MID, margin: 0 });
  s.addNotes("华为胶片铁律：结尾红色字总结。前三条黑字回顾（时机/卡位/壁垒），红色建议收尾。");
})();

pres.writeFile({ fileName: "pitch/Animetta-投资人汇报-华为胶片版.pptx" }).then(() => console.log("written"));
