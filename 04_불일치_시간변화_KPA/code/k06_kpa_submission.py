# -*- coding: utf-8 -*-
"""
k06 — 국토계획(KPA) 투고 초본 docx 생성

원고 본문은 manuscript/국토계획_투고초본_v1_<날짜>.md 에서 읽고,
표의 숫자는 results/ 의 결과 파일에서 읽어 넣는다(본문 문장의 수치는 k04 생성 원고에서 옮긴 것으로,
같은 표 파일에서 나온 값이다). 그림은 output/figures/ 의 파일을 넣고, 그림 1(분석 틀)은 여기서 그린다.

서식: 국토계획 국문논문 익명심사용 투고본(v12, 2026-09-02)과 같은 서식을 따른다.
  A4, 여백 상 1.9 / 하 1.1 / 좌 2.0 / 우 1.8 cm, 본문 HCR Batang 9.5pt 양쪽 정렬 줄간격 1.6,
  장 제목 Ⅰ. 1. 1) 체계(Malgun Gothic), 표·그림 제목 국문/영문 병기, 주는 "주:" 로 시작, 영문 초록·주제어 앞머리.
저자 정보는 넣지 않는다(익명심사). 저자가 채울 항목은 manuscript/투고전_체크리스트.md 에 있다.

실행: python k06_kpa_submission.py [md 파일 경로]
"""
from __future__ import annotations
import re, sys, json
from pathlib import Path
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
import config as C

MK = C.MK
MK.mkdir(parents=True, exist_ok=True)
T = C.TAB; FIG = C.FIG
BODY_FONT, HEAD_FONT, EN_FONT = "HCR Batang", "Malgun Gothic", "Times New Roman"


# ---------- 서식 도우미 ----------
def _rfonts(el, name):
    rpr = el.get_or_add_rPr(); rf = rpr.rFonts
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn(f"w:{a}"), name)


def style(doc, name, font, size, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=1.6, before=0, after=0, first=None, base="Normal"):
    try:
        st = doc.styles[name]
    except KeyError:
        st = doc.styles.add_style(name, 1); st.base_style = doc.styles[base]
    st.font.name = font; st.font.size = Pt(size); st.font.bold = bold; _rfonts(st.element, font)
    pf = st.paragraph_format; pf.alignment = align; pf.line_spacing = line
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    if first is not None: pf.first_line_indent = Cm(first)
    return st


def run_font(run, name=BODY_FONT, size=9.5, bold=None, italic=None):
    run.font.name = name; run.font.size = Pt(size); _rfonts(run._element, name)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic


def para(doc, text, st="Normal", **kw):
    p = doc.add_paragraph(style=st)
    add_runs(p, text, **kw)
    return p


def add_runs(p, text, size=None, font=None):
    """**굵게** 마크업만 처리."""
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for s in parts:
        if not s: continue
        bold = s.startswith("**") and s.endswith("**")
        r = p.add_run(s.strip("*") if bold else s)
        if font or size or bold:
            run_font(r, name=font or p.style.font.name or BODY_FONT, size=size or (p.style.font.size.pt if p.style.font.size else 9.5), bold=bold or None)


def caption(doc, ko, en, kind="table"):
    lab_ko = "표" if kind == "table" else "그림"; lab_en = "Table" if kind == "table" else "Figure"
    p = doc.add_paragraph(style="KPA Caption")
    r = p.add_run(f"{lab_ko} {ko} / {lab_en} {en}"); run_font(r, BODY_FONT, 8.5, bold=True)
    p.paragraph_format.keep_with_next = True
    return p


def note(doc, text):
    p = doc.add_paragraph(style="KPA Note"); r = p.add_run("주: " + text); run_font(r, BODY_FONT, 7.5)
    return p


