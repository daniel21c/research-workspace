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

def runs(par, text):
    text = text.replace("$", "").replace("\\,", " ").replace("\\;", " ").replace("\\ ", " ")
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|\^[^^]+\^|`[^`]+`)", text):
        if part.startswith("**") and part.endswith("**"): par.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2: par.add_run(part[1:-1]).italic = True
        elif part.startswith("^") and part.endswith("^"): par.add_run(part[1:-1]).font.superscript = True
        elif part.startswith("`") and part.endswith("`"): par.add_run(part[1:-1])
        else: par.add_run(part)

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

def add_table(doc, block, fs=9):
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block if not re.match(r"^\|\s*:?-{3,}", r)]
    tb = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for ri, row in enumerate(rows):
        for ci, c in enumerate(row[:len(rows[0])]):
            pp = tb.cell(ri, ci).paragraphs[0]; pp.paragraph_format.line_spacing = 1.0; runs(pp, c)
            for r_ in pp.runs: r_.font.size = Pt(fs); r_.bold = r_.bold or ri == 0
    borders(tb)

def md_table(doc, path):
    t = path.read_text(encoding="utf-8").splitlines()
    title = next((l[2:] for l in t if l.startswith("# ")), path.stem)
    p = doc.add_paragraph(); runs(p, title)
    for r_ in p.runs: r_.bold = True
    i = 0; notes = []
    while i < len(t):
        if t[i].startswith("|"):
            block = []
            while i < len(t) and t[i].startswith("|"): block.append(t[i]); i += 1
            add_table(doc, block)
        else:
            s = t[i].strip()
            if s and not s.startswith("# "):
                if s.startswith("## "): q = doc.add_paragraph(); q.add_run(s[3:]).italic = True
                else: notes.append(s)
            i += 1
    for s in notes:
        q = doc.add_paragraph(); runs(q, s); q.paragraph_format.line_spacing = 1.0
        for r_ in q.runs: r_.font.size = Pt(9)
    doc.add_paragraph()

def body(doc, lines, stop=None):
    i = 0
    while i < len(lines):
        line = lines[i]
        if stop and line.startswith(stop): break
        s = line.strip()
        if s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"): block.append(lines[i]); i += 1
            add_table(doc, block, fs=9.5); continue
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

def build_manuscript(src_name, out_name, tables_dir, heading_tables, spacing=2.0, check_anon=True):
    src = (SRC / src_name).read_text(encoding="utf-8")
    if check_anon:
        for bad in ("Jongha", "Sunyong", "Eom,", "Hanyang", "HY-2024", "박종하", "엄선용", "한양"):
            assert bad not in src.split("## References")[0].split("## 참고문헌")[0], f"identifying text in manuscript body: {bad}"
    d = new_doc(spacing)
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
    build_manuscript("manuscript_ko.md", "Cities_한국어_원고.docx", SRC / "tables_ko", "표", spacing=1.6)
for m, o in (("title_page.md", "Cities_title_page.docx"), ("highlights.md", "Cities_highlights.docx"), ("declarations.md", "Cities_declarations.docx"), ("cover_letter.md", "Cities_cover_letter.docx")):
    simple(m, o)
figs = ["Fig1_study_area.png", "Fig2_framework.png", "Fig3_completion_curves.png", "Fig4_single_facility_shortfall.png", "Fig5_living_zone_map_2025.png", "Fig6_zero_completion_by_unit.png"]
for n, f in enumerate(figs, 1):
    Image.open(FIG / f).convert("RGB").save(FIG / f"Figure_{n}.tif", compression="tiff_lzw", dpi=(600, 600))
Image.open(FIG / "GraphicalAbstract.png").convert("RGB").save(FIG / "GraphicalAbstract.tif", compression="tiff_lzw", dpi=(200, 200))
w = lambda s: len(re.findall(r"\S+", s))
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
