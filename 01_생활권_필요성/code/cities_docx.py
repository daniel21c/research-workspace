# -*- coding: utf-8 -*-
"""Build the Cities submission files (2026-10-02, folder layout as in 03_불일치_접근성_AG).
Sources (text): code/manuscript_src/{manuscript.md, manuscript_ko.md, title_page.md, highlights.md, declarations.md, cover_letter.md, tables/*.md}
Outputs: manuscript/Cities_manuscript_anonymised.docx, Cities_한국어_원고.docx, Cities_title_page.docx, Cities_highlights.docx,
         Cities_declarations.docx, Cities_cover_letter.docx, word_count.json;
         manuscript/figures/Figure_1..6.tif (from Fig*.png, 600 dpi) and GraphicalAbstract.tif.
Optional: python cities_docx.py memo  → 보고_20261002/Cities_교수님보고_20261002.docx from code/manuscript_src/report_memo.md
Tables use horizontal rules only (Cities: avoid vertical rules and shading)."""
import re, sys, json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image
CODE = Path(__file__).parent; SRC = CODE / "manuscript_src"; ROOT = CODE.parent; MAN = ROOT / "manuscript"; FIG = MAN / "figures"

def new_doc(spacing=2.0, size=12, east="Malgun Gothic", font="Times New Roman"):
    d = Document(); st = d.styles["Normal"]; st.font.name = font; st.font.size = Pt(size); st.element.rPr.rFonts.set(qn("w:eastAsia"), east)
    st.paragraph_format.line_spacing = spacing
    for s in d.sections: s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
    return d

def math_runs(par, text, italic=False, bold=False):
    """부록 수식: x_i, x_{s∈S_k}, A^s_ij 를 실제 아래·위첨자로 쓴다(본문과 같은 글꼴·크기, Word가 첨자 크기를 정함).
    첨자 앞 라틴 문자 이름(p, pop, A …)과 첨자 안 라틴 문자는 기울임, 그리스 문자·숫자·기호는 바로 세움."""
    def put(s, it=False, sub=False, sup=False):
        for m in re.finditer(r"[A-Za-z]+|[^A-Za-z]+", s):
            r = par.add_run(m.group(0)); r.bold = bold; w = m.group(0)
            lone = (not sub and not sup and len(w) == 1 and w != "a" and w.isascii() and w.isalpha()
                    and not re.match(r"[A-Za-z0-9.(]", s[m.end():m.end() + 1] or " ") and not re.match(r"[A-Za-z0-9.]", s[m.start() - 1:m.start()] or " ") and not re.search(r"\d\s$", s[:m.start()]))   # "2 h"·"260 s" 같은 단위는 제외
            r.italic = italic or lone or (it and w[0].isascii() and w[0].isalpha())   # 홀로 쓴 변수 글자(i, k, s, u, M, P)도 기울임
            if "̄" in w:   # 결합 문자(τ̄)는 맑은 고딕에서 깨지므로 Times로
                r.font.name = "Times New Roman"; r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "Times New Roman")
            if sub: r.font.subscript = True
            if sup: r.font.superscript = True
    i = 0; buf = ""
    while i < len(text):
        ch = text[i]
        if ch in "_^" and i > 0 and not text[i - 1].isspace() and i + 1 < len(text):
            mb = re.search(r"[A-Za-z]+$", buf)                      # 첨자 앞 이름은 기울임
            if mb: put(buf[:mb.start()]); put(mb.group(0), it=True)
            else: put(buf)
            buf = ""
            if text[i + 1] == "{":
                j = text.index("}", i + 2); scr = text[i + 2:j].replace("_", ""); i = j + 1
            else:
                m = re.match(r"[A-Za-z0-9]+", text[i + 1:]); scr = m.group(0) if m else ""; i += 1 + len(scr)
            put(scr, it=True, sub=(ch == "_"), sup=(ch == "^"))
            continue
        buf += ch; i += 1
    put(buf)