def cell_text(cell, text, size=7.5, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""; p = cell.paragraphs[0]; p.alignment = align; p.paragraph_format.line_spacing = 1.0
    r = p.add_run(str(text)); run_font(r, BODY_FONT, size, bold=bold)
    tcPr = cell._tc.get_or_add_tcPr(); mar = OxmlElement("w:tcMar")
    for k, v in (("top", 20), ("bottom", 20), ("start", 40), ("end", 40)):
        e = OxmlElement(f"w:{k}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    tcPr.append(mar)


def borders(table):
    """학술지 표: 위·아래 굵은 선, 머리행 아래 가는 선, 세로선 없음."""
    tbl = table._tbl; tblPr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge, val, sz in (("top", "single", 12), ("bottom", "single", 12), ("left", "nil", 0), ("right", "nil", 0), ("insideH", "nil", 0), ("insideV", "nil", 0)):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), val)
        if sz: e.set(qn("w:sz"), str(sz)); e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)
    for c in table.rows[0].cells:
        tcPr = c._tc.get_or_add_tcPr(); tb = OxmlElement("w:tcBorders"); e = OxmlElement("w:bottom")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6"); e.set(qn("w:color"), "000000"); tb.append(e); tcPr.append(tb)


def add_table(doc, headers, rows, widths_cm, first_left=True, bold_last=False):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for j, h in enumerate(headers):
        cell_text(t.rows[0].cells[j], h, bold=True)
    for i, row in enumerate(rows, start=1):
        last = bold_last and i == len(rows)
        for j, v in enumerate(row):
            cell_text(t.rows[i].cells[j], v, bold=last, align=WD_ALIGN_PARAGRAPH.LEFT if (j == 0 and first_left) else WD_ALIGN_PARAGRAPH.CENTER)
    for row in t.rows:
        for j, w in enumerate(widths_cm):
            row.cells[j].width = Cm(w)
    borders(t)
    doc.add_paragraph()
    return t


# ---------- 숫자 서식 ----------
pct = lambda x, d=1: f"{x*100:.{d}f}"
pp = lambda x, d=2: f"{x*100:+.{d}f}"


