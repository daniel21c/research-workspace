# -*- coding: utf-8 -*-
"""
연구4 (불일치의 시간 변화 진단, KPA) — 경로·상수 설정

- 입력은 모두 `00_공통_코어엔진/data/`의 확정 배포본(데이터_배포목록.md의 boundary-v2-dong,
  od-daily-v1, boundary-v2-leiden)이다. 이 폴더는 그 파일을 읽기만 한다. 시설·접근성 자료는 쓰지 않는다(연구설계 §8).
- 출력은 이 폴더 안에만 쓴다: 결과 표 `results/`, 원고·그림 `manuscript/`, 패키지 `package/`.
  공동연구자 패키지(PKG_MODE)에서는 `output/tables`, `output/figures`, `manuscript/`를 쓴다.
- 지표 정의는 `연구설계.md` §3과 같다. 아래 상수를 바꾸면 연구설계.md와 원고의 해당 서술도 함께 고친다.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent            # .../04_불일치_시간변화_KPA/code (공동연구자 패키지에서는 scripts)
ROOT = HERE.parent                                # .../04_불일치_시간변화_KPA
REPO = ROOT.parent                                # .../00_박사논문_연구체계
CORE = REPO / "00_공통_코어엔진"
CORE_DATA = CORE / "data"

# 공동연구자 패키지 모드: 패키지 폴더(scripts/의 부모)에 data/core_config.py가 있으면 저장소 대신 패키지 안 자료를 쓴다.
PKG_MODE = (ROOT / "data" / "core_config.py").exists()
if PKG_MODE:
    CORE_DATA = ROOT / "data"

# 코어엔진 config의 구 이름·목표 개수를 그대로 쓴다(숫자를 두 곳에 적지 않기 위해).
# 파일 이름이 같아 import 로 부르면 자기 자신을 부르므로, 경로로 직접 읽는다.
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("core_config", (ROOT / "data" / "core_config.py") if PKG_MODE else (CORE / "scripts" / "config.py"))
_core = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_core)
KU_NAME, KU_NAME_EN, TARGET_COMMUNITIES = _core.KU_NAME, _core.KU_NAME_EN, _core.TARGET_COMMUNITIES

YEARS = ("2020", "2025")
Y0, Y1 = YEARS

# ---- 입력 (읽기 전용) ---------------------------------------------------------
MANIFEST = CORE_DATA / "manifest.json"
LZ_MAP = CORE_DATA / "dong_to_official_livingzone_mapping_424.csv"
DONG_GPKG = CORE_DATA / "seoul_dong_424_dissolved.gpkg"       # layer 'epsg5179' (통계청 2023-07-01 형상, 코드는 2021 코드표)


def od_daily(year: str) -> Path:
    return CORE_DATA / "od" / f"od_daily_{year}01.parquet"


def od_summary(year: str) -> Path:
    return CORE_DATA / "od" / f"od_summary_{year}01.json"


def ld_map(year: str) -> Path:
    return CORE_DATA / f"dong_to_leiden_{year}_mapping_424.csv"


# ---- 출력 ---------------------------------------------------------------------
# 산출물 위치(2026-09-30, AG 폴더와 같은 구성). 저장소: results/ 표, manuscript/ 원고·그림, package/ zip·자체 점검.
# 공동연구자 패키지(PKG_MODE)는 기존 배치(output/tables, output/figures, manuscript/)를 그대로 쓴다.
if PKG_MODE:
    OUT = ROOT / "output"; TAB = OUT / "tables"; FIG = OUT / "figures"; MK = ROOT / "manuscript"; PKG = OUT; WORK = OUT / "_hwp_work"; DOCX = MK
else:
    TAB = ROOT / "results"; FIG = ROOT / "manuscript" / "figures"; MK = ROOT / "manuscript"; PKG = ROOT / "package"; WORK = TAB / "_hwp_work"; OUT = PKG; DOCX = TAB / "_docx"   # 검토용 docx·1단/2단 pdf(중간 산출)
for _p in (TAB, FIG, MK, PKG, DOCX):
    _p.mkdir(parents=True, exist_ok=True)

# ---- 분석 상수 -------------------------------------------------------------------
# 무작위 경계 N0(k01: 같은 구·같은 권역 수·인접 제약의 무작위 분할)의 구별 표본 수와 시드. 원고 Ⅲ.1 2)에 적고 k24가 대조한다.
# 백분위용 무작위 경계 N0·N1·N2는 k13이 따로 뽑는다(시드 k13_benchmark.SEED = 20260927).
N_NULL = 1000
NULL_SEED = 20260924

FLOAT_TOL = 1e-6
