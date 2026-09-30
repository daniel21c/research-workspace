# -*- coding: utf-8 -*-
"""
k22 — 국토계획 학회 샘플(sample_20260122ver.hwp) 위에 투고본 .hwp를 조립 (심사용·저자정보 포함본)

편집규정(2026-06-05 개정) 제18~21조와 학회 샘플을 따른다.
- 앞부분(제목·부제·저자·Abstract·주제어·1쪽 저자 각주·머리말)은 샘플을 HWPML로 내보낸 XML에서 글자만 바꾼다
  (샘플의 스타일·상자·머리말/꼬리말·쪽 번호를 그대로 쓰기 위해). 샘플 본문은 지운다.
- 본문은 한글 자동화로 샘플 스타일(본문·개요 1~2·표 본문·표 주석·인용문헌 제목/본문)을 적용해 2단으로 쓴다.
  표와 그림은 본문 폭(1단 구역, '다단 설정 나누기')에 넣는다. 표 제목은 표 위 왼쪽, 그림 제목은 그림 아래 가운데, 국·영 병기.
- 심사용(anon): 저자명·소속·저자 각주·짝수쪽 머리말 저자명을 넣지 않는다(제19조②9). 저자정보본(author): 넣는다.
- 인용문헌은 번호를 붙이고 국문 문헌 아래 줄에 영문을 병기한다(샘플 형식).

입력: output/manuscript_kpa/국토계획_투고초본_v2_<날짜>.md, 표·그림은 k18 결과, 샘플은 TEMPLATE
출력: output/manuscript_kpa/국토계획_투고본_{심사용|저자정보}_<날짜>.hwp·.pdf, 쪽수는 쪽수_기록.json
실행: python k22_hwp_kpa.py [anon|author|both]   (k18·k19 먼저. Windows + 한글 2022 + pyhwpx)
"""
from __future__ import annotations
import copy, json, os, re, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import config as C
from k18_v2_results import build_tables_v2, FIGS_V2

MK = C.MK; FIG = C.OUT / "figures"
TEMPLATE = C.ROOT / "templates" / "kpa_sample_20260122ver.hwp"     # 학회 홈페이지 '국문샘플'(2026-01-22판) 사본
WORK = C.OUT / "_hwp_work"                                             # 중간 파일(HWPML)
DATE = "20260929"
TEXT_W_MM = 210 - 20 - 18                # 편집규정 제20조: 좌 20, 우 18 → 본문 폭 172 mm
PAGEDEF = {"위쪽": 19.0, "아래쪽": 11.0, "왼쪽": 20.0, "오른쪽": 18.0, "머리말": 7.8, "꼬리말": 7.0, "제본여백": 0}
ALIGN = {"Left": "ParagraphShapeAlignLeft", "Center": "ParagraphShapeAlignCenter", "Justify": "ParagraphShapeAlignJustify"}
# 정렬은 단순 액션으로 바꾼다. (멈춤의 원인은 스타일 적용 시 뜨는 "덮어쓸까요?" 대화상자였고 MSGBOX_AUTO로 해결됨)
# 스타일별 글자 크기(학회 샘플 값). 앞 문단의 글자 모양이 이어지지 않도록 문단마다 명시한다.
STYLE_PT = {"본문": 9.5, "개요1": 13.5, "개요2": 11.0, "표주석": 7.0, "표본문": 9.0, "인용제목": 13.0, "인용본문": 9.0}
ST = {"본문": 10, "개요1": 11, "개요2": 12, "표주석": 14, "표본문": 15, "인용제목": 19, "인용본문": 20}   # 샘플 스타일 번호

# 저자 정보: JTG 게재본(Park, Eom, Lee, 2026; Graduate School of Urban Studies, Hanyang University)과 같게.
# 직위는 연구진 확인표(2026-08) 기준 — 투고 전 저자 확인(체크리스트).
AUTHORS = [
    {"ko": "박종하", "en": "Park, Jongha", "pos": "Doctorate Candidate", "aff": "Graduate School of Urban Studies, Hanyang University",
     "role": "First Author", "email": "daniel21c@hanyang.ac.kr"},
    {"ko": "엄선용", "en": "Eom, Sunyong", "pos": "Associate Professor", "aff": "Graduate School of Urban Studies, Hanyang University",
     "role": "Corresponding Author", "email": "sunyongeom@hanyang.ac.kr"},
]
SHORT_TITLE = "서울시 생활권의 자족성 상승과 경계 불일치"
DOT = "・"                                 # 샘플의 저자 구분 기호


