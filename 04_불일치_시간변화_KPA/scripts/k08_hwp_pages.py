# -*- coding: utf-8 -*-
"""
k08 — 투고 초본의 PDF 변환·쪽수 기록·HWP 변환 (Windows, MS Word·한글 2022 COM 필요)

1) Word COM: 1단 docx → pdf, 2단 docx → pdf, 쪽수 기록
2) 한글 COM: 2단 docx → .hwp 저장, 한글 기준 쪽수 기록
결과: output/manuscript_kpa/쪽수_기록.json
실행: python k08_hwp_pages.py   (k06 먼저)
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import config as C

MK = C.OUT / "manuscript_kpa"


def word_pdf(docx: Path, also_doc=False) -> tuple[Path, int]:
    import win32com.client as w
    app = w.Dispatch("Word.Application"); app.Visible = False
    pdf = docx.with_suffix(".pdf")
    import shutil, uuid                            # Word는 변환 중 강제 종료된 적이 있는 파일 이름을 다시 열 때 멈추므로 임시 이름 사본으로 연다
    tmp = docx.with_name(f"_tmp_{uuid.uuid4().hex[:8]}.docx"); shutil.copy2(docx, tmp)
    try:
        d = app.Documents.Open(str(tmp), AddToRecentFiles=False); d.SaveAs2(str(pdf), FileFormat=17)
        d.Close(False)
    finally:
        app.Quit(); tmp.unlink(missing_ok=True)
    import fitz                                   # 쪽수는 저장된 PDF에서 센다(Word 통계는 배치 모드에서 1을 돌려줄 때가 있음)
    n = len(fitz.open(str(pdf)))
    return pdf, n


def hwp_convert(docx: Path) -> tuple[Path, int]:
    """한글 2022 자동화(pyhwpx가 보안 모듈을 등록). docx 직접 열기가 안 되면 Word가 저장한 .doc로 연다."""
    from pyhwpx import Hwp
    hwp = Hwp(visible=False)
    ok = False
    for path, fmt in ((docx, ""), (docx.with_suffix(".doc"), "MSWord"), (docx.with_suffix(".doc"), "")):
        if not path.exists(): continue
        try:
            ok = bool(hwp.open(str(path), format=fmt, arg="forceopen:true"))
        except Exception:
            ok = False
        if ok and int(hwp.PageCount) > 1: break
        ok = False
    if not ok:
        hwp.quit(); raise RuntimeError("한글이 docx/.doc를 열지 못함 — 최종본은 학회 HWP 양식에 수작업으로 옮긴다")
    out = docx.with_suffix(".hwp"); hwp.save_as(str(out)); n = int(hwp.PageCount); hwp.quit()
    return out, n


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    one = sorted(p for p in MK.glob("국토계획_투고초본_v*.docx") if not p.stem.endswith("_2단편집"))[-1]
    two = one.with_name(one.stem + "_2단편집.docx")
    rec = {"생성": time.strftime("%Y-%m-%d %H:%M:%S"), "원고": one.name}
    pdf1, n1 = word_pdf(one); rec["1단_pdf"] = pdf1.name; rec["1단_쪽수(Word)"] = n1
    if two.exists():
        pdf2, n2 = word_pdf(two); rec["2단_pdf"] = pdf2.name; rec["2단_쪽수(Word)"] = n2
    # .hwp는 k09_hwp_build.py가 한글 자동화로 직접 만든다(docx 경유 변환은 한글이 한워드로 넘겨 실패 — hwp_convert는 기록용으로만 남김)
    old = json.loads((MK / "쪽수_기록.json").read_text(encoding="utf-8")) if (MK / "쪽수_기록.json").exists() else {}
    for k in ("hwp", "hwp_생성", "hwp_쪽수(한글, 1단)", "hwp_pdf", "hwp_방법"):
        if k in old: rec[k] = old[k]
    rec["비고"] = "학회 최종 편집(2단, 학회 양식 글꼴)과 쪽수가 다를 수 있음. 25쪽 한도 참고용."
    (MK / "쪽수_기록.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=1))
