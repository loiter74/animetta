// Animetta 投资人简报 — 13 页，13.33 × 7.5 英寸
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Animetta";
pres.title = "Animetta — 开源全栈 AI 伙伴与虚拟主播框架 · 投资人简报";
pres.subject = "竞品分析与产品卖点";

// ---------- 设计令牌 ----------
const W = 13.33, H = 7.5, M = 0.5;
const DARK = "1A1233";      // 深紫夜色（封面/结尾）
const PANEL = "251A45";     // 深色面板
const PRIMARY = "6D28D9";   // 主紫
const P_MID = "8B5CF6";
const P_SOFT = "C4B5FD";
const TINT = "F4F0FE";      // 极浅紫卡片
const TINT2 = "EDE9FE";     // 浅紫横带
const ACCENT = "EC4899";    // 品红点缀（5-10%）
const ACCENT_D = "BE185D";
const TEXT = "231A3C";
const MUTED = "6E6685";
const LINE_L = "DDD6FE";
const WHITE = "FFFFFF";
const MUTED_D = "A79FC4";   // 深底上的次要文字

const F = "微软雅黑";
const TOTAL = 13;

// ---------- 通用元素 ----------
function header(s, kick, titleTxt, titleSize) {
  s.addText(kick, { x: M, y: 0.42, w: 9, h: 0.32, fontFace: F, fontSize: 12.5, bold: true, color: PRIMARY, charSpacing: 1.5, margin: 0 });
  s.addText(titleTxt, { x: M, y: 0.74, w: W - 2 * M, h: 0.72, fontFace: F, fontSize: titleSize || 28, bold: true, color: TEXT, margin: 0 });
}
function pageNum(s, n) {
  s.addText(`${String(n).padStart(2, "0")} / ${TOTAL}`, { x: 11.9, y: 7.1, w: 0.95, h: 0.3, fontFace: F, fontSize: 10.5, color: MUTED, align: "right", margin: 0 });
}
function srcLine(s, txt) {
  s.addText(txt, { x: M, y: 6.98, w: 11.2, h: 0.48, fontFace: F, fontSize: 10, color: MUTED, valign: "top", margin: 0 });
}
function card(s, x, y, w, h, fill, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: line ? { color: line, width: 1 } : { type: "none" }, rectRadius: 0.09 });
}
function deco(s) { // 封面/结尾的柔和圆
  s.addShape(pres.shapes.OVAL, { x: 9.3, y: -2.4, w: 6.2, h: 6.2, fill: { color: PRIMARY, transparency: 84 }, line: { type: "none" } });
  s.addShape(pres.shapes.OVAL, { x: 10.9, y: 3.9, w: 4.6, h: 4.6, fill: { color: ACCENT, transparency: 88 }, line: { type: "none" } });
  s.addShape(pres.shapes.OVAL, { x: 8.55, y: 5.55, w: 1.15, h: 1.15, fill: { color: P_MID, transparency: 66 }, line: { type: "none" } });
  s.addShape(pres.shapes.OVAL, { x: -1.3, y: 5.7, w: 3.4, h: 3.4, fill: { color: P_MID, transparency: 88 }, line: { type: "none" } });
}

// ============ S1 封面 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: DARK };
  deco(s);
  s.addText("投资人简报 · 2026 年 9 月", { x: M, y: 1.95, w: 8, h: 0.4, fontFace: F, fontSize: 15, color: MUTED_D, charSpacing: 2, margin: 0 });
  s.addText("Animetta", { x: M, y: 2.35, w: 10.5, h: 1.15, fontFace: F, fontSize: 64, bold: true, color: WHITE, margin: 0 });
  s.addText("开源全栈 AI 伙伴与虚拟主播框架", { x: M, y: 3.62, w: 10, h: 0.62, fontFace: F, fontSize: 26, bold: true, color: P_SOFT, margin: 0 });
  s.addText("会说 · 会听 · 会唱 · 会播 · 会玩 —— 把下一个 Neuro-sama 交给每个人", { x: M, y: 4.42, w: 9.6, h: 0.42, fontFace: F, fontSize: 16, color: MUTED_D, margin: 0 });
  const chips = ["LangGraph 状态图编排", "混合记忆 · 数据主权", "开源自托管"];
  chips.forEach((t, i) => {
    const x = M + i * 2.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.35, w: 2.55, h: 0.52, fill: { color: PANEL }, line: { color: "4C3A7A", width: 1 }, rectRadius: 0.26 });
    s.addText(t, { x, y: 5.35, w: 2.55, h: 0.52, fontFace: F, fontSize: 13, color: P_SOFT, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("Confidential · 仅供交流使用", { x: M, y: 6.95, w: 5, h: 0.3, fontFace: F, fontSize: 10.5, color: "6A5F92", margin: 0 });
  s.addNotes("开场：Animetta 是一个开源的全栈 AI 伙伴框架——不只是聊天机器人，而是能听、能说、能唱、能直播、能玩游戏的虚拟主播。今天用 13 页讲清：市场、竞品、我们的卡位与变现路径。");
})();