# 한글 대화상자 자동 응답: 예/덮어씀(YESNO=Yes 0x10000, YESNOCANCEL=Yes 0x1000, OKCANCEL=OK 0x10, OK 0x1).
# 스타일 적용 시 "본문을 [표 본문] 스타일 모양으로 덮어쓸까요?" 창이 떠서 자동화가 멈추고 사용자 화면에 창이 뜨던 문제(2026-09-27).
MSGBOX_AUTO = 0x10000 | 0x1000 | 0x10 | 0x1

# 한글 인스턴스 관리: 이 스크립트가 새로 띄운 Hwp.exe의 PID만 기록해 두고, 비정상 종료 시 그것만 정리한다.
# (이전의 `taskkill /F /IM Hwp.exe`는 사용자가 열어 둔 한글 문서까지 강제 종료할 수 있어 제거함, 2026-09-30 외부 검토.)
_OWN_PIDS: set[int] = set()


def _hwp_pids() -> set[int]:
    import subprocess
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Hwp.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return {int(r.split('","')[1]) for r in out.splitlines() if r.startswith('"Hwp.exe"')}


def cleanup_own_hwp():
    import subprocess
    for pid in _OWN_PIDS & _hwp_pids():
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)


def new_hwp():
    from pyhwpx import Hwp
    before = _hwp_pids(); h = Hwp(new=True, visible=False); _OWN_PIDS.update(_hwp_pids() - before)   # 새 인스턴스만 쓰고 끝에 quit
    try: h.hwp.SetMessageBoxMode(MSGBOX_AUTO)
    except AttributeError: h.SetMessageBoxMode(MSGBOX_AUTO)
    return h


# ------------------------------------------------------------------ 익명화(이전 k09에서 옮김)
def anonymize(hwp_path: Path, pdf_path: Path):
    """익명심사: 한글이 문서 속성에 넣는 Windows 사용자명을 같은 길이의 공백으로 치환(구조 유지), PDF 메타데이터 비움."""
    import getpass
    user = getpass.getuser()
    data = hwp_path.read_bytes(); n = 0
    for enc in ("utf-16le", "utf-8", "cp949"):
        needle = user.encode(enc)
        if needle and needle in data:
            n += data.count(needle); data = data.replace(needle, " ".encode(enc) * len(user))
    if n: hwp_path.write_bytes(data)
    import fitz
    d = fitz.open(str(pdf_path)); d.set_metadata({"author": "", "creator": "", "producer": "", "title": "", "subject": "", "keywords": ""})
    tmp = pdf_path.with_suffix(".tmp.pdf"); d.save(str(tmp), garbage=1); d.close(); tmp.replace(pdf_path)
    print(f"익명화: hwp 사용자명 치환 {n}곳, pdf 메타데이터 제거")


# ------------------------------------------------------------------ 원고 읽기
def read_md(md: Path):
    meta, body = {}, []
    for line in md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^%([A-Z_]+):\s*(.*)$", line)
        if m: meta[m.group(1)] = m.group(2).strip()
        else: body.append(line)
    return meta, body


# ------------------------------------------------------------------ 앞부분(XML)
def _set_text(p, text):
    """문단 p의 첫 TEXT만 남기고 글자를 text로 바꾼다(글자 모양은 첫 TEXT의 것)."""
    texts = [t for t in p if t.tag == "TEXT"]
    t0 = texts[0]
    for t in texts[1:]: p.remove(t)
    for ch in list(t0):
        if ch.tag == "CHAR": t0.remove(ch)
    if text:
        c = ET.SubElement(t0, "CHAR"); c.text = text


def _runs(p, runs):
    """문단 p를 (글자모양번호, 글자) 목록으로 다시 쓴다."""
    for t in [t for t in p if t.tag == "TEXT"]: p.remove(t)
    for cs, s in runs:
        t = ET.SubElement(p, "TEXT", {"CharShape": str(cs)}); c = ET.SubElement(t, "CHAR"); c.text = s


