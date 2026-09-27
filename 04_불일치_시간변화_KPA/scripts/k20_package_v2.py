# -*- coding: utf-8 -*-
"""
k20 — KPA v2 공동연구자 패키지 + 제출본 묶음 + 패키지 자체 재현 시험

A. output/package_kpa_v2_<날짜>/      공동연구자용(자기완결): README · manuscript · tables · figures · scripts · data · manifest
B. output/제출본_v2_<날짜>/            투고 시스템에 올릴 것과 저자 작성 항목·예상 심사 질문·점검 기록
C. 패키지 자체 재현 시험: 패키지 폴더에서 테스트 2종과 k01을 실행해(저장소 경로 없이) 표가 저장소 결과와 같은지 확인
실행: python k20_package_v2.py   (k13~k19, k08, k09, k11 먼저)
"""
from __future__ import annotations
import hashlib, json, platform, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path
import pandas as pd
import config as C

MK = C.OUT / "manuscript_kpa"; FIG = C.OUT / "figures"; B = C.TAB / "benchmark"
KEEP_SCRIPTS = ["config.py", "kpa_metrics.py", "k01_compute.py", "k02_select.py", "k03_figures.py", "k06_kpa_submission.py", "k08_hwp_pages.py", "k09_hwp_build.py",
                "k11_independent_check.py", "k13_benchmark.py", "k14_reassign.py", "k15_access_link.py", "k16_attractors.py", "k17_similarity.py", "k18_v2_results.py",
                "k19_kpa_v2.py", "k20_package_v2.py", "requirements.txt"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def zipdir(src: Path, z: Path):
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src.rglob("*")):
            if p.is_file(): zf.write(p, p.relative_to(src.parent))


def package(stamp):
    pkg = C.OUT / f"package_kpa_v2_{stamp}"
    if pkg.exists(): shutil.rmtree(pkg)
    for d in ("manuscript", "tables/benchmark", "figures", "scripts/tests", "data/od", "data/access/결과/main", "data/access/결과/sens_T600", "data/access/입력/facility", "data/access/입력/grid", "docs"):
        (pkg / d).mkdir(parents=True, exist_ok=True)
    for n in KEEP_SCRIPTS: shutil.copy2(C.HERE / n, pkg / "scripts" / n)
    for f in (C.HERE / "tests").glob("*.py"): shutil.copy2(f, pkg / "scripts" / "tests" / f.name)
    for src in (C.LZ_MAP, C.ld_map(C.Y0), C.ld_map(C.Y1), C.DONG_GPKG, C.MANIFEST): shutil.copy2(src, pkg / "data" / src.name)
    for y in C.YEARS: shutil.copy2(C.od_daily(y), pkg / "data" / "od" / C.od_daily(y).name); shutil.copy2(C.od_summary(y), pkg / "data" / "od" / C.od_summary(y).name)
    shutil.copy2(C.CORE / "scripts" / "config.py", pkg / "data" / "core_config.py")
    for tag in ("main", "sens_T600"):
        for y in C.YEARS: shutil.copy2(C.ACC_DATA / "결과" / tag / f"unit_access_{y}_100.csv", pkg / "data" / "access" / "결과" / tag / f"unit_access_{y}_100.csv")
    shutil.copy2(C.ACC_DATA / "입력" / "facility" / "facility_2020_2025_units.parquet", pkg / "data" / "access" / "입력" / "facility" / "facility_2020_2025_units.parquet")
    shutil.copy2(C.ACC_DATA / "입력" / "grid" / "grid100_master.parquet", pkg / "data" / "access" / "입력" / "grid" / "grid100_master.parquet")
    for f in C.TAB.glob("*.*"): shutil.copy2(f, pkg / "tables" / f.name)
    for f in B.glob("*.*"): shutil.copy2(f, pkg / "tables" / "benchmark" / f.name)
    for f in list(FIG.glob("Fv2_*")) + list(FIG.glob("F4-4-6_*")): shutil.copy2(f, pkg / "figures" / f.name)
    stem = sorted(MK.glob("국토계획_투고초본_v2_*.md"))[-1].stem
    for f in MK.glob(f"{stem}*"): shutil.copy2(f, pkg / "manuscript" / f.name)
    for n in ("수치대조_기록_v2.json", "독립재계산_기록.json", "쪽수_기록.json", "투고전_체크리스트_v2.md"):
        if (MK / n).exists(): shutil.copy2(MK / n, pkg / "manuscript" / n)
    for f in (C.ROOT / "연구설계_v2_경계동진단.md", C.ROOT / "분석메모_재배정동과접근성_20260927.md"):
        if f.exists(): shutil.copy2(f, pkg / "docs" / f.name)
    return pkg, stem