// ============ S2 市场机会 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "01 · 市场机会", "AI 陪伴：本轮 AI 应用中增速最快的赛道之一", 28);
  s.addText("全球 AI 陪伴市场规模（亿美元）", { x: M, y: 1.62, w: 6.6, h: 0.34, fontFace: F, fontSize: 14, bold: true, color: TEXT, margin: 0 });
  s.addChart(pres.charts.BAR, [{
    name: "市场规模", labels: ["2024", "2025", "2030E", "2033E"], values: [28.2, 36.8, 140.8, 318.0]
  }], {
    x: M, y: 2.05, w: 6.6, h: 4.55, barDir: "col", barGapWidthPct: 45,
    varyColors: true, chartColors: [P_SOFT, P_MID, PRIMARY, ACCENT],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: TEXT, dataLabelFontSize: 11.5, dataLabelFontFace: F, dataLabelFormatCode: "#,##0.#",
    catAxisLabelColor: TEXT, catAxisLabelFontSize: 12, catAxisLabelFontFace: F, catAxisLabelFontBold: true,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false, chartArea: { fill: { color: WHITE } }
  });
  const stats = [
    ["30.8%", "全球 AI 陪伴市场年复合增速（2024–2030）", PRIMARY],
    ["480.6 亿元", "2025 年中国虚拟数字人核心市场规模（带动市场 6,402.7 亿元）", PRIMARY],
    ["+64%", "2025 上半年 AI 陪伴 App 消费支出同比（8,200 万美元）", ACCENT]
  ];
  stats.forEach((st, i) => {
    const y = 1.95 + i * 1.64;
    card(s, 7.5, y, 5.33, 1.46, TINT);
    s.addText(st[0], { x: 7.72, y: y + 0.06, w: 2.15, h: 1.34, fontFace: F, fontSize: st[0].length > 6 ? 26 : 34, bold: true, color: st[2], valign: "middle", margin: 0 });
    s.addText(st[1], { x: 9.9, y: y + 0.06, w: 2.8, h: 1.34, fontFace: F, fontSize: 12, color: TEXT, valign: "middle", margin: 0 });
  });
  srcLine(s, "来源：Grand View Research（2024–2030 及 2026 年更新版预测）；艾媒咨询《中国虚拟数字人产业白皮书》；Appfigures（2025-08）");
  pageNum(s, 2);
  s.addNotes("三个数字：全球市场 5-9 年 10 倍、中国虚拟数字人百亿级、App 消费同比 +64%。要点：这不是概念市场，付费行为已经发生。");
})();

// ============ S3 天花板验证 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "02 · 天花板验证", "Neuro-sama：AI 主播已登顶 Twitch", 30);
  const cards3 = [
    ["No.1", "Twitch 全站订阅第一频道\n16.2 万活跃订阅 · 2026-01\n超越全部真人主播", ACCENT],
    ["45,605", "单场直播峰值观众\nAI VTuber 纪录 · 2025-01", PRIMARY],
    ["26.2 万", "第三次 Subathon 活动\n累计付费订阅 · 打赏验证", PRIMARY],
    ["4.09 亿", "YouTube 累计播放\n91.6 万订阅 · 切片二次传播", PRIMARY]
  ];
  cards3.forEach((c, i) => {
    const x = M + i * 3.16, w = 2.86;
    card(s, x, 1.72, w, 2.35, TINT);
    s.addText(c[0], { x: x + 0.22, y: 1.95, w: w - 0.44, h: 0.75, fontFace: F, fontSize: 36, bold: true, color: c[2], margin: 0 });
    s.addText(c[1], { x: x + 0.22, y: 2.78, w: w - 0.44, h: 1.15, fontFace: F, fontSize: 11.5, color: TEXT, lineSpacingMultiple: 1.25, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 4.38, w: W, h: 1.42, fill: { color: TINT2 }, line: { type: "none" } });
  s.addText([
    { text: "一个开发者 + 一套自研框架 = 头部真人主播的产能。", options: { bold: true, fontSize: 15.5, color: TEXT, breakLine: true } },
    { text: "Neuro-sama 由 Vedal 近乎独立运营，完整验证了「AI 主播」的订阅、打赏与内容传播商业闭环——Animetta 要把这条被验证的路径产品化，交给每一位创作者。", options: { fontSize: 13, color: MUTED } }
  ], { x: 0.9, y: 4.5, w: 11.6, h: 1.2, fontFace: F, valign: "middle", paraSpaceAfter: 6, margin: 0 });
  s.addText("天花板已被验证，稀缺的是「人人可用」的框架。", { x: M, y: 6.05, w: 12.33, h: 0.5, fontFace: F, fontSize: 17, bold: true, color: PRIMARY, align: "center", margin: 0 });
  srcLine(s, "来源：Twitch / Streams Charts；Netinfluencer、Tubefilter（2026-01）；Social Blade（2026-09）");
  pageNum(s, 3);
  s.addNotes("Neuro-sama 是赛道的天花板证据：Twitch 订阅第一、单场 4.5 万观众。关键信息：它是闭源的、单人设的——没有人能把这种能力产品化，这是我们的机会。");
})();