# ---------- 표 정의 (숫자는 결과 파일에서) ----------
def build_tables():
    res = json.loads((T / "results.json").read_text(encoding="utf-8"))
    t01 = pd.read_csv(T / "t01_data_summary.csv", encoding="utf-8-sig", dtype={"year": str}).set_index("year")
    long = pd.read_csv(T / "t02_gu_metrics_long.csv", encoding="utf-8-sig")
    ch = pd.read_csv(T / "t03_gu_change.csv", encoding="utf-8-sig"); ch = ch[ch.ku_code != "SEOUL"].copy(); ch["ku_code"] = ch.ku_code.astype(int); ch = ch.set_index("ku_code")
    dec = pd.read_csv(T / "t04_decomposition.csv", encoding="utf-8-sig"); decD = dec[dec.metric == "D"].copy()
    decD = decD[decD.ku_code != "SEOUL"].copy(); decD["ku_code"] = decD.ku_code.astype(int); decD = decD.set_index("ku_code")
    sel = pd.read_csv(T / "t06_selection.csv", encoding="utf-8-sig").set_index("ku_code")
    fixed = pd.read_csv(T / "t04b_fixed_ld2020_on_2025.csv", encoding="utf-8-sig").set_index("ku_code")
    ari = pd.read_csv(T / "t09_ari_ld20_ld25.csv", encoding="utf-8-sig").set_index("ku_code")
    nul = pd.read_csv(T / "t05_null_summary.csv", encoding="utf-8-sig").set_index("ku_code")
    order = list(sel.index)
    S = res["seoul"]; SC = res["seoul_change"]; DS = res["decomposition_seoul"]["D"]

    tables = {}
    # T1 자료
    tables["T1"] = dict(
        ko="1. 분석 자료", en="1. Data Used in the Analysis",
        headers=["자료", "시점·범위", "처리", "역할"],
        rows=[["서울 생활이동 OD", "2020년 1월, 2025년 1월", "도착 09:00~20:59, 통근(HW·WH) 제외, 요일 전체, 서울 내부, 비공개 행 0", "IFR·G·D 계산"],
              ["행정동 경계", "424개(두 해 공통 정본)", "2021년 코드표 기준 통일", "집계·탐지 단위"],
              ["공식 지역생활권(LZ)", "116개(2030 서울생활권계획)", "행정동→생활권 대응(면적 최대 중첩, 최솟값 0.51)", "평가 대상 경계"],
              ["이동 기반 경계(LD)", "연도별 116개", "자치구 내 Leiden 합의(3,000회, τ = 0.5)", "비교 기준점"],
              ["필터 후 통행량", f"{t01.loc['2020','flow_daily_seoul']/1e6:,.1f}백만 / {t01.loc['2025','flow_daily_seoul']/1e6:,.1f}백만", f"비공개 행 비율 {t01.loc['2020','masked_row_share_daily']*100:.1f}% / {t01.loc['2025','masked_row_share_daily']*100:.1f}%", "분모 T의 합"]],
        widths=[3.2, 3.6, 6.4, 3.0], note="생활이동 자료는 서울시·KT의 추정 이동량이며, 3명 미만 셀은 비공개 처리되어 0으로 두었다.")
    # T2 지표
    tables["T2"] = dict(
        ko="2. 지표의 정의", en="2. Definitions of the Measures",
        headers=["지표", "정의", "해석"],
        rows=[["T", "구 K에서 출발한 서울 내 전체 통행량", "두 경계 공통 분모(경계와 무관)"],
              ["IFR^B", "N^B / T, N^B = 경계 B에서 출발·도착이 같은 권역인 통행량", "경계 B의 내부통행비율"],
              ["a, b", "LD에서만 내부인 통행량, LZ에서만 내부인 통행량", "N^LD − N^LZ = a − b"],
              ["G", "(a − b) / T = IFR^LD − IFR^LZ", "격차의 방향(양: LD가 더 담음)"],
              ["D", "(a + b) / T", "격차의 크기(판정이 다른 통행의 비율), 0 ≤ |G| ≤ D"],
              ["ΔG, ΔD", "2025년 값 − 2020년 값", "%p"],
              ["IoU", "동 기준 1:1 최대 교집합 배정의 면적 교집합/합집합", "경계 모양의 일치도(D의 외부 검증)"]],
        widths=[1.6, 8.6, 6.0], note="서울 전체 값은 구 값의 평균이 아니라 분자합/분모합이다.")
    # T3 구별 IFR G D
    rows = []
    for k in order:
        a = long[(long.ku_code == k) & (long.year == 2020)].iloc[0]; b = long[(long.ku_code == k) & (long.year == 2025)].iloc[0]
        rows.append([a.ku_name, pct(a.IFR_lz), pct(a.IFR_ld), pp(a.G), pct(a.D, 2), pct(b.IFR_lz), pct(b.IFR_ld), pp(b.G), pct(b.D, 2)])
    rows.append(["서울 전체", pct(S["2020"]["IFR_lz"]), pct(S["2020"]["IFR_ld"]), pp(S["2020"]["G"]), pct(S["2020"]["D"], 2), pct(S["2025"]["IFR_lz"]), pct(S["2025"]["IFR_ld"]), pp(S["2025"]["G"]), pct(S["2025"]["D"], 2)])
    tables["T3"] = dict(ko="3. 자치구별 내부통행비율과 판정 불일치의 방향(G)·크기(D)", en="3. Internal-Flow Ratios and Directional (G) and Total (D) Mismatch by District",
                        headers=["구", "IFR LZ 2020(%)", "IFR LD 2020(%)", "G 2020(%p)", "D 2020(%)", "IFR LZ 2025(%)", "IFR LD 2025(%)", "G 2025(%p)", "D 2025(%)"],
                        rows=rows, widths=[2.0] + [1.75] * 8, bold_last=True, note="G = 0, D = 0인 구는 두 경계가 완전히 같은 구다. 서울 전체는 분자합/분모합.")
    # T4 변화·분해
    rows = []
    for k in order:
        c = ch.loc[k]; d = decD.loc[k]
        rows.append([c.ku_name, pp(c.dIFR_lz, 1), pp(c.dIFR_ld, 1), pp(c.dG), pp(c.dD), pp(d.flow_effect_mean), pp(d.boundary_effect_mean), c.quadrant])
    rows.append(["서울 전체", pp(SC["IFR_lz"], 1), pp(SC["IFR_ld"], 1), pp(SC["G"]), pp(SC["D"]), pp(DS["flow_effect_mean"]), pp(DS["boundary_effect_mean"]), "—"])
    tables["T4"] = dict(ko="4. 2020→2025년 변화와 ΔD의 분해", en="4. Changes from 2020 to 2025 and Decomposition of ΔD",
                        headers=["구", "ΔIFR LZ(%p)", "ΔIFR LD(%p)", "ΔG(%p)", "ΔD(%p)", "통행 변화 효과(%p)", "경계 재도출 효과(%p)", "사분면(G20, G25)"],
                        rows=rows, widths=[2.0, 1.7, 1.7, 1.6, 1.6, 2.2, 2.2, 2.4], bold_last=True,
                        note="분해는 LD를 2020년에 고정한 순서와 2025년에 고정한 순서의 평균이며 두 효과의 합은 ΔD와 같다. 사분면은 (G 2020 부호, G 2025 부호).")
    # T5 선별
    rows = []
    for k in order:
        s = sel.loc[k]; f = fixed.loc[k]; r = ari.loc[k]
        rows.append([s.ku_name, pct(s.D_2025, 2), pp(s.dD), pp(s.G_2025), "선별" if s.selected_B else "", ("권역 내 운영 검토" if s.type == "접근성·운영 검토" else s.type) if isinstance(s.type, str) else "",
                     "○" if s["selected_B_minband0.5"] else "", "○" if s["selected_B_minband1.0"] else "", pp(f.D_ld20on25 - s.D_2020), f"{r.ari_ld20_ld25:.2f}", int(r.n_dong_changed)])
    tables["T5"] = dict(ko="5. 재정비 검토 대상의 선별과 강건성", en="5. Selection of Districts for Review and Robustness",
                        headers=["구", "D 2025(%)", "ΔD(%p)", "G 2025(%p)", "규칙", "대응 유형", "ΔD>0.5%p", "ΔD>1%p", "ΔD(LD2020 고정)(%p)", "ARI(LD20, LD25)", "소속 변경 동"],
                        rows=rows, widths=[1.8, 1.4, 1.4, 1.5, 1.1, 2.2, 1.3, 1.2, 1.9, 1.5, 1.3],
                        note="규칙: ΔD가 합의 변동 폭(이번 자료에서 0)을 넘어 증가하고 D 2025가 서울 전체 D(8.33%) 이상. 대응 유형은 G 2025의 부호. ARI는 두 해 LD 분할의 조정 랜드 지수, 소속 변경 동은 LD 소속 표기가 달라진 동 수.")
    # TA1 귀무
    rows = []
    for k in order:
        n = nul.loc[k]
        rows.append([n.ku_name, pp(n.null_dIFR_p05, 1), pp(n.null_dIFR_med, 1), pp(n.null_dIFR_p95, 1), pp(n.dIFR_lz, 1), pp(n.dIFR_ld, 1), "예" if n.lz_within_null90 else "아니오", "예" if n.ld_within_null90 else "아니오"])
    tables["TA1"] = dict(ko="A1. 자치구별 ΔIFR과 귀무 분할의 5~95% 구간", en="A1. ΔIFR by District and the 5–95% Range of Null Partitions",
                         headers=["구", "귀무 5%(%p)", "귀무 중앙(%p)", "귀무 95%(%p)", "ΔIFR LZ(%p)", "ΔIFR LD(%p)", "LZ 구간 내", "LD 구간 내"],
                         rows=rows, widths=[2.0, 1.8, 1.8, 1.8, 1.8, 1.8, 1.6, 1.6],
                         note=f"구마다 공식 생활권과 같은 개수의 무작위 인접 분할 {res['null']['n_per_gu']:,}개(시드 {res['null']['seed']})를 두 해 통행에 적용.")
    return tables