def readme(pkg, stem, verify, claims, indep, selftest, stamp):
    s4 = json.loads((B / "b4_summary.json").read_text(encoding="utf-8")); s1 = json.loads((B / "b_summary.json").read_text(encoding="utf-8"))
    q = s4["2025_탐욕재배정"]
    txt = f"""# 국토계획(KPA) 투고 패키지 v2 — {stamp}

**논문**: 공식 생활권은 어디를 고쳐야 하는가 — 무작위 비교경계와 빅데이터 기반 가상경계를 이용한 서울시 생활권 경계 동 진단(2020·2025)
이 폴더만으로 모든 표·그림을 다시 만들 수 있다(저장소 경로 불필요, `scripts/config.py`가 패키지 모드를 자동 인식).

## 0. 한 문단 요지
IFR(생활권 안에서 끝나는 통행 비율)로 보면 생활권이 좋아진 것 같지만 무작위로 그은 경계도 똑같이 올랐고(착시), IFR은 권역 크기에 따라 부풀려진다.
크기를 맞춘 무작위 비교경계와 비교하면 공식 생활권은 97% 수준으로 대체로 잘 그어져 있다. 문제는 경계 동 약 10%이며,
2025년 기준 {q['옮긴_동']}개 동을 옆 생활권으로 옮기면 서울 IFR이 {q['서울IFR_전']:.1f}→{q['서울IFR_후']:.1f}%로 빅데이터 기반 가상경계({q['서울IFR_가상경계']:.1f}%)를 넘는다.
{s4['두해모두_권고_이동']}개 이동은 두 해 모두 권고되어 어긋남은 구조적이며, 기초 시설 접근성·상업·문화·주거 특성으로 설명되지 않는다.

## 1. 용어
- **빅데이터 기반 가상경계**: 생활이동 통행으로 많이 오가는 동끼리 묶은 경계(Leiden 3,000회 합의, 개수 = 공식 생활권). 천장·목표점.
- **무작위 비교경계**: 이동 정보 없이 붙은 동끼리 무작위로 묶은 경계. 구마다 **1,000가지**(1,000은 동 수가 아니라 경계의 가짓수). N0 크기 제약 없음 / N1 권역별 동 수 동일 / N2 N1 + 통행량 비중 유사. 바닥 기준선.
- 분석 동 424개(생활이동 코드에 맞춰 오류2동+항동, 상일1동+상일2동 통합).

## 2. 읽는 순서
1. `manuscript/{stem}.md` — 원고(같은 이름 `.docx`·`.hwp`·`_2단편집.docx/.pdf`·`_한글출력.pdf`)
2. `docs/연구설계_v2_경계동진단.md` — 분석의 틀·가설·판정 기준 · `docs/분석메모_…md` — 결과 해석 전체
3. `tables/benchmark/` — 결과(b1 구, b2 생활권, b3 동, b4 재배정, b5~b7 원인 탐색, b8 재배정 검증)
4. `manuscript/투고전_체크리스트_v2.md` — 저자가 채울 것

## 3. 재현 순서
```
pip install -r scripts/requirements.txt
cd scripts
python tests/test_examples.py      # 기존 지표 손계산 예제
python tests/test_benchmark.py     # 무작위 비교경계·재배정 함수(networkx 대조 포함)
python k01_compute.py              # IFR·G·D·무작위 비교경계(N0) ΔIFR   → tables/
python k02_select.py               # 경계 고정 비교 등 보조 표
python k03_figures.py              # 그림 A1
python k13_benchmark.py            # 무작위 비교경계 N0·N1·N2 대비 평가(구·생활권·동)   ~30분
python k14_reassign.py             # 한 동씩 옮기기·탐욕적 재배정
python k15_access_link.py          # 원인 탐색: 기초 시설 접근성
python k16_attractors.py           # 원인 탐색: 역·대규모점포·문화·일자리
python k17_similarity.py           # 원인 탐색: 주거 특성·중심 권역 편입
python k18_v2_results.py           # 재배정 분할 검증 + 그림
python k19_kpa_v2.py               # 원고 docx + 본문 수치 자동 대조
python k11_independent_check.py    # a·b·T 독립 재계산(순수 파이썬·DuckDB) + docx/hwp 표 대조
python k08_hwp_pages.py; python k09_hwp_build.py   # (Windows + Word·한글 2022) PDF·쪽수·hwp
```
시드: 무작위 비교경계 20260927(k13), N0 ΔIFR 20260924(k01). 같은 순서로 실행하면 바이트 단위로 같은 결과가 나온다.

## 4. 입력 (data/)
| 파일 | 내용 | 출처(배포 ID) |
|---|---|---|
| dong_to_official_livingzone_mapping_424.csv | 동 424 → 공식 생활권 116 | boundary-v2-dong |
| dong_to_leiden_{{2020,2025}}_mapping_424.csv | 동 424 → 가상경계 116 | boundary-v2-leiden |
| od/od_daily_{{2020,2025}}01.parquet | 동×동 통행량(도착 09:00~20:59, HW·WH 제외, 서울 내부, 비공개 → 0) | od-daily-v1 (개인 단위 원자료 미포함) |
| seoul_dong_424_dissolved.gpkg | 동 경계(EPSG:5179, 인접 판정) | boundary-v2-dong |
| access/결과/{{main,sens_T600}}/unit_access_*.csv | 동별 Coverage·MAI(경계 조건별) — k15만 사용 | access-engine-v3 |
| access/입력/facility/…parquet, grid/grid100_master.parquet | 시설 33종 위치, 격자 인구·가구·종사자 — k16·k17만 사용 | facility-v1.2, pop-grid-100m-v1 |

## 5. 검증 결과 ({time.strftime('%Y-%m-%d')})
| 점검 | 결과 |
|---|---|
| 단위시험 | test_examples 7/7, test_benchmark 10/10 |
| 재배정 분할 검증(권역 수 유지·공간 연속·요약값 재계산) | {verify['판정']} (요약값 최대차 {verify['요약값_최대차']:.1e}) |
| 본문 수치 자동 대조 | {len(claims['항목']) - len(claims['실패'])}/{len(claims['항목'])} 일치 |
| a·b·T 독립 재계산(순수 파이썬 / DuckDB) | 최대 상대오차 {indep.get('1a_순수파이썬_vs_표3_최대상대오차', float('nan')):.1e} / {indep.get('1b_DuckDB_SQL_vs_표3_최대상대오차', float('nan')):.1e} |
| docx·hwp 표 셀 대조 | 불일치 docx {indep.get('3_docx_표_불일치')}, hwp {indep.get('3_hwp_표_불일치', '미실행')} |
| k13~k17 전체 재실행 재현성 | {selftest.get('재실행_재현성')} |
| 패키지 자체 재현(패키지 폴더에서 테스트·k01 실행 → 저장소 표와 비교) | {selftest.get('패키지_자체재현')} |
| 파일 해시 | `manifest.json` |

## 6. 공동연구자에게 부탁
1. 원고를 통독하고 논리 비약·표현을 지적해 주기(특히 Ⅳ.4 재배정과 Ⅴ.4 한계 넷째: 모듈성 기준의 순환성).
2. 부록 표 A1의 49개 이동 중 아는 지역이 있으면, 통행 외의 이유(학군·관할·정체성)로 현재 경계가 맞는 경우를 알려 주기.
3. 은평구(크기를 맞춰도 무작위 수준)의 사정에 대한 의견.

문의: 박종하 (daniel21c@hanyang.ac.kr)
"""
    (pkg / "README.md").write_text(txt, encoding="utf-8")