def make_front(meta: dict, mode: str, out_hml: Path, sample_hml: Path):
    raw = sample_hml.read_bytes().lstrip(b"\xef\xbb\xbf")
    root = ET.fromstring(raw)
    ds = root.find("HEAD/DOCSUMMARY")
    for k in ("TITLE", "AUTHOR", "SUBJECT", "KEYWORDS", "COMMENTS"):
        e = ds.find(k)
        if e is not None: e.text = ""
    sec = root.find("BODY/SECTION"); ps = list(sec)
    parent = {c: p for p in root.iter() for c in p}
    allp = list(root.iter("P"))
    by_style = lambda s: [p for p in allp if p.get("Style") == str(s)]
    # 제목(국문 제목 스타일 1): 제목 각주 기호(* **)는 쓰지 않는다(발표·연구비 각주 없음).
    tp = by_style(1)[0]; _set_text(tp, meta["TITLE_KO"])
    sub = ET.Element("P", {"ParaShape": "11", "Style": "2"}); _runs(sub, [(14, ": " + meta["SUBTITLE_KO"])])
    lst = parent[tp]; lst.insert(list(lst).index(tp) + 1, sub)
    _set_text(by_style(3)[0], meta["TITLE_EN"])
    ep = by_style(4)[0]; _runs(ep, [(38, ": " + meta["SUBTITLE_EN"])])          # 영문 소제목 스타일 글자 모양
    # 저자(스타일 5, 국문·영문 두 문단)
    a_ko, a_en = by_style(5)[:2]
    if mode == "author":
        runs = []
        for i, a in enumerate(AUTHORS):
            runs += [(12, (DOT if i else "") + a["ko"]), (47, "*" * (i + 1))]
        _runs(a_ko, runs); _set_text(a_en, DOT.join(a["en"] for a in AUTHORS))
    else:
        _set_text(a_ko, ""); _set_text(a_en, "")
    ap = by_style(7)[0]; _set_text(ap, meta["ABSTRACT_EN"])              # 초록 본문
    # 초록 칸 높이: 샘플(한 줄)보다 길어 아래 줄과 겹치지 않도록 초록 행(RowAddr 2) 칸과 표 높이를 늘린다.
    extra = 3400
    cell = parent[parent[ap]]; row = parent[cell]; tbl = parent[row]
    for c in row:
        if c.tag == "CELL": c.set("Height", str(int(c.get("Height")) + extra))
    sz = tbl.find("SHAPEOBJECT/SIZE")
    if sz is not None: sz.set("Height", str(int(sz.get("Height")) + extra))
    kw_t = by_style(8); _set_text(kw_t[0], "주제어")                        # 주제어 제목(샘플 '키워드')
    kw_b = [p for p in by_style(9) if "".join(c.text or "" for c in p.iter("CHAR")).strip()]   # 빈 간격 칸 제외
    _set_text(kw_b[0], meta["KEYWORDS_KO"]); _set_text(kw_b[1], meta["KEYWORDS_EN"])
    # 머리말: 홀수쪽 = 짧은 제목, 짝수쪽 = 저자명(심사용은 비움)
    for hd in ps[0].iter("HEADER"):
        chars = list(hd.iter("CHAR"))
        if not chars: continue
        if hd.get("ApplyPageType") == "Odd": chars[0].text = SHORT_TITLE
        elif hd.get("ApplyPageType") == "Even": chars[0].text = DOT.join(a["ko"] for a in AUTHORS) if mode == "author" else ""
    # 첫 장 제목
    own = [t for t in ps[0] if t.tag == "TEXT"]
    for t in own:
        for ch in t:
            if ch.tag == "CHAR" and ch.text and "서 론" in ch.text: ch.text = "Ⅰ. 서론"
    # 1쪽 저자 각주 표(샘플 문단 4의 표): 행 1..n = 저자, 나머지 행 삭제
    keep = [ps[0]]
    if mode == "author":
        p4 = ps[4]; tbl = p4.find(".//TABLE"); rows = [r for r in tbl if r.tag == "ROW"]      # 행 0 = 구분선, 행 1.. = 각주
        for i, a in enumerate(AUTHORS):
            cells = [c for c in rows[1 + i] if c.tag == "CELL"]
            txt_p = cells[1].find("PARALIST").findall("P")
            _set_text(txt_p[0], f"{a['pos']}, {a['aff']} ({a['role']}: {a['email']})")
            for extra in txt_p[1:]: cells[1].find("PARALIST").remove(extra)
        for r in rows[1 + len(AUTHORS):]: tbl.remove(r)
        tbl.set("RowCount", str(1 + len(AUTHORS)))
        so = tbl.find("SHAPEOBJECT"); sz = so.find("SIZE"); pos = so.find("POSITION")
        sz.set("Height", str(sum(int(r.find("CELL").get("Height")) for r in rows[:1 + len(AUTHORS)])))
        pos.set("VertRelTo", "Page"); pos.set("VertAlign", "Bottom"); pos.set("VertOffset", "0")   # 1쪽 아래에 고정
        for t in list(p4):                                              # 표 뒤 샘플 글자 제거
            if t.tag == "TEXT":
                for ch in list(t):
                    if ch.tag == "CHAR": t.remove(ch)
        keep.append(p4)
    for p in ps:
        if p not in keep: sec.remove(p)
    out_hml.write_bytes(b'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + ET.tostring(root, encoding="utf-8"))
    return out_hml


# ------------------------------------------------------------------ 본문(한글 자동화)
class Writer:
    def __init__(self, hml: Path):
        self.h = new_hwp()
        self.h.open(str(hml))
        pd_ = self.h.get_pagedef_as_dict(); pd_.update(PAGEDEF); self.h.set_pagedef(pd_)
        self.h.MoveDocEnd()

    def _last_cold(self):
        c, last = self.h.HeadCtrl, None
        while c:
            if c.CtrlID == "cold": last = c
            c = c.Next
        return last

    def columns(self, n):
        """현재 위치에서 다단 설정을 나누고 단 수를 n으로(1 = 본문 폭 구역)."""
        self.h.BreakColDef()
        c = self._last_cold(); ps = c.Properties
        ps.SetItem("Count", n); ps.SetItem("SameSize", 1); ps.SetItem("SameGap", 1700); c.Properties = ps
        # 단 정의가 들어간 문단은 '다음 문단과 함께'가 지켜지지 않으므로(표 제목 두 줄이 쪽을 넘어 갈라짐) 아주 작은 빈 문단을 둔다
        # (문단 모양은 다음 문단으로 이어지므로 바꾸지 않고, 글자 크기만 1pt로 한다. 다음 문단은 para()가 크기를 다시 정한다.)
        self.h.set_style(ST["표본문"]); self.h.set_font(Height=1); self.h.BreakPara()

    def para(self, text, style="본문", align=None, bold_all=False, size=None, newpara=True, keep=False):
        h = self.h
        h.set_style(ST[style])
        if align: h.HAction.Run(ALIGN[align])
        segs = [x for x in re.split(r"(\*\*[^*]+\*\*)", text) if x]
        for s in segs:
            marked = s.startswith("**") and s.endswith("**")
            kw = {"Height": size or STYLE_PT[style]}
            if bold_all or marked or len(segs) > 1: kw["Bold"] = bold_all or marked   # 스타일 기본 굵기를 건드리지 않음
            h.set_font(**kw)
            h.insert_text(s[2:-2] if marked else s)
        if not segs: h.set_font(Height=size or STYLE_PT[style])                # 빈 문단도 크기 명시
        if keep: h.set_para(KeepWithNext=1)                                    # 제목이 다음 문단과 떨어지지 않게
        if newpara: h.BreakPara()

    def two_line(self, first, second, style, align, bold_label=True, size=None, keep_next=False):
        """'표 1. …' + 줄바꿈 + 'Table 1. …' 형식(라벨 굵게)."""
        h = self.h
        h.set_style(ST[style]); h.HAction.Run(ALIGN[align])
        for k, line in enumerate((first, second)):
            m = re.match(r"^((?:표|그림|Table|Fig\.)\s+A?\d+\.)(.*)$", line)
            lab, rest = (m.group(1), m.group(2)) if m else ("", line)
            kw = {"Height": size} if size else {}
            h.set_font(Bold=bold_label, **kw); h.insert_text(lab)
            h.set_font(Bold=False, **kw); h.insert_text(rest)
            if k == 0: h.BreakLine()
        if keep_next: h.set_para(KeepWithNext=1, KeepLinesTogether=1)       # 표 제목이 표와 떨어지지 않게
        h.BreakPara()

    def table(self, headers, rows, widths_cm, bold_last=False, size=7.5):
        h = self.h
        tot = sum(widths_cm) * 10.0; scale = min(1.0, (TEXT_W_MM - 4) / tot)
        widths_mm = [w * 10.0 * scale for w in widths_cm]
        h.set_style(ST["표본문"])
        pset = h.HParameterSet.HTableCreation; h.HAction.GetDefault("TableCreate", pset.HSet)
        pset.Rows = len(rows) + 1; pset.Cols = len(headers); pset.HeightType = 0
        pset.WidthType = 1; pset.WidthValue = h.MiliToHwpUnit(sum(widths_mm))
        for j, w in enumerate(widths_mm): pset.ColWidth.SetItem(j, h.MiliToHwpUnit(w))
        h.HAction.Execute("TableCreate", pset.HSet)
        # 새 표는 직전 표(저자정보본의 쪽 아래 고정 각주 표)의 배치 속성을 물려받을 수 있으므로 '글자처럼 취급'으로 고정한다
        tc = h.ParentCtrl
        if tc is not None and tc.CtrlID == "tbl":
            tp = tc.Properties; tp.SetItem("TreatAsChar", 1); tp.SetItem("TextWrap", 0); tc.Properties = tp
        data = [headers] + rows
        for i, row in enumerate(data):
            last = bold_last and i == len(data) - 1
            for j, v in enumerate(row):
                h.set_style(ST["표본문"]); h.HAction.Run(ALIGN["Left" if j == 0 else "Center"])
                h.set_font(Height=size, Bold=(i == 0 or last)); h.insert_text(str(v))
                if not (i == len(data) - 1 and j == len(row) - 1): h.TableRightCell()
        h.MoveDocEnd()
        h.set_para(KeepWithNext=1)                                             # 표와 아래 주석이 떨어지지 않게
        h.BreakPara()

    def picture(self, path: Path, width_cm: float):
        h = self.h
        w_mm = min(width_cm * 10.0, TEXT_W_MM)
        with Image.open(path) as im: ratio = im.height / im.width
        h.set_style(ST["표본문"]); h.HAction.Run(ALIGN["Center"])
        h.insert_picture(str(path), treat_as_char=True, sizeoption=1, width=int(w_mm), height=int(w_mm * ratio))
        h.MoveDocEnd(); h.set_para(KeepWithNext=1); h.BreakPara()                  # 그림과 아래 제목이 떨어지지 않게

    def save(self, out: Path):
        self.h.save_as(str(out)); n = int(self.h.PageCount)
        pdf = out.with_suffix(".pdf"); self.h.save_as(str(pdf), "PDF"); self.h.quit()
        anonymize(out, pdf)
        return n, pdf


def layout_check(pdf: Path) -> dict:
    """출력 PDF 배치 점검: 글자 줄이 서로 겹친 쪽, 국문·영문 제목 줄이 다른 쪽으로 갈라진 표·그림 번호."""
    import fitz
    d = fitz.open(str(pdf)); over, split = [], []
    loc = {}
    for i, pg in enumerate(d):
        rects = [fitz.Rect(l["bbox"]) for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) if "".join(s["text"] for s in l["spans"]).strip()]
        if any((not (rects[a] & rects[c]).is_empty) and (rects[a] & rects[c]).height > 2 and (rects[a] & rects[c]).width > 5 for a in range(len(rects)) for c in range(a + 1, len(rects))): over.append(i + 1)
        t = pg.get_text()
        for m in re.findall(r"(?:표|그림) (A?\d+)\. ", t): loc.setdefault(("ko", m), i + 1)
        for m in re.findall(r"(?:Table|Fig\.) (A?\d+)\. ", t): loc.setdefault(("en", m), i + 1)
    for (lang, num), pgno in loc.items():
        if lang == "ko" and loc.get(("en", num)) not in (pgno, None): split.append(num)
    return {"쪽수": len(d), "겹친_쪽": over, "제목_갈라진_번호": sorted(set(split))}


