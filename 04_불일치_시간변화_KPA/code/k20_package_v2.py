# -*- coding: utf-8 -*-
"""
k20 — KPA 확정본 공동연구자 패키지 + 제출본 묶음 + 패키지 자체 재현 시험

A. package/package_kpa_final_<날짜>/   공동연구자용(자기완결): README · manuscript · tables · figures · scripts · data · docs · manifest
B. output/제출본_final_<날짜>/        투고 시스템에 올릴 것과 저자 확인 항목·예상 심사 질문·점검 기록
C. 패키지 자체 재현 시험: 패키지 폴더에서 단위시험, k01, k25, 원고 수치 대조를 실행해(저장소 경로 없이) 저장소 결과와 같은지 확인
실행: python k20_package_v2.py   (k13·k14·k25·k18·k19·k08·k22·k11·k23 먼저)
"""
from __future__ import annotations
import hashlib, json, os, platform, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path
import pandas as pd
import config as C

MK = C.MK; FIG = C.FIG; B = C.TAB / "benchmark"
KEEP_SCRIPTS = ["config.py", "kpa_metrics.py", "k01_compute.py", "k06_kpa_submission.py", "k08_hwp_pages.py", "k11_independent_check.py",
                "k13_benchmark.py", "k14_reassign.py", "k18_v2_results.py", "k19_kpa_v2.py", "k20_package_v2.py", "k21_raw_integrity.py",
                "k22_hwp_kpa.py", "k23_repro_check.py", "k24_text_claims.py", "k25_change_story.py", "run_submission.bat", "requirements.txt"]
DATE = "20260930"
SUB = "국토계획_투고본_{}_" + DATE          # k22 출력(심사용·저자정보)
DESIGN = C.ROOT / "연구설계.md"
DOCS = {"투고전_체크리스트_v2.md": C.ROOT / "KPA_투고서식_체크리스트_20260930.md", "외부검토_대응표_20260930.md": C.ROOT / "검수의견_대응표_20260930.md",
        "구성변경_대조표_20260930.md": C.ROOT / "구성변경_대조표_20260930.md"}   # 패키지 안 이름 → 저장소 최상위 문서(2026-09-30 폴더 정리 뒤)


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
    pkg = C.PKG / f"package_kpa_final_{stamp}"
    if pkg.exists(): shutil.rmtree(pkg)
    for d in ("manuscript", "templates", "tables/integrity", "tables/benchmark", "figures", "scripts/tests", "data/od", "docs"):
        (pkg / d).mkdir(parents=True, exist_ok=True)
    for n in KEEP_SCRIPTS: shutil.copy2(C.HERE / n, pkg / "scripts" / n)
    for f in (C.HERE / "tests").glob("*.py"): shutil.copy2(f, pkg / "scripts" / "tests" / f.name)
    for src in (C.LZ_MAP, C.ld_map(C.Y0), C.ld_map(C.Y1), C.DONG_GPKG, C.MANIFEST): shutil.copy2(src, pkg / "data" / src.name)
    for y in C.YEARS:
        shutil.copy2(C.od_daily(y), pkg / "data" / "od" / C.od_daily(y).name); shutil.copy2(C.od_summary(y), pkg / "data" / "od" / C.od_summary(y).name)
        shutil.copy2(B / f"b9_type_agg_{y}.csv", pkg / "data" / "od" / f"b9_type_agg_{y}.csv")      # od_full 대신 k25용 집계표
    shutil.copy2(C.CORE / "scripts" / "config.py", pkg / "data" / "core_config.py")
    for f in C.TAB.glob("*.*"): shutil.copy2(f, pkg / "tables" / f.name)
    for f in B.glob("*.*"): shutil.copy2(f, pkg / "tables" / "benchmark" / f.name)
    for f in (C.TAB / "integrity").glob("*.*"): shutil.copy2(f, pkg / "tables" / "integrity" / f.name)
    for f in (C.ROOT / "templates").glob("*.*"): shutil.copy2(f, pkg / "templates" / f.name)
    for f in FIG.glob("Fv2_*"): shutil.copy2(f, pkg / "figures" / f.name)
    for nm in ("심사용", "저자정보"):
        for ext in (".hwp", ".pdf"):
            f = MK / (SUB.format(nm) + ext)
            if f.exists(): shutil.copy2(f, pkg / "manuscript" / f.name)
    stem = sorted(MK.glob("국토계획_원고_*.md"))[-1].stem
    for f in list(MK.glob(f"{stem}*")) + list(C.DOCX.glob(f"{stem}*")): shutil.copy2(f, pkg / "manuscript" / f.name)
    for n in ("수치대조_기록_v2.json", "독립재계산_기록.json", "쪽수_기록.json"):
        if (MK / n).exists(): shutil.copy2(MK / n, pkg / "manuscript" / n)
    for n, src in DOCS.items():
        if src.exists(): shutil.copy2(src, pkg / "manuscript" / n)
    shutil.copy2(DESIGN, pkg / "docs" / DESIGN.name); (pkg / "docs" / "예상심사질문_답변.md").write_text(QNA, encoding="utf-8")
    return pkg, stem