FIGS = {
    "F1": ("1. 분석의 흐름", "1. Analytical Framework", "F_kpa_framework.png", 13.5, "LD는 공식 생활권의 대체안이 아니라 같은 해의 이동 네트워크에서 도출한 비교 기준점이다."),
    "F2": ("2. 자치구별 내부통행비율의 변화(2020→2025)", "2. Change in Internal-Flow Ratios by District, 2020–2025", "F4-4-1_ifr_dumbbell.png", 15.5, "왼쪽 점 2020년, 오른쪽 점 2025년. 두 경계 모두 모든 구에서 상승."),
    "F3": ("4. 격차의 방향(G) 사분면도(점 크기 = |ΔD|)", "4. Quadrant Plot of the Directional Gap G (marker size = |ΔD|)", "F4-4-3_quadrant_G.png", 11.5, "가로축 G 2020, 세로축 G 2025. 1사분면은 두 해 모두 LD가 더 많이 담는 구."),
    "F4": ("5. 총 판정차의 변화(ΔD)와 선별된 자치구", "5. Change in Total Mismatch (ΔD) and Selected Districts", "F4-4-4_map_dD_selection.png", 14.0, "선별 8개 구. 기호는 대응 유형(경계 재검토 / 권역 내 운영 검토)."),
    "F5": ("6. 선별된 자치구의 공식 생활권과 두 해의 이동 기반 경계", "6. Official Living Zones and Mobility-Based Boundaries in Selected Districts", "F4-4-5_selected_gu_boundaries.png", 13.0, "구마다 왼쪽부터 공식 생활권(LZ), LD 2020, LD 2025. 굵은 검은 선은 권역 경계, 붉은 점선은 두 해 사이 LD 소속(같이 묶인 동의 집합)이 바뀐 동. ARI는 두 해 LD 분할의 조정 랜드 지수."),
    "F6": ("3. 경계 모양의 일치도(IoU)와 판정 불일치의 크기(D)", "3. Boundary Overlap (IoU) and Total Mismatch (D)", "F4-4-7_iou_vs_D.png", 11.5, "색은 G. IoU와 D는 강한 음의 상관(ρ = −0.92, −0.87), IoU와 G는 약함."),
    "FA1": ("A1. 두 경계의 ΔIFR과 귀무 분할의 ΔIFR 분포", "A1. ΔIFR of the Two Boundaries against Null-Partition Distributions", "F4-4-6_null_partition_dIFR.png", 15.5, "회색 상자는 귀무 분할 1,000개의 5~95% 구간."),
}