def runs(par, text, math=False):
    text = text.replace("$", "").replace("\\,", " ").replace("\\;", " ").replace("\\ ", " ")
    pat = r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)" if math else r"(\*\*[^*]+\*\*|\*[^*]+\*|\^[^^]+\^|`[^`]+`)"
    for part in re.split(pat, text):
        if part.startswith("**") and part.endswith("**"):
            if math: math_runs(par, part[2:-2], bold=True)
            else: par.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            if math: math_runs(par, part[1:-1], italic=True)
            else: par.add_run(part[1:-1]).italic = True
        elif part.startswith("^") and part.endswith("^") and not math: par.add_run(part[1:-1]).font.superscript = True
        elif part.startswith("`") and part.endswith("`"): par.add_run(part[1:-1])
        elif math: math_runs(par, part)
        else: par.add_run(part)

def equation(doc, eq, num=""):
    """식 줄: 왼쪽 들여쓰기 1 cm, 식 번호는 오른쪽 탭으로 오른쪽 끝에 맞춤. 여러 줄 식은 원문에서 "$$ "로 시작하는 줄마다 한 줄."""
    from docx.enum.text import WD_TAB_ALIGNMENT
    sec = doc.sections[-1]; width = sec.page_width - sec.left_margin - sec.right_margin
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(1); p.paragraph_format.tab_stops.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)
    p.paragraph_format.keep_with_next = not num
    runs(p, eq, math=True)
    if num: p.add_run("\t" + num)

def borders(tbl, header_rows=1):
    def set_b(cell, **kw):
        tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn("w:tcBorders"))
        if b is None: b = OxmlElement("w:tcBorders"); tcPr.append(b)
        for edge, val in kw.items():
            e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), val); e.set(qn("w:sz"), "8"); e.set(qn("w:color"), "000000"); b.append(e)
    n = len(tbl.rows)
    for ri, row in enumerate(tbl.rows):
        for cell in row.cells:
            set_b(cell, left="nil", right="nil", insideV="nil", top="single" if ri == 0 else "nil", bottom="single" if (ri == header_rows - 1 or ri == n - 1) else "nil")

def is_text(c):
    c = re.sub(r"[*`\s]", "", c); return bool(c) and sum(ch.isalpha() for ch in c) >= 0.5 * len(c)

def add_table(doc, block, fs=9):
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block if not re.match(r"^\|\s*:?-{3,}", r)]
    nc = len(rows[0]); body_ = rows[1:] or rows
    # 글자 열(본문 칸의 60% 이상이 글자 위주)은 왼쪽, 숫자 열은 가운데. 첫 열은 늘 왼쪽
    left = [ci == 0 or sum(is_text(r[ci]) for r in body_ if ci < len(r)) >= 0.6 * len(body_) for ci in range(nc)]
    # 열 너비: 칸 글자 수(머리행은 가장 긴 단어)에 비례, 4~28자로 자름
    # 열 너비: 칸 글자 수에 비례(최대 22자) + 여백 3자. 가장 긴 단어(머리행 포함)보다 좁아지지 않게 해 "2020"·"5%"가 쪼개지지 않게 한다
    cw = lambda t: sum(2 if "가" <= ch <= "힣" else 1 for ch in re.sub(r"[*`]", "", t))   # 한글은 2칸
    word = [max(cw(w) for r in rows if ci < len(r) for w in (r[ci].split() or ["x"])) for ci in range(nc)]
    need = [max(min(22, max((cw(r[ci]) for r in body_ if ci < len(r)), default=4)), word[ci]) + 3 for ci in range(nc)]
    sec = doc.sections[-1]; width = sec.page_width - sec.left_margin - sec.right_margin
    minw = [Cm(0.2 * fs / 9 * word[ci] + 0.5) for ci in range(nc)]   # 가장 긴 단어가 한 줄에 들어가는 절대 최소 너비
    raw = [width * n / sum(need) for n in need]; short = [ci for ci in range(nc) if raw[ci] < minw[ci]]
    if short:
        rest = width - sum(minw[ci] for ci in short); others = [ci for ci in range(nc) if ci not in short]
        raw = [minw[ci] if ci in short else rest * need[ci] / sum(need[cj] for cj in others) for ci in range(nc)]
    tb = doc.add_table(rows=len(rows), cols=nc); tb.autofit = False
    for ri, row in enumerate(rows):
        if ri == 0:   # 쪽을 넘으면 머리행 반복
            trPr = tb.rows[0]._tr.get_or_add_trPr(); h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
        for ci, c in enumerate(row[:nc]):
            cell = tb.cell(ri, ci); cell.width = int(raw[ci])
            pp = cell.paragraphs[0]; f = pp.paragraph_format; f.line_spacing = 1.0; f.space_before = Pt(1); f.space_after = Pt(1); runs(pp, c)
            pp.alignment = 0 if left[ci] else 1
            for r_ in pp.runs: r_.font.size = Pt(fs); r_.bold = r_.bold or ri == 0
    borders(tb)