// ============ S4 竞争格局 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "03 · 竞争格局", "四类玩家，无人占据「开源自托管 × 全栈交互」", 28);
  // 坐标轴
  s.addShape(pres.shapes.LINE, { x: 1.55, y: 4.05, w: 7.35, h: 0, line: { color: LINE_L, width: 1.5, endArrowType: "triangle" } });
  s.addShape(pres.shapes.LINE, { x: 5.2, y: 1.72, w: 0, h: 4.78, line: { color: LINE_L, width: 1.5, beginArrowType: "triangle" } });
  s.addText("闭源 SaaS", { x: 1.55, y: 6.58, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });
  s.addText("开源自托管", { x: 7.3, y: 6.58, w: 1.6, h: 0.3, fontFace: F, fontSize: 11.5, bold: true, color: PRIMARY, align: "right", margin: 0 });
  s.addText("纯对话  ⟶  全栈具身交互（唱 · 播 · 玩）", { x: -0.75, y: 3.9, w: 2.9, h: 0.32, fontFace: F, fontSize: 11, color: MUTED, align: "center", rotate: 270, margin: 0 });
  // 象限条目
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.4, y: 2.12, w: 2.3, h: 1.12, fill: { color: PRIMARY }, line: { color: ACCENT, width: 1.5 }, rectRadius: 0.09, shadow: { type: "outer", color: "6D28D9", blur: 8, offset: 2, angle: 45, opacity: 0.3 } });
  s.addText([
    { text: "Animetta", options: { fontSize: 16, bold: true, color: WHITE, breakLine: true } },
    { text: "开源自托管 · 五项全栈", options: { fontSize: 11, color: TINT2 } }
  ], { x: 6.4, y: 2.12, w: 2.3, h: 1.12, fontFace: F, align: "center", valign: "middle", margin: 0 });
  card(s, 2.0, 2.12, 2.5, 0.95, WHITE, LINE_L);
  s.addText([
    { text: "Neuro-sama", options: { fontSize: 13.5, bold: true, color: TEXT, breakLine: true } },
    { text: "闭源 · 单人设 · Twitch", options: { fontSize: 11, color: MUTED } }
  ], { x: 2.0, y: 2.12, w: 2.5, h: 0.95, fontFace: F, align: "center", valign: "middle", margin: 0 });
  card(s, 5.95, 4.4, 2.85, 1.32, WHITE, LINE_L);
  s.addText([
    { text: "AIRI · 4.9 万 ★", options: { fontSize: 11.5, color: TEXT, breakLine: true } },
    { text: "Open-LLM-VTuber · 1.4 万 ★", options: { fontSize: 11.5, color: TEXT, breakLine: true } },
    { text: "Amica · 0.2 万 ★（停更）", options: { fontSize: 11.5, color: MUTED } }
  ], { x: 6.1, y: 4.48, w: 2.6, h: 1.16, fontFace: F, valign: "middle", paraSpaceAfter: 4, margin: 0 });
  card(s, 1.7, 4.3, 3.05, 0.95, WHITE, LINE_L);
  s.addText([
    { text: "Character.AI · Replika", options: { fontSize: 11.5, color: TEXT, breakLine: true } },
    { text: "星野 · 猫箱 · X Eva", options: { fontSize: 11.5, color: TEXT } }
  ], { x: 1.7, y: 4.3, w: 3.05, h: 0.95, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  card(s, 1.7, 5.42, 3.05, 0.85, WHITE, LINE_L);
  s.addText([
    { text: "硅基智能 · 腾讯智影", options: { fontSize: 11.5, color: TEXT, breakLine: true } },
    { text: "B 端播报型 · 非实时交互", options: { fontSize: 11, color: MUTED } }
  ], { x: 1.7, y: 5.42, w: 3.05, h: 0.85, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  // 右侧结论列
  s.addText("为什么右上象限空缺", { x: 9.35, y: 1.72, w: 3.48, h: 0.4, fontFace: F, fontSize: 15, bold: true, color: TEXT, margin: 0 });
  const why = [
    ["闭源 App", "体验好，但记忆与关系锁死在云端，用户无法带走"],
    ["开源框架", "可自托管，却止步于「桌面聊天」，缺直播与歌唱"],
    ["B 端数字人", "念稿播报为主，不是能对话的实时智能体"]
  ];
  why.forEach((r, i) => {
    const y = 2.25 + i * 1.16;
    s.addShape(pres.shapes.OVAL, { x: 9.38, y: y + 0.07, w: 0.14, h: 0.14, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText([
      { text: r[0], options: { fontSize: 13.5, bold: true, color: TEXT, breakLine: true } },
      { text: r[1], options: { fontSize: 11.5, color: MUTED } }
    ], { x: 9.66, y, w: 3.2, h: 1.05, fontFace: F, paraSpaceAfter: 4, lineSpacingMultiple: 1.15, margin: 0 });
  });
  card(s, 9.35, 5.9, 3.48, 0.62, DARK);
  s.addText("右上象限 = Animetta 独占卡位", { x: 9.35, y: 5.9, w: 3.48, h: 0.62, fontFace: F, fontSize: 13, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  srcLine(s, "★ 为 GitHub 星标数，来源：GitHub API 实测（2026-09-19）；其余为各公司公开资料");
  pageNum(s, 4);
  s.addNotes("横轴：闭源到开源；纵轴：纯对话到全栈交互。四类玩家各占一角，右上——既开源可自托管、又覆盖唱播玩全栈——只有 Animetta。");
})();

// ============ S5 竞品能力矩阵 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "04 · 竞品对比", "「说·听·唱·播·玩」五项能力 × 五类玩家", 28);
  const hdr = (t, animetta) => ({ text: t, options: { fill: { color: animetta ? ACCENT : DARK }, color: WHITE, bold: true, fontSize: animetta ? 12.5 : 11.5, align: "center", valign: "middle", fontFace: F } });
  const lab = (t) => ({ text: t, options: { fill: { color: "FAF9FE" }, color: TEXT, bold: true, fontSize: 12.5, align: "left", valign: "middle", fontFace: F } });
  const ok = (t) => ({ text: t, options: { color: PRIMARY, bold: true, fontSize: 11.5, align: "center", valign: "middle", fontFace: F } });
  const mid = (t) => ({ text: t || "部分", options: { color: MUTED, fontSize: 11, align: "center", valign: "middle", fontFace: F } });
  const no = { text: "—", options: { color: "B9B3CC", fontSize: 11.5, align: "center", valign: "middle", fontFace: F } };
  const aok = (t) => ({ text: t, options: { fill: { color: "FCE7F3" }, color: ACCENT_D, bold: true, fontSize: 11.5, align: "center", valign: "middle", fontFace: F } });
  const am = (t) => ({ text: t, options: { fill: { color: "FCE7F3" }, color: ACCENT_D, fontSize: 11, align: "center", valign: "middle", fontFace: F } });
  const rows = [
    [hdr("能力维度"), hdr("Neuro-sama"), hdr("AIRI"), hdr("Open-LLM-VTuber"), hdr("商业陪伴 App"), hdr("B 端数字人"), hdr("Animetta", true)],
    [lab("实时语音对话"), ok("✓"), ok("✓"), ok("✓"), ok("✓"), mid("念稿播报"), aok("✓ 可打断")],
    [lab("Live2D / 虚拟形象"), ok("✓ Live2D"), ok("✓ VRM"), ok("✓ Live2D"), mid("2D 头像"), ok("✓ 视频分身"), aok("✓ Live2D")],
    [lab("长期记忆"), mid(), no, mid("会话级"), ok("✓ 锁在云端"), no, aok("✓ 混合检索")],
    [lab("AI 歌唱"), ok("✓"), no, no, mid("少数内置"), no, aok("✓ RVC 声线")],
    [lab("直播实时互动"), ok("✓ Twitch"), no, no, no, mid("带货话术"), aok("✓ B 站弹幕")],
    [lab("游戏游玩"), ok("✓"), ok("✓ MC"), no, no, no, aok("✓ MC")],
    [lab("开源自托管"), no, ok("✓"), ok("✓"), no, no, aok("✓")]
  ];
  s.addTable(rows, {
    x: M, y: 1.68, w: 12.33, colW: [2.3, 1.55, 1.55, 1.85, 1.85, 1.75, 1.48],
    rowH: [0.6, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55],
    border: { pt: 0.5, color: "E5E0F2" }, valign: "middle", margin: 0.04, fontFace: F
  });
  srcLine(s, "✓ 支持 · 部分 = 有限支持 · — 不支持。Animetta 的歌唱与游戏为原型级能力（见 P10 路线图）。来源：各项目 GitHub 仓库与官方产品页（2026-09）");
  pageNum(s, 5);
  s.addNotes("矩阵结论：Neuro-sama 能力最全但闭源单人设；开源框架止步于语音对话；商业 App 的记忆锁在云端。唯一全绿的一列是 Animetta。");
})();

// ============ S6 付费意愿 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "05 · 付费意愿", "C 端千万级用户，B 端亿元级营收", 30);
  s.addText("头部 AI 陪伴产品月活（百万，2025）", { x: M, y: 1.66, w: 6.3, h: 0.34, fontFace: F, fontSize: 14, bold: true, color: TEXT, margin: 0 });
  s.addChart(pres.charts.BAR, [{
    name: "月活", labels: ["猫箱", "Talkie+星野", "Replika", "Character.AI"], values: [4.5, 20.1, 40, 45]
  }], {
    x: M, y: 2.1, w: 6.3, h: 4.4, barDir: "bar", barGapWidthPct: 50,
    varyColors: true, chartColors: [LINE_L, P_SOFT, P_MID, ACCENT],
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: TEXT, dataLabelFontSize: 11.5, dataLabelFontFace: F, dataLabelFormatCode: "#,##0.#",
    catAxisLabelColor: TEXT, catAxisLabelFontSize: 12.5, catAxisLabelFontFace: F, catAxisLabelFontBold: true,
    valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    showLegend: false, showTitle: false, chartArea: { fill: { color: WHITE } }
  });
  const facts = [
    ["Character.AI", "2025 年收入约 5,000 万美元（+66%），获 Google 约 27 亿美元技术授权"],
    ["小冰公司", "投后估值约 20 亿美元，2024 年以 140 亿元列胡润独角兽榜"],
    ["硅基智能", "数字人营收 2022 年 2.23 亿 → 2024 年 6.55 亿元，两年近 3 倍，已递交港股招股书"],
    ["定价锚点", "闪剪直播带货 2,980 元 / 年；腾讯智影 2,000 元 / 形象、AI 直播间算力 1 万+ / 月"]
  ];
  facts.forEach((r, i) => {
    const y = 1.9 + i * 1.18;
    s.addShape(pres.shapes.OVAL, { x: 7.4, y: y + 0.09, w: 0.14, h: 0.14, fill: { color: PRIMARY }, line: { type: "none" } });
    s.addText([
      { text: r[0], options: { fontSize: 14, bold: true, color: TEXT, breakLine: true } },
      { text: r[1], options: { fontSize: 12, color: MUTED } }
    ], { x: 7.68, y, w: 5.1, h: 1.05, fontFace: F, paraSpaceAfter: 4, lineSpacingMultiple: 1.2, margin: 0 });
    if (i < 3) s.addShape(pres.shapes.LINE, { x: 7.4, y: y + 1.06, w: 5.38, h: 0, line: { color: "EDE9FE", width: 0.75 } });
  });
  srcLine(s, "来源：Business of Apps / WSJ；财新、胡润研究院；硅基智能招股书（财联社）；MiniMax 招股书（虎嗅转述）；点点数据（2024–2026）");
  pageNum(s, 6);
  s.addNotes("左图证明 C 端规模：四款产品月活都是百万到千万级。右侧证明两件事：用户在付费（Character.AI 5,000 万美元年收入）、企业在付费（硅基智能 6.55 亿元营收、腾讯智影万元级月费）。");
})();

// ============ S7 产品架构 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "06 · 产品", "一套 LangGraph 状态图编排的全栈 AI 伙伴框架", 28);
  s.addText("从观众输入到三路实时输出 —— 链路每一步可插拔、可观测", { x: M, y: 1.52, w: 11, h: 0.36, fontFace: F, fontSize: 13.5, color: MUTED, margin: 0 });
  const chain = [
    ["ASR 语音识别", 2.25, 1.6],
    ["人格 · 记忆注入", 4.15, 1.75],
    ["LLM 推理", 6.25, 1.45],
    ["情感理解", 8.05, 1.45]
  ];
  // 输入
  card(s, 0.5, 3.15, 1.45, 1.3, DARK);
  s.addText([
    { text: "观众", options: { fontSize: 15, bold: true, color: WHITE, breakLine: true } },
    { text: "语音 · 弹幕", options: { fontSize: 11, color: MUTED_D } }
  ], { x: 0.5, y: 3.15, w: 1.45, h: 1.3, fontFace: F, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 1.97, y: 3.8, w: 0.25, h: 0, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
  // 链路
  chain.forEach((b) => {
    card(s, b[1], 3.3, b[2], 1.0, TINT, LINE_L);
    s.addText(b[0], { x: b[1], y: 3.3, w: b[2], h: 1.0, fontFace: F, fontSize: 13, bold: true, color: TEXT, align: "center", valign: "middle", margin: 0 });
  });
  const gaps = [[3.87, 4.12], [5.92, 6.17], [7.72, 7.97]];
  gaps.forEach((g) => s.addShape(pres.shapes.LINE, { x: g[0], y: 3.8, w: g[1] - g[0], h: 0, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } }));
  // 分流到输出
  s.addShape(pres.shapes.LINE, { x: 9.5, y: 3.8, w: 0.22, h: 0, line: { color: P_SOFT, width: 1.75 } });
  s.addShape(pres.shapes.LINE, { x: 9.72, y: 2.75, w: 0, h: 2.1, line: { color: P_SOFT, width: 1.75 } });
  const outs = [
    ["Live2D 表情动作", 2.3, TINT, TEXT, LINE_L],
    ["TTS 语音 · RVC 歌声", 3.35, TINT, TEXT, LINE_L],
    ["工具调用：Minecraft · 直播互动", 4.4, PRIMARY, WHITE, null]
  ];
  outs.forEach((o) => {
    const yc = o[1] + 0.45;
    s.addShape(pres.shapes.LINE, { x: 9.72, y: yc, w: 0.26, h: 0, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
    card(s, 10.0, o[1], 2.83, 0.9, o[2], o[4]);
    s.addText(o[0], { x: 10.08, y: o[1], w: 2.67, h: 0.9, fontFace: F, fontSize: o[0].length > 12 ? 11.5 : 12.5, bold: true, color: o[3], align: "center", valign: "middle", margin: 0 });
  });
  // 平台条
  const plat = [
    ["前端", "Vue 3 · Electron · Live2D"],
    ["实时通道", "Socket.IO 实时会话"],
    ["Provider 插件制", "LLM / ASR / TTS / VAD 一键切换"],
    ["可观测", "OTel · Prometheus · Stats 面板"]
  ];
  plat.forEach((p, i) => {
    const x = M + i * 3.13, w = 2.94;
    card(s, x, 5.55, w, 1.0, TINT);
    s.addText([
      { text: p[0], options: { fontSize: 12.5, bold: true, color: PRIMARY, breakLine: true } },
      { text: p[1], options: { fontSize: 11, color: MUTED } }
    ], { x: x + 0.18, y: 5.63, w: w - 0.36, h: 0.85, fontFace: F, paraSpaceAfter: 3, margin: 0 });
  });
  srcLine(s, "ASR → 人格 → LLM → 情感 → 输出的编排链路、Provider 插件与记忆系统均已实现并经测试覆盖（11 项 ADR）");
  pageNum(s, 7);
  s.addNotes("产品核心是一条 LangGraph 状态图：观众语音或弹幕进来，经过 ASR、人格与记忆注入、LLM 推理、情感理解，同时驱动 Live2D 表情、语音歌声、工具调用三路输出。底层四大平台能力都是插件化的。");
})();

// ============ S8 卖点一：全栈 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "07 · 卖点一 · 全栈", "说·听·唱·播·玩 五项一体，竞品平均覆盖不到两项", 27);
  const caps = [
    ["说", "多模型大脑", "DeepSeek / Qwen / MIMO\nProvider 插件化切换"],
    ["听", "实时听觉", "流式 ASR 识别\n用户可随时打断"],
    ["唱", "AI 歌唱", "RVC 声线推理\n弹幕点歌开唱（原型）"],
    ["播", "直播营业", "B 站弹幕实时互动\nOBS 推流直播"],
    ["玩", "自主游玩", "Minecraft 世界交互\n弹幕点名互动（原型）"]
  ];
  caps.forEach((c, i) => {
    const x = M + i * 2.52, w = 2.27;
    card(s, x, 1.72, w, 3.55, TINT);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.2, y: 1.98, w: 0.66, h: 0.66, fill: { color: i === 4 ? ACCENT : PRIMARY }, line: { type: "none" }, rectRadius: 0.12 });
    s.addText(c[0], { x: x + 0.2, y: 1.98, w: 0.66, h: 0.66, fontFace: F, fontSize: 22, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(c[1], { x: x + 0.2, y: 2.85, w: w - 0.4, h: 0.4, fontFace: F, fontSize: 15.5, bold: true, color: TEXT, margin: 0 });
    s.addText(c[2], { x: x + 0.2, y: 3.32, w: w - 0.4, h: 1.7, fontFace: F, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.3, margin: 0 });
  });
  s.addText("五项能力覆盖对比（● 支持）", { x: M, y: 5.52, w: 6, h: 0.32, fontFace: F, fontSize: 12, bold: true, color: TEXT, margin: 0 });
  const cov = [
    ["AIRI", "●●●○○", 3, TEXT],
    ["Open-LLM-VTuber", "●●○○○", 2, TEXT],
    ["商业陪伴 App", "●●○○○", 2, TEXT],
    ["Animetta", "●●●●●", 5, ACCENT_D]
  ];
  cov.forEach((r, i) => {
    const x = M + i * 3.13, w = 2.94;
    s.addText(`${r[0]}  ${r[1]}  ${r[2]}/5`, { x, y: 5.9, w, h: 0.42, fontFace: F, fontSize: 12.5, bold: true, color: r[3], valign: "middle", margin: 0 });
  });
  card(s, M, 6.42, 12.33, 0.52, TINT2);
  s.addText("一体化意味着同一个记忆与人格贯穿所有场景：她昨天陪你聊的天，今天会在直播里记得，唱歌时也用同一个声音。", { x: 0.8, y: 6.42, w: 11.8, h: 0.52, fontFace: F, fontSize: 12.5, color: TEXT, valign: "middle", margin: 0 });
  srcLine(s, "覆盖统计口径见上页矩阵；Animetta 歌唱与游玩为原型级链路，进入稳定性打磨阶段");
  pageNum(s, 8);
  s.addNotes("卖点一：全栈。五项能力不是五个功能，而是同一个体。竞品对比：AIRI 3 项、OLV 和商业 App 各 2 项。");
})();

// ============ S9 卖点二：记忆 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "08 · 卖点二 · 记忆", "混合记忆：越相处越懂你，数据归用户所有", 28);
  card(s, 2.55, 1.66, 2.5, 0.5, WHITE, LINE_L);
  s.addText("每一轮对话", { x: 2.55, y: 1.66, w: 2.5, h: 0.5, fontFace: F, fontSize: 12.5, color: MUTED, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 2.16, w: 0, h: 0.24, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
  const stores = [
    ["Chroma 向量库", "语义记忆", 0.5],
    ["SQLite FTS5", "关键词记忆", 3.0],
    ["Markdown Wiki", "人格档案 · 兴趣画像", 5.5]
  ];
  stores.forEach((st) => {
    card(s, st[2], 2.44, 2.2, 1.1, TINT);
    s.addText([
      { text: st[0], options: { fontSize: 13, bold: true, color: TEXT, breakLine: true } },
      { text: st[1], options: { fontSize: 11, color: MUTED } }
    ], { x: st[2] + 0.15, y: 2.44, w: 1.9, h: 1.1, fontFace: F, align: "center", valign: "middle", paraSpaceAfter: 3, margin: 0 });
  });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 3.54, w: 0, h: 0.24, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
  card(s, 0.5, 3.82, 7.2, 0.68, WHITE, LINE_L);
  s.addText("B 站梗库 —— 流行梗与直播语境持续学习（ADR-010）", { x: 0.5, y: 3.82, w: 7.2, h: 0.68, fontFace: F, fontSize: 12.5, color: TEXT, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 4.5, w: 0, h: 0.24, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 4.78, w: 7.2, h: 0.75, fill: { color: PRIMARY }, line: { type: "none" }, rectRadius: 0.09 });
  s.addText("检索融合 · 向量 70% + 关键词 30% 混合权重", { x: 0.5, y: 4.78, w: 7.2, h: 0.75, fontFace: F, fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.LINE, { x: 3.8, y: 5.53, w: 0, h: 0.24, line: { color: P_SOFT, width: 1.75, endArrowType: "triangle" } });
  card(s, 0.5, 5.81, 7.2, 0.75, WHITE, ACCENT);
  s.addText("注入下一轮对话 —— 她记得你说过的每一句话", { x: 0.5, y: 5.81, w: 7.2, h: 0.75, fontFace: F, fontSize: 13.5, bold: true, color: ACCENT_D, align: "center", valign: "middle", margin: 0 });
  // 右侧价值
  const vals = [
    ["数据主权", "商业 App 的记忆锁死在云端、无法迁移；自托管让用户真正拥有这段「关系」"],
    ["召回质量", "向量 + 关键词混合检索（ADR-002），比单一向量记忆召回更准"],
    ["人格一致", "Wiki 档案 + 梗库让角色不失忆、不变脸（ADR-005 / 010），长期陪伴成立"]
  ];
  vals.forEach((v, i) => {
    const y = 1.78 + i * 1.62;
    s.addText([
      { text: v[0], options: { fontSize: 14.5, bold: true, color: PRIMARY, breakLine: true } },
      { text: v[1], options: { fontSize: 12, color: TEXT } }
    ], { x: 8.1, y, w: 4.75, h: 1.45, fontFace: F, paraSpaceAfter: 5, lineSpacingMultiple: 1.25, margin: 0 });
    if (i < 2) s.addShape(pres.shapes.LINE, { x: 8.1, y: y + 1.44, w: 4.73, h: 0, line: { color: "EDE9FE", width: 0.75 } });
  });
  srcLine(s, "混合权重 70/30 为默认配置，可调；架构见仓库 ADR-002 / ADR-005 / ADR-010");
  pageNum(s, 9);
  s.addNotes("卖点二：记忆是关系的资产。三层存储 + 梗库，混合检索注入每轮对话。对用户：数据在自己手里；对平台：记忆资产形成迁移成本与复利。");
})();

// ============ S10 卖点三：工程 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "09 · 卖点三 · 工程", "个人产品的体验，企业工程的骨架", 30);
  const stats10 = [
    ["11 项", "架构决策记录（ADR）"],
    ["15 个", "架构分层模块"],
    ["63 个", "LangGraph 编排图节点"],
    ["OTel", "全链路分布式追踪"]
  ];
  stats10.forEach((st, i) => {
    const x = M + i * 3.13, w = 2.94;
    card(s, x, 1.7, w, 1.5, TINT);
    s.addText(st[0], { x: x + 0.2, y: 1.85, w: w - 0.4, h: 0.62, fontFace: F, fontSize: 30, bold: true, color: PRIMARY, margin: 0 });
    s.addText(st[1], { x: x + 0.2, y: 2.52, w: w - 0.4, h: 0.55, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
  });
  const feats = [
    ["Provider 注册制", "interface → 实现 → 工厂 → 导出，新增模型供应商零侵入核心代码"],
    ["影响感知验证", "tooling.quality 按改动范围自动圈定测试组，重构有安全网"],
    ["可观测栈", "OTel 追踪 + Prometheus 指标 + Stats 面板，线上问题分钟级定位"],
    ["一键部署", "Docker Compose / Zeabur，个人版一条命令拉起全栈"]
  ];
  feats.forEach((f, i) => {
    const x = M + i * 3.13, w = 2.94;
    card(s, x, 3.45, w, 2.0, WHITE, LINE_L);
    s.addText(f[0], { x: x + 0.2, y: 3.65, w: w - 0.4, h: 0.4, fontFace: F, fontSize: 14.5, bold: true, color: TEXT, margin: 0 });
    s.addText(f[1], { x: x + 0.2, y: 4.12, w: w - 0.4, h: 1.2, fontFace: F, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.3, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.75, w: W, h: 1.0, fill: { color: TINT2 }, line: { type: "none" } });
  s.addText("商业化是在就绪的骨架上叠加功能，而不是推倒重构 —— 这是小团队做大产品的唯一路径。", { x: 0.9, y: 5.75, w: 11.6, h: 1.0, fontFace: F, fontSize: 15.5, bold: true, color: TEXT, align: "center", valign: "middle", margin: 0 });
  srcLine(s, "数据来源：仓库 docs/adrs/（11 项 ADR）、架构知识图谱统计（15 分层 / 63 编排节点）、tooling/quality 组件映射");
  pageNum(s, 10);
  s.addNotes("卖点三：工程化。这套仓库不是 demo 代码——11 项 ADR、影响感知测试、全链路可观测。意味着商业化是叠加而非重构，融资的钱花在产品上而不是还债上。");
})();

// ============ S11 路线图 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "10 · 路线图", "从开源原型到商业闭环", 30);
  s.addShape(pres.shapes.LINE, { x: 0.9, y: 2.32, w: 11.5, h: 0, line: { color: LINE_L, width: 2, endArrowType: "triangle" } });
  const stages = [
    ["2026 Q3", "已达成", ["语音对话全链路闭环", "B 站直播与弹幕接入", "混合记忆 v2 落地", "歌唱 · Minecraft 原型跑通"], true],
    ["2026 Q4", "规划", ["公开测试直播 30 分钟不中断", "沉淀 10 条传播切片", "观众反馈驱动人格迭代"], false],
    ["2027 H1", "规划", ["Anima Cloud 云托管 Beta", "形象 · 人格市场上线", "抖音 / YouTube 多平台"], false],
    ["2027 H2", "规划", ["企业虚拟主播私有化部署", "MCN 内容合作与分成", "（目标承诺，非当前实现）"], false]
  ];
  stages.forEach((st, i) => {
    const x = M + i * 3.16, w = 2.86, cx = x + w / 2;
    s.addShape(pres.shapes.OVAL, { x: cx - 0.14, y: 2.18, w: 0.28, h: 0.28, fill: { color: i === 0 ? PRIMARY : (i === 3 ? ACCENT : WHITE) }, line: { color: i === 0 ? PRIMARY : (i === 3 ? ACCENT : P_MID), width: 2 } });
    s.addText(st[0], { x, y: 1.62, w, h: 0.42, fontFace: F, fontSize: 16, bold: true, color: TEXT, align: "center", margin: 0 });
    card(s, x, 2.75, w, 2.85, i === 0 ? TINT : WHITE, i === 0 ? null : LINE_L);
    const bw = 0.95, bx = x + 0.22;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: 2.98, w: bw, h: 0.4, fill: { color: i === 0 ? PRIMARY : WHITE }, line: i === 0 ? { type: "none" } : { color: P_MID, width: 1 }, rectRadius: 0.2 });
    s.addText(st[1], { x: bx, y: 2.98, w: bw, h: 0.4, fontFace: F, fontSize: 11.5, bold: true, color: i === 0 ? WHITE : PRIMARY, align: "center", valign: "middle", margin: 0 });
    s.addText(st[2].map((t, j) => ({ text: t, options: { breakLine: true } })), { x: x + 0.22, y: 3.55, w: w - 0.44, h: 1.9, fontFace: F, fontSize: 12, color: TEXT, paraSpaceAfter: 8, lineSpacingMultiple: 1.1, margin: 0 });
  });
  s.addText("四阶段节奏：先验证「有人愿意看」，再验证「有人愿意付」——每一步都以开源社区的反馈为输入。", { x: M, y: 5.95, w: 12.33, h: 0.45, fontFace: F, fontSize: 13.5, color: MUTED, align: "center", margin: 0 });
  srcLine(s, "「已达成」以仓库当前实现为准；「规划」为承诺目标（招标口径），非当前实现，详见仓库 roadmap");
  pageNum(s, 11);
  s.addNotes("路线图：Q3 已完成全栈原型；Q4 公开直播验证观众；2027 上半年云托管与形象市场开始变现；下半年进企业市场。明确区分已实现与承诺目标，保持可信度。");
})();