def draw_framework():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    plt.rcParams["font.family"] = "Malgun Gothic"; plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9.5, 3.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
    boxes = [(0.2, 2.3, "① 자료\n생활이동 OD\n2020·2025년 1월\n행정동 424"), (2.3, 2.3, "② 두 경계\n공식 생활권 LZ(고정 116)\n이동 기반 LD_t(연도별 116)"),
             (4.4, 2.3, "③ 판정 불일치\na, b → G(방향), D(크기)\n같은 분모 T"), (6.5, 2.3, "④ 변화\nΔG, ΔD\n통행 변화 / 경계 재도출 분해"),
             (8.6, 2.3, "⑤ 선별\n사전 규칙\n대응 유형(G 부호)")]
    for x, y, s in boxes:
        ax.add_patch(FancyBboxPatch((x, y), 1.9, 1.5, boxstyle="round,pad=0.05", fc="#f2f2f2", ec="black", lw=0.8)); ax.text(x + 0.95, y + 0.75, s, ha="center", va="center", fontsize=8.2)
    for x in (2.1, 4.2, 6.3, 8.4):
        ax.add_patch(FancyArrowPatch((x, 3.05), (x + 0.2, 3.05), arrowstyle="-|>", mutation_scale=10, lw=0.8))
    ax.add_patch(FancyBboxPatch((2.3, 0.3), 6.1, 1.3, boxstyle="round,pad=0.05", fc="white", ec="black", lw=0.8, ls="--"))
    ax.text(5.35, 0.95, "기준선·강건성: 무작위 인접 분할 1,000개(경계 무관 IFR 상승) · 독립 합의 10회 변동 폭 · τ 0.4/0.6 · LD2020 고정 · 최소 증가 폭 0.5/1%p · IoU 외부 검증", ha="center", va="center", fontsize=7.8)
    ax.add_patch(FancyArrowPatch((5.35, 2.3), (5.35, 1.6), arrowstyle="<|-|>", mutation_scale=9, lw=0.7, ls="--"))
    out = FIG / "F_kpa_framework.png"; fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(); return out