def build(md: Path, mode: str):
    meta, body = read_md(md)
    tables, figs = build_tables_v2(), FIGS_V2
    WORK.mkdir(parents=True, exist_ok=True)
    sample_hml = WORK / "kpa_sample.hml"
    if not sample_hml.exists():
        h = new_hwp(); h.open(str(TEMPLATE)); h.save_as(str(sample_hml), "HWPML2X"); h.quit()
    hml = make_front(meta, mode, WORK / f"front_{mode}.hml", sample_hml)
    W = Writer(hml)
    if mode == "anon": W.h.BreakPara()               # 'Ⅰ. 서론' 뒤 새 문단(저자본은 각주 표 문단에 이어 씀)
    # 본문 원고를 블록 목록으로: ('h1'|'h2'|'p'|'ref'|'float', 내용)
    blocks, in_refs, first_h1 = [], False, True
    for line in body:
        s = line.strip()
        if not s: continue
        if s.startswith("# "):
            t = s[2:].strip()
            if first_h1: first_h1 = False; continue          # 'Ⅰ. 서론'은 샘플 문단에 있음
            in_refs = t.startswith("인용문헌"); blocks.append(("h1", t)); continue
        if s.startswith("## "): blocks.append(("h2", s[3:])); continue
        m = re.match(r"^\[\[(TABLE|FIG):(\w+)\]\]$", s)
        if m: blocks.append(("float", m.groups())); continue
        blocks.append(("ref" if in_refs else "p", s))
    i, ref_no, one_col = 0, 0, False

    def h2(v):
        # 절 제목 뒤 빈 문단을 두면 한글이 빈 문단에는 '다음 문단과 함께'를 지키지 않아 제목이 쪽 끝에 홀로 남는다(외부 검토 2026-09-30, 6쪽·13쪽)
        # → 빈 문단 대신 문단 아래 간격으로 띄운다.
        W.para(v, "개요2", bold_all=True, keep=True, newpara=False); W.h.set_para(KeepWithNext=1, NextSpacing=10); W.h.BreakPara()

    while i < len(blocks):
        kind, v = blocks[i]
        if kind == "h2" and i + 1 < len(blocks) and blocks[i + 1][0] == "float":
            # 제목 바로 뒤가 표·그림이면 단 정의 문단이 끼어 '다음 문단과 함께'가 깨지므로(부록 제목이 쪽 끝에 홀로 남음) 제목을 1단 구역 안에 쓴다
            W.columns(1); one_col = True; h2(v); i += 1; continue
        if kind == "float":
            if not one_col: W.columns(1)
            while i < len(blocks) and blocks[i][0] == "float":
                typ, key = blocks[i][1]
                if typ == "TABLE":
                    t = tables[key]
                    W.two_line(f"표 {t['ko']}", f"Table {t['en']}", "표본문", "Left", size=8.5, keep_next=True)
                    W.table(t["headers"], t["rows"], t["widths"], bold_last=t.get("bold_last", False))
                    W.para("주: " + t["note"], "표주석", align="Left")
                else:
                    ko, en, fn, wcm, nt = figs[key]
                    W.picture(FIG / fn, wcm)
                    W.two_line(f"그림 {ko}", f"Fig. {en}", "표본문", "Center", size=8.5)
                    W.para("주: " + nt, "표주석", align="Left")
                i += 1
            W.columns(2); one_col = False
            continue
        if kind == "h1":
            if v.startswith("인용문헌"):
                W.para("인용문헌", "인용제목", bold_all=True); W.para("References", "인용제목", bold_all=True, size=12)
            else:
                W.para(v, "개요1", bold_all=True, keep=True)
        elif kind == "h2":
            h2(v)
        elif kind == "ref":
            ref_no += 1; parts = v.split(" // ")
            h = W.h; h.set_style(ST["인용본문"]); h.set_font(Height=9, Bold=False)     # 샘플 인용문헌 9pt(앞 'References' 12pt가 이어지지 않게)
            h.insert_text(f"{ref_no}. {parts[0]}")
            for ptxt in parts[1:]: h.BreakLine(); h.insert_text(ptxt)
            h.BreakPara()
        else:
            W.para(v, "본문")
        i += 1
    name = {"anon": "심사용", "author": "저자정보"}[mode]
    out = MK / f"국토계획_투고본_{name}_{DATE}.hwp"
    n, pdf = W.save(out)
    rec_p = MK / "쪽수_기록.json"
    rec = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else {}
    lay = layout_check(pdf)
    if lay["겹친_쪽"] or lay["제목_갈라진_번호"]: print("배치 경고:", lay)
    for k in ("hwp", "hwp_생성", "hwp_쪽수(한글, 1단)", "hwp_pdf", "hwp_방법", "hwp_error"): rec.pop(k, None)   # 이전 k09(1단) 기록
    rec[f"hwp_{name}"] = {"파일": out.name, "쪽수(한글)": n, "pdf": pdf.name, "생성": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "방법": "k22 학회 샘플(2026-01-22판) 위 조립, 본문 2단·표/그림 본문 폭", "배치_점검": lay}
    rec_p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, n, pdf


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    md = sorted(MK.glob("국토계획_투고초본_v2_*.md"))[-1]
    try:
        for mode in (["anon", "author"] if which == "both" else [which]):
            out, n, pdf = build(md, mode)
            print(f"{mode}: {out.name} | {n}쪽 | {pdf.name}")
    finally:
        cleanup_own_hwp()
