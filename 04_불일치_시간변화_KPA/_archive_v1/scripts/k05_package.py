# -*- coding: utf-8 -*-
"""
k05 — 공동연구자 공유 패키지 만들기 (KPA 투고 전)

output/package_<날짜>/ 에 아래를 모아 zip 으로 묶는다.
  README.md          무엇을 어떻게 계산했는지, 재현 순서, 지표 정의, 파일 목록과 해시
  scripts/           이 폴더의 코드 전부 (config, kpa_metrics, k01~k05, tests)
  data/              입력 배포본 사본: 동→공식 생활권 매핑, 동→Leiden 매핑 2020/2025, od_daily 2020/2025(동×동 집계),
                     동 경계 gpkg. 원자료(개인 단위 생활이동 CSV)는 포함하지 않는다.
  tables/ figures/ manuscript/   결과 전부
  manifest.json      모든 파일의 SHA-256, 실행 환경, 입력 해시(코어엔진 manifest 와 대조 가능)
실행: python k05_package.py   (k01~k04 를 먼저 실행해 둔다)
"""
from __future__ import annotations
import hashlib, json, platform, shutil, subprocess, sys, time, zipfile
from pathlib import Path
import config as C

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    stamp = time.strftime("%Y%m%d")
    pkg = C.OUT / f"package_{stamp}"
    # 같은 날 다시 만들면 덮어쓴다(삭제하지 않음). 이전 날짜 패키지는 그대로 둔다.
    (pkg / "data" / "od").mkdir(parents=True, exist_ok=True)
    # 코드
    shutil.copytree(C.HERE, pkg / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    # 입력 배포본
    for src in (C.LZ_MAP, C.ld_map(C.Y0), C.ld_map(C.Y1), C.DONG_GPKG, C.MANIFEST):
        shutil.copy2(src, pkg / "data" / src.name)
    for y in C.YEARS:
        shutil.copy2(C.od_daily(y), pkg / "data" / "od" / C.od_daily(y).name)
        shutil.copy2(C.od_summary(y), pkg / "data" / "od" / C.od_summary(y).name)
    # 코어엔진 config 도 함께 (구 이름·목표 개수 상수)
    shutil.copy2(C.CORE / "scripts" / "config.py", pkg / "data" / "core_config.py")
    # 결과
    for d in ("tables", "figures", "manuscript"):
        shutil.copytree(C.OUT / d, pkg / d, dirs_exist_ok=True)
    # manifest
    files = {str(p.relative_to(pkg)).replace("\\", "/"): {"sha256": sha(p), "bytes": p.stat().st_size}
             for p in sorted(pkg.rglob("*")) if p.is_file()}
    try:
        import pandas, numpy, scipy, geopandas, matplotlib
        env = {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pandas.__version__,
               "numpy": numpy.__version__, "scipy": scipy.__version__, "geopandas": geopandas.__version__,
               "matplotlib": matplotlib.__version__}
    except Exception as e:  # pragma: no cover
        env = {"error": str(e)}
    core = json.loads(C.MANIFEST.read_text(encoding="utf-8"))
    manifest = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "env": env,
                "core_engine_inputs": core["files"], "leiden_runs": {y: core["years"][y]["run_info"] for y in C.YEARS},
                "files": files}
    (pkg / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # README
    res = json.loads((C.TAB / "results.json").read_text(encoding="utf-8"))
    tst = json.loads((C.TAB / "t06_tests.json").read_text(encoding="utf-8"))
    readme = f"""# 연구4 (KPA) 분석 패키지 — {stamp}

공식 생활권(LZ)과 이동 기반 경계(LD)의 내부통행 판정 불일치를 2020-01·2025-01 두 시점에서 비교한 분석의 코드·입력·결과다.
학위논문 4.4절과 국토계획(KPA) 투고본의 모든 수치는 이 패키지의 `scripts/`로 `data/`에서 다시 계산할 수 있다.

## 1. 재현 순서
```
pip install -r scripts/requirements.txt
cd scripts
python tests/test_examples.py     # 손계산 예제 A~D (연구설계 7.1)
python k01_compute.py             # 지표 (tables/)
python k02_select.py              # 판정·선별·강건성
python k03_figures.py             # 그림 (figures/)
python k04_manuscript.py          # 원고 초안 (manuscript/)
```
`scripts/config.py`의 `CORE_DATA`가 코어엔진 폴더를 가리킨다. 이 패키지만 받은 경우 `CORE_DATA = Path(__file__).resolve().parents[1] / "data"`,
`CORE_OUT`은 없으므로 k02의 안정성·대안 구획 읽기는 건너뛴다(결과 표 `t06_consensus_stability.csv`, `t07_robustness.csv`가 이미 들어 있다).

## 2. 입력 (data/)
| 파일 | 내용 | 출처 |
|---|---|---|
| dong_to_official_livingzone_mapping_424.csv | 행정동 424 → 공식 지역생활권 116 | 코어엔진 s01 (배포 ID boundary-v2-dong) |
| dong_to_leiden_{{2020,2025}}_mapping_424.csv | 행정동 424 → 이동 기반 경계 116, 연도별 | 코어엔진 s03 (boundary-v2-leiden). Leiden 3,000회 × 해상도, co-association τ=0.5, 자기 루프 포함, 구별 개수=공식 생활권 수, Q 최대 선정. base seed 2020={core['years']['2020']['run_info']['base_seed']}, 2025={core['years']['2025']['run_info']['base_seed']} |
| od/od_daily_{{2020,2025}}01.parquet | 동×동 통행량 (도착 09~20시, HW/WH 제외, 요일 전체, 서울 내부, `*`→0) | 코어엔진 s02 (od-daily-v1). 개인 단위 원자료는 포함하지 않음 |
| seoul_dong_424_dissolved.gpkg | 행정동 경계 (EPSG:5179) | 코어엔진 s01 |
| manifest.json | 코어엔진 배포본 해시·실행 정보 | |

## 3. 지표 정의 (scripts/kpa_metrics.py)
구 K, 연도 t. T = 출발이 K인 서울 내 모든 통행량(두 경계 공통 분모).
- IFR^B = N^B / T (B ∈ {{LZ, LD}}; N^B = 출발·도착이 같은 권역인 통행량)
- a = LD에서만 내부인 통행량, b = LZ에서만 내부인 통행량
- **G = IFR^LD − IFR^LZ = (a − b)/T** : 격차의 방향
- **D = (a + b)/T** : 격차의 크기(상쇄 전 총 판정차), 0 ≤ |G| ≤ D
- 상위 단위(서울)는 분자합/분모합. ΔX = X_2025 − X_2020.
- 분해: X(LD_s, OD_u) 네 조합으로 ΔX = 통행 변화 효과 + 경계 재도출 효과(두 순서 평균).
- 귀무 분할: 구별 같은 개수의 무작위 인접 분할 {C.N_NULL}개(시드 {C.NULL_SEED}), 두 해 통행에 같이 적용.
- IoU: 동 기준 1:1 최대교집합 배정(연구2 정의). D의 외부 검증용.

## 4. 핵심 결과 (tables/results.json, t06_tests.json)
- 서울 IFR: LZ {res['seoul']['2020']['IFR_lz']:.1%}→{res['seoul']['2025']['IFR_lz']:.1%}, LD {res['seoul']['2020']['IFR_ld']:.1%}→{res['seoul']['2025']['IFR_ld']:.1%}. LZ의 상승은 25개 구 중 {res['null']['lz_within_null90_n']}개 구에서 귀무 분할 5~95% 안 → 경계와 무관.
- G(서울): {res['seoul']['2020']['G']*100:+.2f}%p → {res['seoul']['2025']['G']*100:+.2f}%p. G 커진 구 {tst['H3_sign_test_excl_ties']['up']} / 작아진 구 {tst['H3_sign_test_excl_ties']['down']}.
- D(서울): {res['seoul']['2020']['D']:.2%} → {res['seoul']['2025']['D']:.2%}. D 커진 구 {tst['H2_sign_test_excl_ties']['up']} / 줄어든 구 {tst['H2_sign_test_excl_ties']['down']} / 변화 없음 {tst['H2_sign_test_excl_ties']['tie']}.
- IoU↔D ρ = {tst['iou_corr']['IoU_vs_D_2025']['spearman']:+.2f}(2025), IoU↔G ρ = {tst['iou_corr']['IoU_vs_G_2025']['spearman']:+.2f}.
- 선별({tst['selection_rule']}): {tst['selected_n']}개 구 — {', '.join(d['ku_name']+'('+d['type']+')' for d in tst['selected'])}. ΔD>1%p: {', '.join(tst['selected_minband1.0'])}.

## 5. 표·그림 대응
| 파일 | 원고 |
|---|---|
| tables/t02_gu_metrics_*.csv, t03_gu_change.csv | 표 4.4-1, 4.4-2 |
| tables/t04_decomposition.csv, t04b_fixed_ld2020_on_2025.csv | 표 4.4-4 |
| tables/t05_null_summary.csv (t05_null_partitions.csv 원자료) | 표 4.4-3, 그림 4.4-6 |
| tables/t06_selection.csv, t06_tests.json, t07_robustness.csv | 표 4.4-5 |
| tables/t09_ari_ld20_ld25.csv | 그림 4.4-5 |
| tables/t10_iou_vs_gap.csv | 그림 4.4-7 |
| tables/t08b_lz116_change.csv | 부록 4.4-D (본문 미사용) |
| manuscript/기준원고_대조표.csv | 부록 4.4-B |

## 6. 점검한 것
- 손계산 예제 4개 테스트 통과. 항등식 N_LD − N_LZ = a − b, |G| ≤ D, 구 합산 = 생활권 합산 = 서울, 분해 두 순서의 합 = ΔX 를 실행마다 확인.
- 코어엔진 s05 독립 검증(IFR·Q 재계산 최대 오차 5e-7)과 구별 IFR 일치.
- 확인이 더 필요한 것: a·b·T를 다른 도구(DuckDB SQL 또는 다른 사람)로 독립 재계산.

문의: 박종하 (daniel21c@hanyang.ac.kr)
"""
    (pkg / "README.md").write_text(readme, encoding="utf-8")
    zpath = C.OUT / f"KPA_package_{stamp}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(pkg.parent))
    print("패키지:", pkg, "\nzip:", zpath, f"({zpath.stat().st_size/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
