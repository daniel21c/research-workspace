# -*- coding: utf-8 -*-
"""
k09 — 국토계획 투고 초본 .hwp 직접 생성 (한글 2022 자동화, pyhwpx)

한글 2022는 docx·doc·rtf를 자동화로 열면 한워드(Hword)로 넘겨 버려 변환이 되지 않는다(k08 기록).
그래서 docx를 거치지 않고, k06과 같은 원고(md)·표(결과 파일)·그림을 한글 자동화 API로 직접 써서 .hwp를 만든다.
표는 TableCreate 액션(열 너비 지정), 그림은 insert_picture, 글자·문단 모양은 set_font/set_para.
("표 속성 대화상자" 계열 액션은 서버 예외를 내므로 쓰지 않는다.)

출력: output/manuscript_kpa/국토계획_투고초본_v1_<날짜>.hwp, 같은 이름 _한글출력.pdf, 쪽수는 쪽수_기록.json에 추가
실행: python k09_hwp_build.py   (k03·k06 먼저. Windows + 한글 2022 + pyhwpx 필요)
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
from PIL import Image
import config as C
from k06_kpa_submission import build_tables, FIGS, draw_framework, MK, FIG

BODY, HEAD, EN = "함초롬바탕", "맑은 고딕", "Times New Roman"
TEXT_W_MM = 210 - 20 - 18          # 본문 폭(용지 210, 좌 20, 우 18)


class HwpDoc:
    def __init__(self):
        from pyhwpx import Hwp
        os.system("taskkill /F /IM Hwp.exe >nul 2>&1")
        self.h = Hwp(visible=False)
        pd_ = self.h.get_pagedef_as_dict()
        pd_.update({"위쪽": 19.0, "아래쪽": 11.0, "왼쪽": 20.0, "오른쪽": 18.0, "머리말": 6.0, "꼬리말": 5.0, "제본여백": 0})
        self.h.set_pagedef(pd_)

    # ----- 문단 -----
    def para(self, text, face=BODY, size=9.5, bold=False, align="Justify", line=160, indent=0.0, before=0, after=0, italic=False):
        h = self.h
        h.set_para(AlignType=align, LineSpacing=line, PrevSpacing=before, NextSpacing=after, Indentation=indent)
        parts = re.split(r"(\*\*[^*]+\*\*)", text)
        for s in parts:
            if not s: continue
            b = s.startswith("**") and s.endswith("**")
            h.set_font(FaceName=face, Height=size, Bold=(bold or b), Italic=italic)
            h.insert_text(s.strip("*") if b else s)
        h.BreakPara()

    # ----- 표 -----
    def table(self, headers, rows, widths_cm, bold_last=False, font=7.2):
        h = self.h
        tot = sum(widths_cm) * 10.0
        scale = min(1.0, (TEXT_W_MM - 2) / tot)
        widths_mm = [w * 10.0 * scale for w in widths_cm]
        pset = h.HParameterSet.HTableCreation; h.HAction.GetDefault("TableCreate", pset.HSet)
        pset.Rows = len(rows) + 1; pset.Cols = len(headers); pset.HeightType = 0
        pset.WidthType = 1; pset.WidthValue = h.MiliToHwpUnit(sum(widths_mm))
        for j, w in enumerate(widths_mm):
            pset.ColWidth.SetItem(j, h.MiliToHwpUnit(w))
        h.HAction.Execute("TableCreate", pset.HSet)
        data = [headers] + rows
        for i, row in enumerate(data):
            last = bold_last and i == len(data) - 1
            for j, v in enumerate(row):
                h.set_font(FaceName=BODY, Height=font, Bold=(i == 0 or last)); h.set_para(AlignType="Left" if j == 0 else "Center", LineSpacing=115)
                h.insert_text(str(v))
                if not (i == len(data) - 1 and j == len(row) - 1): h.TableRightCell()
        h.MoveDocEnd()

    # ----- 그림 -----
    def picture(self, path: Path, width_cm: float):
        h = self.h
        w_mm = min(width_cm * 10.0, TEXT_W_MM)
        with Image.open(path) as im:
            ratio = im.height / im.width
        h.set_para(AlignType="Center")
        h.insert_picture(str(path), treat_as_char=True, sizeoption=1, width=int(w_mm), height=int(w_mm * ratio))
        h.MoveDocEnd(); h.BreakPara()

    def save(self, out: Path):
        ok = self.h.save_as(str(out)); n = int(self.h.PageCount)
        pdf = out.with_name(out.stem + "_한글출력.pdf"); self.h.save_as(str(pdf), "PDF")
        self.h.quit(); return ok, n, pdf


def build(md_path: Path):
    meta, body = {}, []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^%([A-Z_]+):\s*(.*)$", line)
        if m: meta[m.group(1)] = m.group(2).strip()
        else: body.append(line)
    tables = build_tables(); draw_framework()
    d = HwpDoc()
    d.para(meta["TITLE_KO"], HEAD, 14, True, "Center", 130, after=2)
    d.para("- " + meta["SUBTITLE_KO"] + " -", HEAD, 11, False, "Center", 130, after=6)
    d.para(meta["TITLE_EN"], EN, 12, True, "Center", 120, after=2)
    d.para("- " + meta["SUBTITLE_EN"] + " -", EN, 10.5, False, "Center", 120, after=10)
    d.para("**Abstract**  " + meta["ABSTRACT_EN"], EN, 8.5, False, "Justify", 130, after=6)
    d.para("**주제어:** " + meta["KEYWORDS_KO"], BODY, 8.5, False, "Left", 130, after=2)
    d.para("**Keywords:** " + meta["KEYWORDS_EN"], EN, 8.5, False, "Left", 130, after=8)
    in_refs = False
    for line in body:
        s = line.strip()
        if not s: continue
        if s.startswith("# "):
            t = s[2:].strip(); in_refs = t.startswith("인용문헌"); d.para(t, HEAD, 13.5, True, "Left", 120, before=14, after=6); continue
        if s.startswith("## "): d.para(s[3:], HEAD, 11, True, "Left", 120, before=10, after=4); continue
        if s.startswith("### "): d.para(s[4:], HEAD, 10.5, True, "Left", 120, before=6, after=2); continue
        m = re.match(r"^\[\[TABLE:(\w+)\]\]$", s)
        if m:
            t = tables[m.group(1)]
            d.para(f"표 {t['ko']} / Table {t['en']}", BODY, 8.5, True, "Center", 110, before=6, after=3)
            d.table(t["headers"], t["rows"], t["widths"], bold_last=t.get("bold_last", False))
            d.para("주: " + t["note"], BODY, 7.5, False, "Justify", 115, after=8); continue
        m = re.match(r"^\[\[FIG:(\w+)\]\]$", s)
        if m:
            ko, en, fn, w, nt = FIGS[m.group(1)]
            d.picture(FIG / fn, w)
            d.para(f"그림 {ko} / Figure {en}", BODY, 8.5, True, "Center", 110, after=3)
            d.para("주: " + nt, BODY, 7.5, False, "Justify", 115, after=8); continue
        if in_refs:
            d.para(s, BODY, 8.5, False, "Left", 130, after=2); continue
        d.para(s, BODY, 9.5, False, "Justify", 160, indent=3.5)
    out = MK / (md_path.stem + ".hwp")
    ok, n, pdf = d.save(out)
    rec_p = MK / "쪽수_기록.json"
    rec = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else {}
    rec.update({"hwp": out.name, "hwp_생성": time.strftime("%Y-%m-%d %H:%M:%S"), "hwp_쪽수(한글, 1단)": n, "hwp_pdf": pdf.name, "hwp_방법": "k09 한글 자동화 직접 생성(docx 미경유)"})
    rec.pop("hwp_error", None)
    rec_p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, n, pdf


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(MK.glob("국토계획_투고초본_v*.md"))[-1]
    out, n, pdf = build(md)
    print("hwp:", out, "| 쪽수", n, "| pdf:", pdf.name)