# ---------- 본문 조립 ----------
def build(md_path: Path):
    meta, body = {}, []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^%([A-Z_]+):\s*(.*)$", line)
        if m: meta[m.group(1)] = m.group(2).strip()
        else: body.append(line)
    tables = build_tables(); draw_framework()

    doc = Document()
    sec = doc.sections[0]; sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.top_margin = Cm(1.9); sec.bottom_margin = Cm(1.1); sec.left_margin = Cm(2.0); sec.right_margin = Cm(1.8)
    style(doc, "Normal", BODY_FONT, 9.5, line=1.6, first=0.35)
    style(doc, "KPA Title", HEAD_FONT, 14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.3, after=2)
    style(doc, "KPA Subtitle", HEAD_FONT, 11, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.3, after=6)
    style(doc, "KPA Title EN", EN_FONT, 12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.2, before=4, after=2)
    style(doc, "KPA Subtitle EN", EN_FONT, 10.5, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.2, after=10)
    style(doc, "KPA Abstract", EN_FONT, 8.5, line=1.3, after=6)
    style(doc, "KPA Keywords", BODY_FONT, 8.5, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.3, after=2)
    style(doc, "KPA Heading 1", HEAD_FONT, 13.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.2, before=14, after=6)
    style(doc, "KPA Heading 2", HEAD_FONT, 11, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.2, before=10, after=4)
    style(doc, "KPA Heading 3", HEAD_FONT, 10.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.2, before=6, after=2)
    style(doc, "KPA Caption", BODY_FONT, 8.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.1, before=6, after=3)
    style(doc, "KPA Note", BODY_FONT, 7.5, line=1.15, after=8)
    style(doc, "KPA Reference", BODY_FONT, 8.5, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.3, after=2)
    doc.styles["KPA Reference"].paragraph_format.left_indent = Cm(0.8); doc.styles["KPA Reference"].paragraph_format.first_line_indent = Cm(-0.8)

    # 머리
    para(doc, meta["TITLE_KO"], "KPA Title"); para(doc, "- " + meta["SUBTITLE_KO"] + " -", "KPA Subtitle")
    para(doc, meta["TITLE_EN"], "KPA Title EN"); para(doc, "- " + meta["SUBTITLE_EN"] + " -", "KPA Subtitle EN")
    p = doc.add_paragraph(style="KPA Abstract"); r = p.add_run("Abstract  "); run_font(r, EN_FONT, 9, bold=True); r = p.add_run(meta["ABSTRACT_EN"]); run_font(r, EN_FONT, 8.5)
    p = doc.add_paragraph(style="KPA Keywords"); r = p.add_run("주제어: "); run_font(r, BODY_FONT, 8.5, bold=True); r = p.add_run(meta["KEYWORDS_KO"]); run_font(r, BODY_FONT, 8.5)
    p = doc.add_paragraph(style="KPA Keywords"); r = p.add_run("Keywords: "); run_font(r, EN_FONT, 8.5, bold=True); r = p.add_run(meta["KEYWORDS_EN"]); run_font(r, EN_FONT, 8.5)

    in_refs = False
    blocks = []   # (첫 요소, 마지막 요소, 넓은 블록 여부) — 2단 편집에서 넓은 블록은 1단 폭으로 둔다
    WIDE = {"T3", "T4", "T5", "TA1", "F1", "F2", "F4", "F5", "FA1"}
    for line in body:
        s = line.strip()
        if not s: continue
        if s.startswith("# "):
            title = s[2:].strip(); in_refs = title.startswith("인용문헌")
            para(doc, title, "KPA Heading 1"); continue
        if s.startswith("## "): para(doc, s[3:], "KPA Heading 2"); continue
        if s.startswith("### "): para(doc, s[4:], "KPA Heading 3"); continue
        m = re.match(r"^\[\[TABLE:(\w+)\]\]$", s)
        if m:
            t = tables[m.group(1)]; cp = caption(doc, t["ko"], t["en"], "table")
            add_table(doc, t["headers"], t["rows"], t["widths"], bold_last=t.get("bold_last", False)); np_ = note(doc, t["note"])
            blocks.append((cp._p, np_._p, m.group(1) in WIDE)); continue
        m = re.match(r"^\[\[FIG:(\w+)\]\]$", s)
        if m:
            ko, en, fn, w, nt = FIGS[m.group(1)]; p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(FIG / fn), width=Cm(w)); caption(doc, ko, en, "figure"); np_ = note(doc, nt)
            blocks.append((p._p, np_._p, m.group(1) in WIDE)); continue
        if in_refs:
            para(doc, s, "KPA Reference"); continue
        para(doc, s, "Normal")
    cp = doc.core_properties; cp.author = ""; cp.last_modified_by = ""; cp.title = ""; cp.comments = ""   # 익명심사: 문서 속성 비움
    out = MK / (md_path.stem + ".docx"); doc.save(out)
    out2 = two_column(out, out.with_name(out.stem + "_2단편집.docx"))
    return out, out2


