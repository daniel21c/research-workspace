# -*- coding: utf-8 -*-
"""
k07 — 국토계획(KPA) 투고용 공동연구자 공유 패키지

output/package_kpa_<날짜>/ 에 아래를 모으고 zip 으로 묶는다.
  README.md                      읽는 순서, 논문의 논리, 재현 순서, 표·그림 ↔ 파일 대응, 확인 요청, 해시
  manuscript/                    투고 초본(md·docx), 투고전_체크리스트.md, 학위논문 4.4 원고(참고)
  tables/ figures/               결과 전부
  scripts/                       코드 전부(config, kpa_metrics, k01~k07, tests)
  data/                          입력 배포본 사본(동→생활권·Leiden 매핑, od_daily 2020·2025, 동 경계 gpkg, 코어엔진 manifest)
  design/                        연구설계.md, 투고설계_국토계획_20260926.md (설계 근거)
  manifest.json                  모든 파일 SHA-256, 실행 환경, 입력 해시
실행: python k07_package_kpa.py   (k01~k06 을 먼저 실행해 둔다)
"""
from __future__ import annotations
import hashlib, json, platform, shutil, sys, time, zipfile
from pathlib import Path
import config as C

MK = C.OUT / "manuscript_kpa"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    stamp = time.strftime("%Y%m%d")
    pkg = C.OUT / f"package_kpa_{stamp}"
    for d in ("manuscript", "tables", "figures", "scripts", "data/od", "design"):
        (pkg / d).mkdir(parents=True, exist_ok=True)
    shutil.copytree(C.HERE, pkg / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    for src in (C.LZ_MAP, C.ld_map(C.Y0), C.ld_map(C.Y1), C.DONG_GPKG, C.MANIFEST):
        shutil.copy2(src, pkg / "data" / src.name)
    for y in C.YEARS:
        shutil.copy2(C.od_daily(y), pkg / "data" / "od" / C.od_daily(y).name)
        shutil.copy2(C.od_summary(y), pkg / "data" / "od" / C.od_summary(y).name)
    shutil.copy2(C.CORE / "scripts" / "config.py", pkg / "data" / "core_config.py")
    shutil.copytree(C.OUT / "tables", pkg / "tables", dirs_exist_ok=True)
    shutil.copytree(C.OUT / "figures", pkg / "figures", dirs_exist_ok=True)
    for f in MK.glob("*"):
        shutil.copy2(f, pkg / "manuscript" / f.name)
    for f in (C.OUT / "manuscript").glob("4-4절_*.md"):
        shutil.copy2(f, pkg / "manuscript" / ("참고_학위논문_" + f.name))
    for f in (C.HERE.parent / "연구설계.md", C.HERE.parent / "투고설계_국토계획_20260926.md"):
        if f.exists(): shutil.copy2(f, pkg / "design" / f.name)

    res = json.loads((C.TAB / "results.json").read_text(encoding="utf-8"))
    tst = json.loads((C.TAB / "t06_tests.json").read_text(encoding="utf-8"))
    core = json.loads(C.MANIFEST.read_text(encoding="utf-8"))
    md = sorted(MK.glob("국토계획_투고초본_v*.md"))[-1].name
    readme = f"""# 국토계획(KPA) 투고 패키지 — {stamp}

공식 생활권(LZ)과 이동 기반 경계(LD)의 판정 불일치를 2020-01·2025-01 두 시점에서 비교하고 재정비 검토 대상을 선별한 논문의
**투고 초본·코드·입력·결과**다. 공동연구자는 이 폴더만으로 모든 표·그림을 다시 만들 수 있다.

## 0. 이 논문이 하려는 말 (한 문단)
공식 생활권은 한 번 그어 두면 이동과 어긋나기 시작한다. 그 어긋남은 내부통행비율(IFR) 하나로는 보이지 않으므로(무작위 경계에서도 같은 크기로 오름),
같은 해의 이동 기반 경계를 기준점으로 삼아 불일치의 **방향 G**와 **크기 D**를 두 시점에서 재고, 사전에 정한 규칙으로 재정비 검토 구를 선별한다.
접근성은 이 논문에 넣지 않는다(설계 근거: design/투고설계_국토계획_20260926.md 7절 이후, 07_시계열_종합탐색 보고서).

## 1. 읽는 순서
1. `manuscript/{md}` — 투고 초본(본문). 같은 이름의 `.docx`가 국토계획 서식판(1단), `_2단.docx`·`.hwp`는 학회 2단 편집 확인용.
2. `manuscript/투고전_체크리스트.md` — 저자가 채울 것·확인할 것.
3. `tables/results.json`, `t06_tests.json` — 핵심 수치와 검정.
4. `design/연구설계.md` — 가설·지표·검증 계획·예상 반론(8절). `design/투고설계_…md` — 접근성 축을 뺀 이유.
5. `scripts/` — 아래 재현 순서.

## 2. 재현 순서
```
pip install -r scripts/requirements.txt
cd scripts
python tests/test_examples.py     # 손계산 예제 A~D
python k01_compute.py             # 지표·분해·귀무 분할 (tables/)
python k02_select.py              # 판정·선별·강건성
python k03_figures.py             # 그림 (figures/)
python k04_manuscript.py          # 학위논문 4.4 원고(참고)
python k06_kpa_submission.py      # 투고 초본 docx (manuscript_kpa/)
python k08_hwp_pages.py           # Word PDF·쪽수 (Windows)
python k09_hwp_build.py           # 한글 자동화로 .hwp 생성 (Windows + 한글 2022 + pyhwpx)
```
`scripts/config.py`의 `CORE_DATA`를 이 패키지의 `data/`로 바꾸면 코어엔진 없이 실행된다(k02의 대안 구획 읽기는 건너뛰며 `t07_robustness.csv`가 이미 있음).

## 3. 입력 (data/)
| 파일 | 내용 | 출처 |
|---|---|---|
| dong_to_official_livingzone_mapping_424.csv | 행정동 424 → 공식 지역생활권 116 | boundary-v2-dong |
| dong_to_leiden_{{2020,2025}}_mapping_424.csv | 행정동 424 → LD 116, 연도별 | boundary-v2-leiden (3,000회 합의, τ=0.5, base seed 2020={core['years']['2020']['run_info']['base_seed']}, 2025={core['years']['2025']['run_info']['base_seed']}) |
| od/od_daily_{{2020,2025}}01.parquet | 동×동 통행량(도착 09~20시, HW/WH 제외, 서울 내부, `*`→0) | od-daily-v1. 개인 단위 원자료 미포함 |
| seoul_dong_424_dissolved.gpkg | 행정동 경계(EPSG:5179) | boundary-v2-dong |

## 4. 지표 (scripts/kpa_metrics.py, 초본 표 2)
T = 구 출발 서울 내 전체 통행(두 경계 공통 분모). a = LD만 내부, b = LZ만 내부. **G = (a−b)/T**, **D = (a+b)/T**, 0 ≤ |G| ≤ D. 서울 전체는 분자합/분모합.
분해: ΔD = 통행 변화 효과 + 경계 재도출 효과(두 순서 평균). 귀무: 구별 무작위 인접 분할 {C.N_NULL}개(시드 {C.NULL_SEED}).

## 5. 핵심 결과
- 서울 IFR: LZ {res['seoul']['2020']['IFR_lz']:.1%}→{res['seoul']['2025']['IFR_lz']:.1%}, LD {res['seoul']['2020']['IFR_ld']:.1%}→{res['seoul']['2025']['IFR_ld']:.1%}. LZ 상승은 {res['null']['lz_within_null90_n']}/25 구에서 귀무 구간 안.
- G: {res['seoul']['2020']['G']*100:+.2f}%p → {res['seoul']['2025']['G']*100:+.2f}%p (커진 구 {tst['H3_sign_test_excl_ties']['up']}, 작아진 구 {tst['H3_sign_test_excl_ties']['down']}, p = {tst['H3_sign_test_excl_ties']['p_greater']:.3f}).
- D: {res['seoul']['2020']['D']:.2%} → {res['seoul']['2025']['D']:.2%} (커진 구 {tst['H2_sign_test_excl_ties']['up']}, 줄어든 구 {tst['H2_sign_test_excl_ties']['down']}, 변화 없음 {tst['H2_sign_test_excl_ties']['tie']}). 분해: 통행 {res['decomposition_seoul']['D']['flow_effect_mean']*100:+.2f}%p, 경계 재도출 {res['decomposition_seoul']['D']['boundary_effect_mean']*100:+.2f}%p.
- 선별 {tst['selected_n']}개 구: {', '.join(d['ku_name']+'('+d['type']+')' for d in tst['selected'])}. ΔD>1%p: {', '.join(tst['selected_minband1.0'])}.

## 6. 초본 표·그림 ↔ 파일
| 초본 | 파일 |
|---|---|
| 표 1 자료 | tables/t01_data_summary.csv |
| 표 3 구별 IFR·G·D | tables/t02_gu_metrics_long.csv, results.json |
| 표 4 변화·분해 | tables/t03_gu_change.csv, t04_decomposition.csv |
| 표 5 선별·강건성 | tables/t06_selection.csv, t04b_fixed_ld2020_on_2025.csv, t09_ari_ld20_ld25.csv, t07_robustness.csv |
| 표 A1 귀무 | tables/t05_null_summary.csv (원자료 t05_null_partitions.csv) |
| 그림 1 분석 틀 | figures/F_kpa_framework.png (k06 생성) |
| 그림 2~6, A1 | figures/F4-4-1, F4-4-3, F4-4-4, F4-4-5, F4-4-7, F4-4-6 |
| 본문의 생활권 단위 ΔD | tables/t08b_lz116_change.csv |

## 7. 공동연구자에게 확인을 부탁하는 것
1. a·b·T를 다른 도구(DuckDB SQL 또는 스프레드시트, 동 수가 적은 금천구 1개)로 독립 재계산해 표 3과 대조.
2. 초본 Ⅳ장 문장의 수치가 표 3~5·A1과 같은지 대조(문장은 k04 생성 원고에서 옮김).
3. 선별 규칙(Ⅲ.5)과 대응 유형 구분이 사전 규칙으로 읽히는지, 최소 폭 병기가 사후 선택으로 보이지 않는지.
4. 인용문헌 서지(특히 Halás 2024, INSEE 2022, OMB 2021)의 원문 대조.

## 8. 점검한 것
손계산 예제 4개 테스트 통과. 항등식 N_LD − N_LZ = a − b, |G| ≤ D, 생활권 합산 = 구 = 서울, 분해 두 순서의 합 = ΔX. 코어엔진 s05 독립 검증과 구별 IFR 일치(최대 오차 5e-7).
Git에는 데이터가 없다. 이 패키지의 `manifest.json`이 모든 파일의 SHA-256이다.

문의: 박종하 (daniel21c@hanyang.ac.kr)
"""
    (pkg / "README.md").write_text(readme, encoding="utf-8")
    files = {str(p.relative_to(pkg)).replace("\\", "/"): {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(pkg.rglob("*")) if p.is_file()}
    try:
        import pandas, numpy, scipy, geopandas, matplotlib, docx
        env = {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pandas.__version__, "numpy": numpy.__version__,
               "scipy": scipy.__version__, "geopandas": geopandas.__version__, "matplotlib": matplotlib.__version__}
    except Exception as e:
        env = {"error": str(e)}
    manifest = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "env": env, "core_engine_inputs": core["files"],
                "leiden_runs": {y: core["years"][y]["run_info"] for y in C.YEARS}, "files": files}
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    zpath = C.OUT / f"KPA_submission_package_{stamp}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pkg.rglob("*")):
            if p.is_file(): z.write(p, p.relative_to(pkg.parent))
    print("패키지:", pkg, "\nzip:", zpath, f"({zpath.stat().st_size/1e6:.1f} MB)", f"파일 {len(files)}개")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