def readme(pkg, stem, verify, claims, indep, selftest, stamp):
    ri = json.loads((C.TAB / "integrity" / "raw_integrity.json").read_text(encoding="utf-8"))
    raw = ("통과" if ri["all_pass"] else "실패") + " — " + ", ".join(
        f"{y}: 원자료 CSV 해시 {ri[y]['raw_hash']['match']}/24, 원자료→OD 재구성 {ri[y]['rebuild_daily']['pairs_rebuilt']:,}쌍 일치" for y in C.YEARS)
    s4 = json.loads((B / "b4_summary.json").read_text(encoding="utf-8")); s9 = json.loads((B / "b9_change_story.json").read_text(encoding="utf-8"))
    q = s4["2025_탐욕재배정"]; G = s9["G확대"]; U = s9["유형분해"]; Sd = json.loads((C.TAB / "results.json").read_text(encoding="utf-8"))["seoul"]
    md = (MK / f"{stem}.md").read_text(encoding="utf-8"); title = re.search(r"^%TITLE_KO: (.*)$", md, flags=re.M).group(1); sub = re.search(r"^%SUBTITLE_KO: (.*)$", md, flags=re.M).group(1)
    txt = f"""# 국토계획(KPA) 투고 — 확정본 공동연구자 패키지 ({stamp})

**논문**: {title} — {sub}
이 폴더만으로 원고의 모든 표·그림·수치를 다시 만들 수 있다(저장소 경로 불필요, `scripts/config.py`가 패키지 모드를 자동 인식).

## 0. 한 문단 요지
2020년에서 2025년 사이 서울 기존 생활권의 내부통행률(IFR)은 모든 자치구에서 올랐다. 그러나 무작위로 그은 경계도 같은 범위로 올랐고, 상승분의 {U['유형내_비중'] * 100:.0f}%는 통행 구성의 변화가 아니라 각 유형의 통행이 생활권 안에 머무는 비율이 높아진 결과였으며(거리 단축을 확인한 것은 아님) 상승 폭은 주말에 더 컸다.
같은 기간 기존 생활권과 데이터 기반 커뮤니티의 불일치 D는 {Sd['2020']['D'] * 100:.1f}%에서 {Sd['2025']['D'] * 100:.1f}%로 소폭 낮아졌으나 자치구별 변화 방향은 일관되지 않았고(부호검정 비유의), 내부통행률 격차 G는 {G['G2020'] * 100:.2f}%p에서 {G['G2025'] * 100:.2f}%p로 벌어졌으며 그 절반가량({G['통행몫_평균'] * 100:.0f}%)이 통행 변화에서 왔다.
권역 크기를 맞춘 무작위 경계와 견주면 기존 생활권은 통행 기준으로 잘 그어져 있고(구별 백분위 중앙값 97, 24/25 구), 통행 지표상 재검토 후보는 일부 경계 동에 한정되며 두 해에 같은 재배정이 반복된다({s4['두해모두_권고_이동']}개 동). 별도의 순차 재배정에서 일부 경계 동의 소속만 바꾸면(2025년 {q['옮긴_동']}개 동) 서울 IFR이 {q['서울IFR_전']:.1f}→{q['서울IFR_후']:.1f}%로 커뮤니티({q['서울IFR_가상경계']:.1f}%)와 비슷해지고 D는 {q['서울D_전']:.1f}→{q['서울D_후']:.1f}%로 준다.
결론: 내부통행률의 상승을 생활권 불일치의 해소로 해석해서는 안 되며, 재정비는 지목된 경계 동의 검토에서 출발할 수 있다.

## 1. 용어
- **IFR(내부통행률, 내부통행률)**: 동에서 출발한 서울 내부 통행 중 같은 권역 안에서 끝나는 통행의 비율(동 내부통행 포함, 구를 넘는 통행은 외부).
- **데이터 기반 커뮤니티**: 같은 해 생활이동 통행으로 도출한 경계(자치구 내 Leiden 3,000회 합의, 개수 = 기존 생활권). 기존 생활권을 대체하는 안이 아니라 비교 기준.
- **무작위 경계**: 이동 정보 없이 인접한 동을 무작위로 묶은 경계. 자치구마다 1,000번 추출(중복 허용). N0 권역 수만 / N1 권역별 동 수 동일 / N2 N1 중 통행량 비중이 비슷한 것. 바닥 기준선.
- **불일치 D**: 두 경계가 권역 안/밖을 다르게 판정한 통행의 비율. **내부통행률 격차 G** = 커뮤니티 IFR − 기존 생활권 IFR.

## 2. 읽는 순서
1. `manuscript/국토계획_투고본_심사용_{DATE}.hwp·.pdf` — 투고용(학회 샘플 양식, 익명). `…_저자정보_…` — 저자·소속·이메일 포함본(심사 업로드용 아님)
2. `manuscript/{stem}.md` — 원고 원문(같은 이름 `.docx`는 검토용 Word)
3. `docs/{DESIGN.name}` — 확정 설계(질문·분석 틀·판정 기준·결과 요약)
4. `manuscript/투고전_체크리스트_v2.md` — 저자·교신저자가 확인할 것
5. `manuscript/외부검토_대응표_20260930.md` — AI 대조 점검(2026-09-30, 1·2차) 지적 항목별 반영·미반영과 그 이유
6. `docs/예상심사질문_답변.md` — 예상 심사 질문 15개와 답변 요지
7. `manuscript/구성변경_대조표_20260930.md` — 2026-09-30 구성 변경(질문 순서 정렬)의 옛 절 → 새 절 대조표. 대응표의 '위치'는 옛 절 번호다

## 3. 재현 순서
이 패키지가 재현하는 범위는 집계 OD와 확정 경계(공식·가상) 이후의 계산이다. 원자료 CSV 집계와 커뮤니티 도출(자치구 내 Leiden 3,000회 합의)은 별도 저장소 `00_공통_코어엔진`에 있으며 이 ZIP만으로는 재현되지 않는다.
```
pip install -r scripts/requirements.txt
cd scripts
python tests/test_examples.py      # 지표 손계산 예제
python tests/test_benchmark.py     # 무작위 경계·재배정·백분위 함수
python k01_compute.py              # IFR·G·D·무작위 경계(N0) ΔIFR·G 분해     → results/
python k13_benchmark.py            # 무작위 경계 N0·N1·N2 대비 평가(구·생활권·동)   ~30분
python k14_reassign.py             # 한 동씩 옮기기·순차 재배정·고정경계 평가·대안 분모
python k25_change_story.py         # 내부통행률 상승의 유형 분해·주말 비교, D·G 변화 검정과 G 분해
python k18_v2_results.py           # 재배정 분할 검증 + 표·그림
python k19_kpa_v2.py               # 원고 docx + 원고 본문 수치 대조(k24)·변조 시험·구조 점검
python tests/test_text_claims.py   # 원고 숫자를 바꾸면 반드시 실패하는지
python k11_independent_check.py    # a·b·T 독립 재계산 + docx/hwp 표 셀 대조
python k22_hwp_kpa.py both         # (Windows + 한글 2022) 학회 샘플 위 투고본 hwp·pdf
python k23_repro_check.py          # k13·k14·k25·k18 재실행 재현성(약 35분)
python k21_raw_integrity.py        # (원자료가 있을 때만) 원자료 CSV 48개 해시·원자료→OD 재구성
```
시드: 무작위 경계 20260927(k13), N0 ΔIFR 20260924(k01). 같은 순서로 실행하면 csv는 바이트 단위로, json은 실행 시간 항목을 뺀 내용이 같다.

## 4. 입력 (data/)
| 파일 | 내용 | 출처 |
|---|---|---|
| dong_to_official_livingzone_mapping_424.csv | 동 424 → 기존 생활권 116 | 코어엔진 boundary-v2-dong |
| dong_to_leiden_{{2020,2025}}_mapping_424.csv | 동 424 → 커뮤니티 116 | 코어엔진 boundary-v2-leiden |
| od/od_daily_{{2020,2025}}01.parquet | 동×동 통행량(도착 09:00~20:59, HW·WH 제외, 서울 내부, 비공개 → 0) | 코어엔진 od-daily-v1 |
| od/b9_type_agg_{{2020,2025}}.csv | 구 × 이동유형 × 평일/주말 통행 집계(od_full에서 k25가 만든 것; od_full은 용량 때문에 미포함) | k25 |
| seoul_dong_424_dissolved.gpkg | 동 경계(EPSG:5179, 인접 판정) | 코어엔진 |

## 5. 검증 결과 ({time.strftime('%Y-%m-%d')})
| 점검 | 결과 |
|---|---|
| 원자료 무결성 | {raw} |
| 단위시험 | test_examples, test_benchmark(백분위 회귀시험 포함), test_text_claims(원고 변조 시험) 통과 |
| 재배정 분할 검증(권역 수 유지·공간 연속·요약값 재계산) | {verify['판정']} (요약값 최대차 {verify['요약값_최대차']:.1e}) |
| 원고 본문 수치 대조(원고 문장의 숫자 ↔ 결과 파일, 절·문맥 단위) | {claims['원고_수치_대조']['일치']}/{claims['원고_수치_대조']['주장수']} 일치 |
| 변조 시험(주장마다 숫자 변경·문장 삭제 시 실패하는지) | 숫자 변경 {claims['변조_시험']['숫자변조_감지']}/{claims['변조_시험']['숫자변조']}, 삭제 {claims['변조_시험']['삭제_감지']}/{claims['변조_시험']['삭제']} 감지 |
| 구조 점검(재배정 검증·표·초록 무수치·인용) | {len(claims['항목']) - len(claims['실패'])}/{len(claims['항목'])} 통과 |
| a·b·T 독립 재계산(순수 파이썬 / DuckDB) | 최대 상대오차 {indep.get('1a_순수파이썬_vs_표3_최대상대오차', float('nan')):.1e} / {indep.get('1b_DuckDB_SQL_vs_표3_최대상대오차', float('nan')):.1e} |
| docx·hwp 표 셀 대조 | 불일치 docx {indep.get('3_docx_표_불일치')}, hwp {indep.get('3_hwp_표_불일치', '미실행')} |
| 재실행 재현성(csv 바이트·json 정규화) | {selftest.get('재실행_재현성')} |
| 패키지 자체 재현(패키지 폴더에서 테스트·k01·k25·원고 대조) | {selftest.get('패키지_자체재현')} |
| 파일 해시 | `manifest.json` |

## 6. 공동연구자에게 부탁
1. 원고를 통독하고 논리 비약·표현을 지적해 주기(특히 Ⅱ 선행연구의 차별성 서술, Ⅴ.4 한계 넷째: 재배정과 커뮤니티가 같은 모듈러리티 기준을 쓰는 점).
2. 부록 표 A1의 {s4['두해모두_권고_이동']}개 재배정 중 아는 지역이 있으면, 통행 외의 이유(학군·관할·정체성)로 현재 경계가 맞는 경우를 알려 주기.
3. 제목과 초록이 학회지 성격에 맞는지, 하정원 외(2024)·커뮤니티 방법 선행 논문과의 차별성이 충분히 드러나는지 의견.

문의: 박종하 (daniel21c@hanyang.ac.kr)
"""
    (pkg / "README.md").write_text(txt, encoding="utf-8")