// ============ S12 商业模式 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  header(s, "11 · 商业模式", "开源获客，四层变现", 30);
  const biz = [
    ["01", "开源核心", "MIT 协议免费自托管，沉淀开发者生态与信任，作为获客漏斗顶部", "锚点：AIRI 4.9 万 ★ 验证社区需求"],
    ["02", "Anima Cloud", "托管订阅：免配置、常在线、数据可导出，按创作者档位计价", "定价 ¥99–399/月 ｜ 闪剪 298 元/月、智影直播间 1 万+/月"],
    ["03", "形象 · 人格市场", "Live2D 形象 + 人格包交易，创作者经济飞轮，平台抽成 30%", "锚点：Live2D 模型单品市场已是成熟供给"],
    ["04", "企业方案", "虚拟主播 / 数字员工私有化部署，含合规与运维", "客单 10 万+ ｜ 硅基智能 2024 营收 6.55 亿元"]
  ];
  biz.forEach((b, i) => {
    const x = M + i * 3.13, w = 2.94;
    card(s, x, 1.72, w, 3.6, i === 1 ? TINT : WHITE, i === 1 ? null : LINE_L);
    s.addText(b[0], { x: x + 0.2, y: 1.9, w: w - 0.4, h: 0.5, fontFace: F, fontSize: 24, bold: true, color: P_SOFT, margin: 0 });
    s.addText(b[1], { x: x + 0.2, y: 2.45, w: w - 0.4, h: 0.42, fontFace: F, fontSize: 16, bold: true, color: TEXT, margin: 0 });
    s.addText(b[2], { x: x + 0.2, y: 2.95, w: w - 0.4, h: 1.35, fontFace: F, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.3, margin: 0 });
    s.addShape(pres.shapes.LINE, { x: x + 0.2, y: 4.42, w: w - 0.4, h: 0, line: { color: "EDE9FE", width: 0.75 } });
    s.addText(b[3], { x: x + 0.2, y: 4.5, w: w - 0.4, h: 0.72, fontFace: F, fontSize: 10.5, color: PRIMARY, lineSpacingMultiple: 1.2, margin: 0 });
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.62, w: W, h: 1.1, fill: { color: TINT2 }, line: { type: "none" } });
  s.addText("两端市场均已被验证：", { x: 0.9, y: 5.62, w: 2.75, h: 1.1, fontFace: F, fontSize: 14.5, bold: true, color: TEXT, valign: "top", margin: 0.08 });
  s.addText("C 端 Character.AI 年收入约 5,000 万美元、AI 陪伴 App 消费半年 8,200 万美元；B 端硅基智能两年营收近 3 倍。Animetta 以开源占据中间层 —— 先生态，后变现。", { x: 3.7, y: 5.62, w: 8.8, h: 1.1, fontFace: F, fontSize: 13, color: MUTED, valign: "top", lineSpacingMultiple: 1.25, margin: 0.08 });
  srcLine(s, "锚点数据来源：GitHub、闪剪 / 腾讯智影公开定价、硅基智能招股书、Business of Apps / Appfigures");
  pageNum(s, 12);
  s.addNotes("四层变现：免费开源获客 → 云托管订阅（对标闪剪/智影定价，做低门槛档）→ 形象人格市场抽成 → 企业私有化。重点讲第二层的定价锚点：市场已接受每月几百到上万元的价格带。");
})();

