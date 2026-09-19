# -*- coding: utf-8 -*-
"""Deck QA: XML 段落合法性 / 文本溢出估算 / 越界与重叠检查"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pptx import Presentation
from pptx.util import Emu
import zipfile, re

PATH = r"pitch/Animetta-投资人简报.pptx"

# 1) 同一 <a:p> 内多个 <a:pPr>（pptxgenjs 混排陷阱）
bad_ppr = []
with zipfile.ZipFile(PATH) as z:
    for n in z.namelist():
        if re.match(r"ppt/slides/slide\d+\.xml$", n):
            xml = z.read(n).decode("utf-8")
            for m in re.finditer(r"<a:p>(.*?)</a:p>", xml, re.S):
                if m.group(1).count("<a:pPr>") > 1:
                    bad_ppr.append(n)
print("multi-pPr paragraphs:", bad_ppr or "none")

# 2) 形状级检查
prs = Presentation(PATH)
SW, SH = prs.slide_width, prs.slide_height
def emu_in(v): return v / 914400

def char_w(ch, pt):
    # 全角按字号宽度，半角按 0.55 倍
    return pt * (1.0 if ord(ch) > 0x2E7F else 0.55) / 72.0

issues = []
for si, slide in enumerate(prs.slides, 1):
    boxes = []
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        txt = sh.text_frame.text
        if not txt.strip():
            continue
        L, T = sh.left, sh.top
        Wd, Ht = sh.width, sh.height
        if L < -Emu(20000) or T < -Emu(20000) or L + Wd > SW + Emu(20000) or T + Ht > SH + Emu(20000):
            issues.append(f"S{si} OUT-OF-SLIDE: '{txt[:14]}' pos=({emu_in(L):.2f},{emu_in(T):.2f}) size=({emu_in(Wd):.2f}x{emu_in(Ht):.2f})")
        # 估算最高字号与行数
        max_pt, lines = 0, 0
        for para in sh.text_frame.paragraphs:
            ptxt = "".join(r.text for r in para.runs)
            pt = max([r.font.size.pt for r in para.runs if r.font.size] + [12])
            max_pt = max(max_pt, pt)
            if not ptxt:
                lines += 1
                continue
            wsum = sum(char_w(c, pt) for c in ptxt)
            avail = max(emu_in(Wd) - 0.06, 0.1)
            lines += max(1, -(-wsum // avail))
        est_h = lines * max_pt * 1.32 / 72.0
        if est_h > emu_in(Ht) * 1.18 + 0.06:
            issues.append(f"S{si} OVERFLOW? '{txt[:16]}' lines={int(lines)} est={est_h:.2f}in box={emu_in(Ht):.2f}in")
        boxes.append((L, T, Wd, Ht, txt[:10]))
    # 文本框重叠（忽略包含关系 >85% 的）
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0]))
            oy = max(0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))
            inter = ox * oy
            amin = min(a[2]*a[3], b[2]*b[3])
            if inter > amin * 0.35 and inter < amin * 0.95:
                issues.append(f"S{si} OVERLAP: '{a[4]}' vs '{b[4]}' {inter/amin:.0%}")

print("slides:", len(prs.slides))
if issues:
    print(f"{len(issues)} issue(s):")
    for x in issues: print(" ", x)
else:
    print("no issues found")