QNA = """# 예상 심사 질문과 답변 요지 (확정본)

| # | 예상 질문 | 답변 요지 | 본문 |
|---|---|---|---|
| 1 | 하정원 외(2024)와 무엇이 다른가 | 그 연구는 코로나19 전후 기능적 생활권을 새로 그어 비교하고 기존 상위 권역과의 차이를 논의했다. 이 연구는 116개 지역생활권 전체를 대상으로 크기 조건을 맞춘 무작위 기준선, G·D의 구분, 행정동 단위 재검토 후보 진단과 재배정 효과를 결합한다 | Ⅱ.5 |
| 2 | 커뮤니티 방법은 기존 연구와 같지 않은가 | 선행연구(Park et al., 2026; 생활이동 2025년 3월, Louvain·Leiden 3,000회, 공식 116개와 비교)에 바탕을 둔 절차이며 Ⅲ.1의 2)에 인용하고 비교 기준으로만 쓴다고 밝혔다. 이 연구는 2020년 1월·2025년 1월 두 시점, Leiden 합의 분할, 무작위 기준선, 시간 변화가 다르다. 이 논문의 기여는 기존 경계의 평가(무작위 기준선), 불일치의 추적(D·G와 G 분해), 경계 동 진단과 재배정이다(편집위원회에 재사용 범위 고지) | Ⅲ.1 |
| 3 | IFR 상승은 누구나 예상하는 국지화 아닌가 | 그래서 무작위 경계와 비교했다. 상승이 기존 경계에 특유하지 않다는 것, 각 유형 안에서 생활권 내부 비율이 높아진 것이며 주말에 더 컸다는 것을 보인 뒤, 그럼에도 불일치가 유의하게 줄지 않았다는 점이 핵심이다 | Ⅳ.2~3 |
| 4 | 격차 확대는 커뮤니티를 새로 그었기 때문 아닌가 | G 변화를 통행 변화와 커뮤니티 재도출로 분해했다. 통행 변화 몫이 절반가량(순서에 따라 35~72%)이고, 통행 변화 몫이 격차를 키운 구가 16:5로 많다 | Ⅳ.3, 표 4 |
| 5 | 재배정 기준이 커뮤니티와 같으니(모듈러리티) 가까워지는 건 당연하다 | 한계에 독립 검증이 아님을 명시했다. 보조 근거: 2020년 자료로 정한 재배정 경계를 2025년 통행에 다시 최적화하지 않고 적용해도 22개 구 중 모듈러리티 19개, D 18개 구에서 개선되고, 두 해의 재배정이 48개 동에서 같다 | Ⅳ.4, Ⅴ.5 |
| 6 | 크기를 맞춘 무작위와 비교하면 97이라는데 불일치가 문제인가 | 전반적 적합성과 국지적 재검토는 다른 문제다. 기존 생활권의 IFR은 크기를 맞춘 무작위보다 대체로 높지만, 전체 424개 동의 8~9%가 단일 이동 진단의 재검토 후보로 식별되었다. 별도의 순차 재배정에서는 각 해 65개 동의 최종 소속이 바뀌었으며, 48개 동은 '원래 → 최종' 생활권 조합이 두 해에 같았다 | Ⅳ.4 |
| 7 | 큰 생활권 옆 동이 그쪽으로 많이 가는 건 당연하지 않나 | 기대 연결량을 보정하는 모듈러리티이 함께 오를 때만 재검토 후보로 보았다. 옆 생활권 지향 동의 상당수는 크기 효과로 제외된다 | Ⅳ.4, 표 5 |
| 8 | 통행만 보고 경계를 옮겨도 되나 | 권고는 검토의 출발점이며 학군·행정 관할·정체성 등 통행 밖 기준과 함께 판단한다 | Ⅴ.4 |
| 9 | 왜 그 동들이 어긋나는가 | 이 연구의 범위 밖이며 후속 과제로 남겼다(생활중심지–배후주거지 설정 방식, 역세권 영향이 후보) | Ⅴ.5 |
| 10 | 두 시점(1월)만으로 충분한가, 분모 정의는 | 계절성·중간 시기는 한계로 명시. 같은 구·자기 동 제외 분모로 계산해도 재배정 후 개선 방향은 같다 | Ⅴ.5 |
| 11 | Leiden 랜덤성 | 해상도마다 3,000회 합의, 시드를 달리한 독립 반복 10회에서 합의 분할이 같음(ARI 1.0) | Ⅲ.1 |
| 12 | 무작위 백분위는 가능한 모든 분할에 대한 확률인가 | 아니다. 이 연구의 생성 절차로 얻은 표본(구마다 1,000회, 중복 허용) 안에서의 순위다. N2는 고유 분할이 적은 구가 있어 보조 분석이다. 절대적 우수성이나 계획적 타당성 확률로 읽지 않는다 | Ⅲ.1, Ⅴ.5, 표 2 주 |
| 13 | 구별 부호검정 p값이 서울 전체 지표의 변화를 검정한 것인가 | 아니다. 구별 증가·감소 방향의 검정이며 자치구 간 독립을 전제로 한다. 서울 전체 통행가중 D·G의 변화는 기술값으로 따로 보고한다 | Ⅲ.4, Ⅳ.3, Ⅴ.5 |
| 14 | 기존 생활권은 원래 경계 그대로인가 | 최대 면적 중첩으로 424개 행정동에 대응시킨 경계다(최솟값 0.51). 중첩이 낮은 동에서는 원 경계와 차이가 있을 수 있으므로 재검토 후보를 곧바로 실제 경계의 오류로 부르지 않는다 | Ⅲ.1 |
| 15 | 65개 동 변경이 불일치를 줄이는 데 필요한 최소 변경 수인가 | 아니다. 65개는 모듈러리티 증가 기준 순차 재배정의 결과이며 바꿀 동의 수를 최소화하도록 설계한 것이 아니다. 최소 변경안이나 반드시 시행할 재배정 규모로 해석하지 않는다 | Ⅳ.4 |
"""