def _sect_break(before_el, cols):
    """요소 앞에 '연속 구역 나누기' 문단을 넣는다. 그 문단의 sectPr가 '그 앞' 구역의 단 수(cols)를 정한다."""
    p = OxmlElement("w:p"); pPr = OxmlElement("w:pPr"); sectPr = OxmlElement("w:sectPr")
    for tag, attrs in (("w:type", {"w:val": "continuous"}), ("w:pgSz", {"w:w": str(Cm(21).twips), "w:h": str(Cm(29.7).twips)}),
                       ("w:pgMar", {"w:top": str(Cm(1.9).twips), "w:bottom": str(Cm(1.1).twips), "w:left": str(Cm(2.0).twips), "w:right": str(Cm(1.8).twips), "w:header": "340", "w:footer": "283", "w:gutter": "0"}),
                       ("w:cols", {"w:num": str(cols), "w:space": "400"})):
        e = OxmlElement(tag)
        for k, v in attrs.items(): e.set(qn(k), v)
        sectPr.append(e)
    pPr.append(sectPr); p.append(pPr); before_el.addprevious(p)


WIDE_CAPTIONS = ("그림 1.", "그림 2.", "표 3.", "표 4.", "그림 4.", "표 5.", "그림 5.", "표 A1.", "그림 A1.")


def two_column(src: Path, out: Path) -> Path:
    """학회 인쇄 편집 확인용: 저장된 1단 docx를 다시 읽어 머리(제목·초록·주제어) 1단, 본문 2단으로 만든다.
    넓은 표·그림(WIDE_CAPTIONS)은 1단 폭 구역으로 끼워 넣고, 나머지 그림·표는 단 폭(8.4 cm)에 맞춘다."""
    doc = Document(str(src))
    ps = list(doc.paragraphs)
    first = next(p for p in ps if p.style.name == "KPA Heading 1"); _sect_break(first._p, 1)
    wide_els = []
    for i, p in enumerate(ps):
        if p.style.name != "KPA Caption" or not p.text.startswith(WIDE_CAPTIONS): continue
        if p.text.startswith("표"):
            start, end = p._p, ps[i + 1]._p            # 제목 → 표 → 주
        else:
            start, end = ps[i - 1]._p, ps[i + 1]._p    # 그림 → 제목 → 주
        el = start
        while el is not None:
            wide_els.append(el)
            if el is end: break
            el = el.getnext()
        _sect_break(start, 2); nxt = end.getnext()
        if nxt is not None: _sect_break(nxt, 1)
    wide_ids = {id(e) for e in wide_els}
    colw = Cm(8.4)
    for shp in doc.inline_shapes:
        pel = shp._inline.getparent().getparent()
        if id(pel) not in wide_ids and shp.width > colw:
            r = colw / shp.width; shp.height = int(shp.height * r); shp.width = int(colw)
    for tb in doc.tables:
        if id(tb._tbl) in wide_ids: continue
        tot = sum(c.width for c in tb.rows[0].cells)
        if tot > colw:
            r = colw / tot
            for row in tb.rows:
                for c in row.cells:
                    c.width = int(c.width * r)
                    for p in c.paragraphs:
                        for run in p.runs: run.font.size = Pt(6.5)
    last = doc.sections[-1]._sectPr; final_cols = "2"
    prev = last.getprevious()                         # 문서 끝이 넓은 블록이면 마지막 빈 구역을 없애고 1단으로
    if prev is not None and prev.tag == qn("w:p") and prev.find(qn("w:pPr")) is not None and prev.find(qn("w:pPr")).find(qn("w:sectPr")) is not None:
        prev.getparent().remove(prev); final_cols = "1"
    cols = last.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols"); last.append(cols)
    cols.set(qn("w:num"), final_cols); cols.set(qn("w:space"), "400")
    t = last.find(qn("w:type"))
    if t is None:
        t = OxmlElement("w:type"); last.insert(0, t)
    t.set(qn("w:val"), "continuous")
    doc.save(out)
    return out