// ============ S13 结语 ============
(() => {
  const s = pres.addSlide();
  s.background = { color: DARK };
  deco(s);
  s.addText("12 · 结语", { x: M, y: 0.55, w: 9, h: 0.32, fontFace: F, fontSize: 12.5, bold: true, color: P_SOFT, charSpacing: 1.5, margin: 0 });
  s.addText("为什么是现在，为什么是我们", { x: M, y: 0.95, w: 11, h: 0.8, fontFace: F, fontSize: 36, bold: true, color: WHITE, margin: 0 });
  const rows13 = [
    ["01", "时机", "实时语音与推理成本快速下降，复制 Neuro-sama 的窗口刚刚打开；市场正以 30%+ 复合增速扩张"],
    ["02", "卡位", "开源框架无人覆盖「记忆 + 歌唱 + 直播 + 游戏」组合；商业 App 闭源锁定用户，反向衬托自托管价值"],
    ["03", "壁垒", "企业级工程骨架已就绪；记忆与人格资产随使用持续沉淀，形成数据复利"]
  ];
  rows13.forEach((r, i) => {
    const y = 2.15 + i * 1.28;
    s.addText(r[0], { x: M, y, w: 0.85, h: 0.7, fontFace: F, fontSize: 30, bold: true, color: ACCENT, margin: 0 });
    s.addText(r[1], { x: 1.55, y: y + 0.06, w: 1.0, h: 0.45, fontFace: F, fontSize: 17, bold: true, color: WHITE, margin: 0 });
    s.addText(r[2], { x: 2.65, y: y + 0.05, w: 9.8, h: 1.05, fontFace: F, fontSize: 13.5, color: MUTED_D, valign: "top", lineSpacingMultiple: 1.3, margin: 0 });
  });
  s.addShape(pres.shapes.LINE, { x: M, y: 6.1, w: 7.2, h: 0, line: { color: "4C3A7A", width: 0.75 } });
  s.addText("把下一个 Neuro-sama，交给每个人。", { x: M, y: 6.3, w: 9.5, h: 0.6, fontFace: F, fontSize: 24, bold: true, color: WHITE, margin: 0 });
  s.addText("Animetta · 投资人简报 · 2026.09", { x: M, y: 6.98, w: 6, h: 0.32, fontFace: F, fontSize: 11.5, color: "6A5F92", margin: 0 });
  s.addNotes("收尾三句话：时机（成本下降+市场增速）、卡位（开源全栈空档）、壁垒（工程骨架+数据复利）。CTA：把下一个 Neuro-sama 交给每个人。");
})();

pres.writeFile({ fileName: "pitch/Animetta-投资人简报.pptx" }).then(() => console.log("written"));