def bundle(stamp, stem):
    out = C.PKG / f"제출본_final_{stamp}"
    if out.exists(): shutil.rmtree(out)
    for d in ("05_그림_원본", "06_표_원본", "09_점검기록", "10_저자정보포함본_심사업로드금지"): (out / d).mkdir(parents=True)
    shutil.copy2(MK / (SUB.format("심사용") + ".hwp"), out / "01_투고본_심사용_익명.hwp"); shutil.copy2(MK / (SUB.format("심사용") + ".pdf"), out / "02_투고본_심사용_익명_확인용.pdf")
    shutil.copy2(C.DOCX / f"{stem}.docx", out / "03_검토용_Word_익명.docx")
    for ext in (".hwp", ".pdf"): shutil.copy2(MK / (SUB.format("저자정보") + ext), out / "10_저자정보포함본_심사업로드금지" / (SUB.format("저자정보") + ext))
    md = (MK / f"{stem}.md").read_text(encoding="utf-8"); meta = dict(re.findall(r"^%([A-Z_]+):\s*(.*)$", md, flags=re.M))
    from k22_hwp_kpa import AUTHORS
    au = "\n".join(f"{k + 1}. {a['ko']} ({a['en']}) — {a['pos']}, {a['aff']} — {a['role']} — {a['email']}" for k, a in enumerate(AUTHORS))
    txt = (f"[국문 제목]\n{meta['TITLE_KO']}\n: {meta['SUBTITLE_KO']}\n\n[영문 제목]\n{meta['TITLE_EN']}\n: {meta['SUBTITLE_EN']}\n\n"
           f"[저자(투고 시스템 입력용, 심사용 원고에는 넣지 않음)]\n{au}\n\n[Abstract]\n{meta['ABSTRACT_EN']}\n\n"
           f"[국문 요약(투고 시스템에서 요구할 때)]\n{meta.get('ABSTRACT_KO', '')}\n\n[주제어]\n{meta['KEYWORDS_KO']}\n\n[Keywords]\n{meta['KEYWORDS_EN']}\n")
    (out / "04_투고시스템_입력내용.txt").write_text(txt, encoding="utf-8")
    for f in FIG.glob("Fv2_*"): shutil.copy2(f, out / "05_그림_원본" / f.name)
    for f in B.glob("*.*"): shutil.copy2(f, out / "06_표_원본" / f.name)
    for n in ("수치대조_기록_v2.json", "독립재계산_기록.json", "쪽수_기록.json"):
        if (MK / n).exists(): shutil.copy2(MK / n, out / "09_점검기록" / n)
    for n in ("외부검토_대응표_20260930.md", "구성변경_대조표_20260930.md"):
        if DOCS[n].exists(): shutil.copy2(DOCS[n], out / "09_점검기록" / n)
    shutil.copy2(C.TAB / "integrity" / "raw_integrity.json", out / "09_점검기록" / "원자료_무결성.json")
    for src in (C.TAB / "_repro_result_benchmark.json", C.PKG / "package_selfcheck.json"):
        if src.exists(): shutil.copy2(src, out / "09_점검기록" / src.name.lstrip("_"))
    shutil.copy2(DOCS["투고전_체크리스트_v2.md"], out / "07_저자확인항목.md")
    (out / "08_예상심사질문_답변.md").write_text(QNA, encoding="utf-8")
    import getpass, fitz
    from docx import Document
    names = [getpass.getuser(), "박종하", "엄선용", "daniel21c", "sunyongeom", "hanyang", "Hanyang", "Jongha", "Sunyong"]; found = []
    b = (out / "01_투고본_심사용_익명.hwp").read_bytes()
    for nm in names:
        for enc in ("utf-16le", "utf-8", "cp949"):
            if nm.encode(enc) in b: found.append(f"hwp:{nm}")
    pdf = fitz.open(str(out / "02_투고본_심사용_익명_확인용.pdf")); m = pdf.metadata; ptxt = "".join(pg.get_text() for pg in pdf)
    found += [f"pdf:{k}={m[k]}" for k in ("author", "creator", "producer") if m.get(k)] + [f"pdf본문:{nm}" for nm in names[1:] if nm in ptxt]
    cp = Document(str(out / "03_검토용_Word_익명.docx")).core_properties
    if cp.author or cp.last_modified_by: found.append("docx:author")
    (out / "09_점검기록" / "익명검사.json").write_text(json.dumps({"발견": found, "판정": "통과" if not found else "실패"}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "README.md").write_text(
        f"# 국토계획 제출본(확정본) — {stamp}\n\n**투고 시스템에 올릴 원고: 01(hwp, 학회 샘플 양식·익명)**. 02는 같은 원고의 확인용 PDF.\n\n"
        "03 검토용 Word · 04 투고 시스템 입력 내용(제목·저자·Abstract·국문 요약·주제어) · 05 그림 원본(220 dpi) · 06 표 원본 · 07 저자 확인 항목 · "
        "08 예상 심사 질문 · 09 점검 기록(원자료 무결성·수치 대조·독립 재계산·재현성·익명 검사) · 10 저자정보 포함본(심사 업로드 금지)\n\n"
        f"익명 검사: {'통과' if not found else found}\n", encoding="utf-8")
    return out, found


def selftest(pkg):
    R = {}
    rr = C.TAB / "_repro_result_benchmark.json"
    if rr.exists():
        d = json.loads(rr.read_text(encoding="utf-8")); R["재실행_재현성"] = "동일(csv 바이트·json 정규화)" if not d["달라진파일"] else f"달라짐: {d['달라진파일']}"
    else: R["재실행_재현성"] = "미실행"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    run = lambda cmd: subprocess.run([sys.executable] + cmd, cwd=pkg / "scripts", capture_output=True, text=True, encoding="utf-8", env=env)
    runs = []
    for cmd in (["tests/test_examples.py"], ["tests/test_benchmark.py"], ["k01_compute.py"]):
        p = run(cmd); runs.append({"cmd": cmd[0], "rc": p.returncode, "tail": (p.stdout + p.stderr).strip()[-200:]})
    # k25·원고 대조: 패키지의 결과 표(k13·k14)를 실행 위치로 옮겨 놓고 돌린다(원고는 config.MK가 패키지 모드에서 manuscript/를 가리킨다)
    ob = pkg / "output" / "tables" / "benchmark"; ob.mkdir(parents=True, exist_ok=True)
    for f in (pkg / "tables" / "benchmark").glob("*.*"):
        if not f.name.startswith("b9_"): shutil.copy2(f, ob / f.name)
    for cmd in (["k25_change_story.py"], ["tests/test_text_claims.py"]):
        p = run(cmd); runs.append({"cmd": cmd[0], "rc": p.returncode, "tail": (p.stdout + p.stderr).strip()[-200:]})
    R["실행"] = runs
    diffs = []
    for f in ("t02_gu_metrics_long.csv", "t03_gu_change.csv", "t04_decomposition.csv", "t05_null_summary.csv"):
        a = pd.read_csv(C.TAB / f, encoding="utf-8-sig"); b = pd.read_csv(pkg / "output" / "tables" / f, encoding="utf-8-sig")
        num = a.select_dtypes("number").columns
        diffs.append(float((a[num] - b[num]).abs().max().max()) if a.shape == b.shape else float("inf"))
    j0 = json.loads((B / "b9_change_story.json").read_text(encoding="utf-8")); j1 = json.loads((ob / "b9_change_story.json").read_text(encoding="utf-8"))
    def flat(d, p=""):
        out = {}
        for k, x in d.items():
            if isinstance(x, dict): out.update(flat(x, f"{p}{k}."))
            else: out[f"{p}{k}"] = x
        return out
    f0, f1 = flat(j0), flat(j1)
    dk = max((abs(f0[k] - f1[k]) for k in f0 if isinstance(f0[k], (int, float)) and not isinstance(f0[k], bool)), default=0.0)
    same_str = all(f0[k] == f1[k] for k in f0 if isinstance(f0[k], str))
    ok = all(r["rc"] == 0 for r in runs) and max(diffs) < 1e-9 and dk < 1e-9 and same_str
    R["패키지_자체재현"] = ("통과" if ok else "실패") + f" (k01 표 4종 최대차 {max(diffs):.1e}, k25 최대차 {dk:.1e}, 원고 수치 대조 {'통과' if runs[-1]['rc'] == 0 else '실패'})"
    shutil.rmtree(pkg / "output", ignore_errors=True)                     # 시험 산출물은 패키지에 남기지 않는다
    for pyc in pkg.rglob("__pycache__"): shutil.rmtree(pyc, ignore_errors=True)
    (C.PKG / "package_selfcheck.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
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
    zipdir(pkg, C.PKG / f"KPA_확정본_공동연구자패키지_{stamp}.zip")
    out, found = bundle(stamp, stem); zipdir(out, C.PKG / f"KPA_확정본_제출본_{stamp}.zip")
    shutil.rmtree(pkg, ignore_errors=True); shutil.rmtree(out, ignore_errors=True)   # zip과 같은 내용의 폴더는 남기지 않는다(중복 산출물 정리, 2026-09-30)
    print(json.dumps({"패키지": pkg.name, "파일": len(files), "자체시험": st, "제출본": out.name, "익명": found or "통과"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