def md_table(doc, path):
    t = path.read_text(encoding="utf-8").splitlines()
    title = next((l[2:] for l in t if l.startswith("# ")), path.stem)
    p = doc.add_paragraph(); m_ = re.match(r"^((?:Table|표) [A-Z]?\.?\d+\.?)\s*(.*)$", title)
    if m_: p.add_run(m_.group(1)).bold = True; p.add_run(" " + m_.group(2))   # "Table 1." 굵게, 제목은 보통
    else: runs(p, title)
    i = 0; notes = []
    def flush():   # 주석은 그 표 바로 아래(표 4처럼 (a)·(b)가 있으면 각각)
        for s in notes:
            q = doc.add_paragraph(); runs(q, s); q.paragraph_format.line_spacing = 1.0
            for r_ in q.runs: r_.font.size = Pt(9)
        notes.clear()
    while i < len(t):
        if t[i].startswith("|"):
            block = []
            while i < len(t) and t[i].startswith("|"): block.append(t[i]); i += 1
            add_table(doc, block); flush()
        else:
            s = t[i].strip()
            if s and not s.startswith("# "):
                if s.startswith("## "): q = doc.add_paragraph(); q.add_run(s[3:]).italic = True
                else: notes.append(s)
            i += 1
    flush(); doc.add_paragraph()