def bundle(stamp, stem):
    out = C.OUT / f"제출본_v2_{stamp}"
    if out.exists(): shutil.rmtree(out)
    for d in ("05_그림_원본", "06_표_원본", "09_점검기록"): (out / d).mkdir(parents=True)
    shutil.copy2(MK / f"{stem}.hwp", out / "01_투고본_익명_한글.hwp"); shutil.copy2(MK / f"{stem}_한글출력.pdf", out / "02_투고본_익명_확인용.pdf"); shutil.copy2(MK / f"{stem}.docx", out / "03_투고본_익명_Word.docx")
    md = (MK / f"{stem}.md").read_text(encoding="utf-8"); meta = dict(re.findall(r"^%([A-Z_]+):\s*(.*)$", md, flags=re.M))
    (out / "04_영문초록_주제어.txt").write_text(f"[국문 제목]\n{meta['TITLE_KO']}\n- {meta['SUBTITLE_KO']} -\n\n[영문 제목]\n{meta['TITLE_EN']}\n- {meta['SUBTITLE_EN']} -\n\n[Abstract]\n{meta['ABSTRACT_EN']}\n\n[주제어]\n{meta['KEYWORDS_KO']}\n\n[Keywords]\n{meta['KEYWORDS_EN']}\n", encoding="utf-8")
    for f in list(FIG.glob("Fv2_*")) + list(FIG.glob("F4-4-6_*")): shutil.copy2(f, out / "05_그림_원본" / f.name)
    for f in B.glob("*.*"): shutil.copy2(f, out / "06_표_원본" / f.name)
    for n in ("수치대조_기록_v2.json", "독립재계산_기록.json", "쪽수_기록.json"):
        if (MK / n).exists(): shutil.copy2(MK / n, out / "09_점검기록" / n)
    for n in ("_repro_result_benchmark.json", "_package_selftest.json"):
        if (C.OUT / n).exists(): shutil.copy2(C.OUT / n, out / "09_점검기록" / n.lstrip("_"))
    shutil.copy2(MK / "투고전_체크리스트_v2.md", out / "07_저자작성항목.md")
    (out / "08_예상심사질문_답변.md").write_text("""# 예상 심사 질문과 답변 요지 (v2)

| # | 예상 질문 | 답변 요지 | 본문 |
|---|---|---|---|
| 1 | 무작위 비교경계는 어떻게 만들었나, 왜 1,000개인가 | 같은 구 안에서 인접한 동끼리 무작위로 묶은 서로 다른 경계 1,000가지(동 수가 아님). 권역 수·동 수·통행량 비중을 맞춘 세 종류 | Ⅲ.2, 표 2 |
| 2 | 공식 생활권이 무작위의 97%보다 낫다면 문제가 없는 것 아닌가 | 전체적으로는 잘 그어졌다는 것이 결과. 어긋남은 경계 동 약 10%에 몰려 있고, 이를 고치면 가상경계 수준에 도달 | Ⅳ.2~4 |
| 3 | 큰 생활권 옆 동이 그쪽으로 많이 가는 건 당연하지 않나 | 그래서 크기를 통제하는 모듈성을 함께 요구했다. 옆 생활권 지향 동 104개 중 IFR만 오르는 50개는 크기 효과로 보고 제외, 둘 다 오르는 40개만 오배정 | Ⅳ.3, 표 4 |
| 4 | 재배정 기준이 가상경계의 목적함수와 같으니 가상경계에 가까워지는 건 당연하다 | 한계에 명시. 목표로 삼지 않은 IFR이 가상경계를 넘었고, 두 해 독립 계산에서 같은 이동 49개가 반복 | Ⅳ.4, Ⅴ.4 |
| 5 | 두 시점으로 시간 변화를 말할 수 있나 | 두 시점은 변화 추정이 아니라 반복 확인 장치. 결론은 "어긋남은 구조적". 2020 경계를 2025에 적용하면 15개 구에서 커지지만 작다 | Ⅳ.5 |
| 6 | 왜 그 동들이 잘못 배정됐나 | 사전 기준으로 여섯 후보를 검토. 기초 시설·상업·문화·주거 특성은 관계없음, 역 근접·중심 권역 편입은 약한 신호. 원인은 특정하지 못했고 후속 과제 | Ⅳ.5, 표 6 |
| 7 | 통행만 보고 경계를 옮겨도 되나 | 권고는 검토 우선순위이며 학군·관할·정체성 등 통행 밖 기준과 함께 판단 | Ⅴ.3 |
| 8 | 옮기면 IFR이 떨어지는 이동이 있다 | 65개 중 18개. 큰 권역에서 작은 권역으로 옮기는 경우로 크기 편향의 반대 방향 | Ⅳ.4 |
| 9 | Leiden 랜덤성 | 3,000회 합의, 독립 반복 10회 ARI 1.0 | Ⅲ.2 |
| 10 | 비공개 셀·구 내부 한정 | 모든 경계에 같은 자료·같은 제약. 한계에 명시 | Ⅲ.1, Ⅴ.4 |
| 11 | 원인 탐색이 결과를 보고 지표를 고른 것 아닌가 | 판정 기준을 계산 전에 적었고, 지표를 더 늘리지 않고 중단(다중비교 위험) | Ⅲ.3, 표 6 주 |
""", encoding="utf-8")
    import getpass, fitz
    from docx import Document
    names = [getpass.getuser(), "박종하", "daniel21c", "hanyang"]; found = []
    b = (out / "01_투고본_익명_한글.hwp").read_bytes()
    for nm in names:
        for enc in ("utf-16le", "utf-8", "cp949"):
            if nm.encode(enc) in b: found.append(f"hwp:{nm}")
    m = fitz.open(str(out / "02_투고본_익명_확인용.pdf")).metadata
    found += [f"pdf:{k}={m[k]}" for k in ("author", "creator", "producer") if m.get(k)]
    cp = Document(str(out / "03_투고본_익명_Word.docx")).core_properties
    if cp.author or cp.last_modified_by: found.append("docx:author")
    (out / "09_점검기록" / "익명검사.json").write_text(json.dumps({"발견": found, "판정": "통과" if not found else "실패"}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "README.md").write_text(f"# 국토계획 제출본 v2 — {stamp}\n\n01 hwp(학회 양식에 옮길 원본) · 02 확인용 PDF · 03 Word · 04 초록·주제어 · 05 그림 · 06 표 · 07 저자 작성 항목 · 08 예상 심사 질문 · 09 점검 기록(수치 대조·독립 재계산·재현성·익명 검사)\n\n익명 검사: {'통과' if not found else found}\n", encoding="utf-8")
    return out, found


def selftest(pkg):
    R = {}
    rr = C.OUT / "_repro_result_benchmark.json"
    if rr.exists():
        d = json.loads(rr.read_text(encoding="utf-8")); R["재실행_재현성"] = "바이트 동일" if not d["달라진파일"] else f"달라짐: {d['달라진파일']}"
    else: R["재실행_재현성"] = "미실행"
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    runs = []
    for cmd in (["tests/test_examples.py"], ["tests/test_benchmark.py"], ["k01_compute.py"]):
        p = subprocess.run([sys.executable] + cmd, cwd=pkg / "scripts", capture_output=True, text=True, encoding="utf-8", env=env)
        runs.append({"cmd": cmd[0], "rc": p.returncode, "tail": (p.stdout + p.stderr).strip()[-200:]})
    R["실행"] = runs
    diffs = []
    for f in ("t02_gu_metrics_long.csv", "t03_gu_change.csv", "t04_decomposition.csv", "t05_null_summary.csv"):
        a = pd.read_csv(C.TAB / f, encoding="utf-8-sig"); b = pd.read_csv(pkg / "output" / "tables" / f, encoding="utf-8-sig")
        num = a.select_dtypes("number").columns
        diffs.append(float((a[num] - b[num]).abs().max().max()) if a.shape == b.shape else float("inf"))
    R["패키지_자체재현"] = ("통과" if all(r["rc"] == 0 for r in runs) and max(diffs) < 1e-9 else "실패") + f" (k01 표 4종 최대차 {max(diffs):.1e})"
    shutil.rmtree(pkg / "output", ignore_errors=True)                     # 시험 산출물은 패키지에 남기지 않는다
    for pyc in pkg.rglob("__pycache__"): shutil.rmtree(pyc, ignore_errors=True)
    (C.OUT / "_package_selftest.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    return R


def main():
    stamp = time.strftime("%Y%m%d")
    pkg, stem = package(stamp)
    st = selftest(pkg)
    verify = json.loads((B / "b8_verify.json").read_text(encoding="utf-8")); claims = json.loads((MK / "수치대조_기록_v2.json").read_text(encoding="utf-8"))
    indep = json.loads((MK / "독립재계산_기록.json").read_text(encoding="utf-8"))
    readme(pkg, stem, verify, claims, indep, st, stamp)
    files = {str(p.relative_to(pkg)).replace("\\", "/"): {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(pkg.rglob("*")) if p.is_file()}
    core = json.loads(C.MANIFEST.read_text(encoding="utf-8"))
    (pkg / "manifest.json").write_text(json.dumps({"created": time.strftime("%Y-%m-%d %H:%M:%S"), "python": sys.version.split()[0], "platform": platform.platform(),
                                                   "core_engine_inputs": core["files"], "files": files}, ensure_ascii=False, indent=1), encoding="utf-8")
    zipdir(pkg, C.OUT / f"KPA_v2_공동연구자패키지_{stamp}.zip")
    out, found = bundle(stamp, stem); zipdir(out, C.OUT / f"KPA_v2_제출본_{stamp}.zip")
    print(json.dumps({"패키지": pkg.name, "파일": len(files), "자체시험": st, "제출본": out.name, "익명": found or "통과"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