def checklist():
    txt = """# 국토계획 투고 전 저자 작성·확인 사항 (초본 v1, 2026-09-27)

초본에는 저자 정보를 넣지 않았다(익명심사). 투고 시스템과 최종본에서 아래를 채운다.

1. 저자명·소속·직위·이메일·ORCID·교신저자. 학회 회원·회비 납부 확인.
2. 자기인용 처리: 이동 기반 구획 방법(연구2, JTG 게재본)은 익명심사용 초본에서 인용하지 않고 "이동 기반 경계의 도출" 절에 방법을 그대로 적었다. 채택 후 최종본에 인용을 넣는다.
3. 연구비·사사, 생활이동 자료의 이용 조건(집계 자료, IRB 비대상) 문구.
4. 생성형 AI 사용 고지(도구·기간·범위·저자 검증책임) — 학회 규정 확인.
5. 학술대회 발표본(2026-04 도시설계학회)과의 차이를 사사 또는 각주에 적는다. 이 초본은 신규 투고로 다룬다(사용자 결정 2026-09-27).
6. 영문 초록 분량·주제어 수, 표·그림 해상도(300 dpi 이상), 쪽수(25쪽 한도)와 게재료 확인. 최종본은 학회 제공 HWP 양식에 옮긴다.
7. 원자료에서 k01~k03을 마지막으로 재실행하고 표 3~5·A1의 수치와 manifest 해시를 대조한다.
8. 본문 문장의 수치는 k04 생성 원고(output/manuscript/)에서 옮긴 것이다. 표는 k06이 결과 파일에서 직접 만든다. 두 곳의 값이 같은지 최종 확인한다.
9. 참고문헌 서지: Halás(2024) Regional Studies 58(11): 2175-2187, INSEE(2022) 2022년 12월 발행, OMB(2021) 86 FR 37770-37778 — 2026-09-27 출판사·관보·INSEE 누리집에서 확인함. 나머지는 00_선행연구/문헌목록.md 확인 상태(W/L).
10. 심사 예상 질문(연구설계.md 8절): 원인 분석 부재, LD의 순환성, 구 내부 탐지 제약, 두 시점 한계, 비공개 셀, 선별 임계 사후 선택 여부.
11. 그림 2~6·A1의 구 이름·범례는 국문(k03, 2026-09-27 국문화). 수치 불변.
12. 쪽수: `.pdf`(1단, Word 변환) 18쪽, `_2단편집.pdf`(본문 2단, 넓은 표·그림은 1단 폭) 15쪽 — `쪽수_기록.json`. 학회 최종 편집(학회 양식 글꼴·2단)과는 다를 수 있으나 25쪽 한도 안이다.
13. HWP: `k09_hwp_build.py`가 한글 2022 자동화로 `.hwp`(1단, 14쪽)와 `_한글출력.pdf`를 직접 만든다(docx 미경유 — 한글은 docx·doc·rtf 자동화 열기를 한워드로 넘겨 실패). 학회 HWP 양식(2단·글꼴)으로 옮길 때 이 파일의 본문·표·그림을 그대로 붙여 넣는다.
"""
    (MK / "투고전_체크리스트.md").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(MK.glob("국토계획_투고초본_v*.md"))[-1]
    out, out2 = build(md); checklist()
    print("생성:", out, "\n2단:", out2)