def body(doc, lines, stop=None):
    i = 0; math = False
    while i < len(lines):
        line = lines[i]
        if stop and line.startswith(stop): break
        if line.startswith("## "): math = line.startswith(("## Appendix A", "## 부록 A"))   # 수식 표기는 부록 A에만
        s = line.strip()
        eqm = re.match(r"^(?:\$\$\s*)?(.*?)\s{2,}(\(A\.\d+\))$", s) if math else None
        if eqm: equation(doc, eqm.group(1), eqm.group(2)); i += 1; continue
        if math and s.startswith("$$"): equation(doc, s[2:].strip()); i += 1; continue
        if math and s and not s.startswith(("|", "#", "- ")): runs(doc.add_paragraph(), s, math=True); i += 1; continue
        if s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"): block.append(lines[i]); i += 1
            add_table(doc, block, fs=9)
            while i < len(lines) and not lines[i].strip(): i += 1
            if i < len(lines) and lines[i].startswith(("Note:", "주:")):   # 표 주석: 뒤쪽 표와 같은 9 pt, 줄 간격 1
                q = doc.add_paragraph(); runs(q, lines[i].strip(), math=math); q.paragraph_format.line_spacing = 1.0
                for r_ in q.runs: r_.font.size = Pt(9)
                i += 1
            continue
        if s.startswith("$$"): p = doc.add_paragraph(); p.alignment = 1; runs(p, s.strip("$"))
        elif line.startswith("# "): doc.add_heading(line[2:], level=0)
        elif line.startswith("#### "): doc.add_heading(line[5:], level=3)
        elif line.startswith("### "): doc.add_heading(line[4:], level=2)
        elif line.startswith("## "): doc.add_heading(line[3:], level=1)
        elif line.startswith("- "): runs(doc.add_paragraph(style="List Bullet"), line[2:])
        elif re.match(r"^\d+\. ", line): runs(doc.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", line))
        elif s == "---": doc.add_page_break()
        elif s: runs(doc.add_paragraph(), s)
        i += 1

def build_manuscript(src_name, out_name, tables_dir, heading_tables, spacing=2.0, check_anon=True, font="Times New Roman", size=12):
    src = (SRC / src_name).read_text(encoding="utf-8")
    if check_anon:
        for bad in ("Jongha", "Sunyong", "Eom,", "Hanyang", "HY-2024", "박종하", "엄선용", "한양"):
            assert bad not in src.split("## References")[0].split("## 참고문헌")[0], f"identifying text in manuscript body: {bad}"
    d = new_doc(spacing, size=size, font=font)
    tables_key = "## Tables" if "## Tables" in src else "## 표"
    body(d, src.splitlines(), stop=tables_key)
    d.add_page_break(); d.add_heading(heading_tables, level=1)
    for f in sorted(tables_dir.glob("Table*.md")): md_table(d, f)
    d.save(MAN / out_name); return src

def simple(md_name, out_name, spacing=1.15):
    d = new_doc(spacing); body(d, (SRC / md_name).read_text(encoding="utf-8").splitlines()); d.save(MAN / out_name)

if len(sys.argv) > 1 and sys.argv[1] == "memo":
    out = ROOT / "보고_20261002" / "Cities_교수님보고_20261002.docx"; out.parent.mkdir(exist_ok=True)
    d = new_doc(1.25, 10.5, font="Malgun Gothic"); body(d, (SRC / "report_memo.md").read_text(encoding="utf-8").splitlines()); d.save(out); print(out); sys.exit()

en = build_manuscript("manuscript.md", "Cities_manuscript_anonymised.docx", SRC / "tables", "Tables")
if (SRC / "manuscript_ko.md").exists():
    build_manuscript("manuscript_ko.md", "Cities_한국어_원고.docx", SRC / "tables_ko", "표", spacing=1.6, font="Malgun Gothic", size=11)   # 한글·라틴·수식 모두 맑은 고딕(크기 차이 없음)
for m, o in (("title_page.md", "Cities_title_page.docx"), ("highlights.md", "Cities_highlights.docx"), ("declarations.md", "Cities_declarations.docx"), ("cover_letter.md", "Cities_cover_letter.docx")):
    simple(m, o)
figs = ["Fig1_study_area.png", "Fig2_framework.png", "Fig3_completion_curves.png", "Fig4_single_facility_shortfall.png", "Fig5_living_zone_map_2025.png", "Fig6_zero_completion_by_unit.png"]
for n, f in enumerate(figs, 1):
    Image.open(FIG / f).convert("RGB").save(FIG / f"Figure_{n}.tif", compression="tiff_lzw", dpi=(600, 600))
Image.open(FIG / "GraphicalAbstract.png").convert("RGB").save(FIG / "GraphicalAbstract.tif", compression="tiff_lzw", dpi=(200, 200))
w = lambda s: len(re.findall(r"\S+", s.replace("$$", "")))
abstract = en.split("## Abstract")[1].split("**Keywords")[0]
main = en.split("## 1. Introduction")[1].split("## Appendix A")[0]
appx = en.split("## Appendix A")[1].split("## References")[0]
refs = en.split("## References")[1].split("## Figure captions")[0]
caps = en.split("## Figure captions")[1].split("## Tables")[0]
tabs = sum(w(p.read_text(encoding="utf-8")) for p in (SRC / "tables").glob("Table*.md"))
wc = {"abstract": w(abstract), "main_text_1_to_5": w(main), "appendices": w(appx), "references": w(refs), "figure_captions": w(caps), "tables": tabs,
      "total_including_references": w(abstract) + w(main) + w(appx) + w(refs) + w(caps) + tabs,
      "n_references": len([x for x in refs.split("\n\n") if x.strip()]), "highlights_chars": [len(l[2:]) for l in (SRC / "highlights.md").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]}
json.dump(wc, open(MAN / "word_count.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(wc, ensure_ascii=False)); print(sorted(p.name for p in MAN.iterdir()))
