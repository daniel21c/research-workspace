# -*- coding: utf-8 -*-
"""
연구4 (불일치의 시간 변화 진단, KPA) — 경로·상수 설정

- 입력은 모두 `00_공통_코어엔진/data/`의 확정 배포본(데이터_배포목록.md의 boundary-v2-dong,
  od-daily-v1, boundary-v2-leiden)이다. 이 폴더는 그 파일을 읽기만 한다.
- 출력은 이 폴더(`04_불일치_시간변화_KPA/output/`)에만 쓴다.
- 지표 정의는 `연구설계.md` 5절과 같다. 이 파일의 상수를 바꾸면 연구설계.md 9절도 함께 고친다.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent            # .../04_불일치_시간변화_KPA/scripts
ROOT = HERE.parent                                # .../04_불일치_시간변화_KPA
REPO = ROOT.parent                                # .../00_박사논문_연구체계
CORE = REPO / "00_공통_코어엔진"
CORE_DATA = CORE / "data"
CORE_OUT = CORE / "output"
# 접근성 엔진 결과·입력(원인 탐색 k15~k17에서만 읽음)
ACC_DATA = REPO / "06_접근성분석" / "접근성분석_패키지" / "데이터"

# 공동연구자 패키지 모드: 패키지 폴더(scripts/의 부모)에 data/core_config.py가 있으면 저장소 대신 패키지 안 자료를 쓴다.
PKG_MODE = (ROOT / "data" / "core_config.py").exists()
if PKG_MODE:
    CORE_DATA = ROOT / "data"
    CORE_OUT = ROOT / "data" / "_core_output_absent"      # 대안 구획(τ 0.4/0.6)은 패키지에 없음 → k02가 건너뜀(결과 표는 포함)
    ACC_DATA = ROOT / "data" / "access"

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
DONG_GPKG = CORE_DATA / "seoul_dong_424_dissolved.gpkg"       # layer 'epsg5179'
ALL_GPKG = CORE_DATA / "seoul_boundaries_all.gpkg"


def od_daily(year: str) -> Path:
    return CORE_DATA / "od" / f"od_daily_{year}01.parquet"


def od_summary(year: str) -> Path:
    return CORE_DATA / "od" / f"od_summary_{year}01.json"


def ld_map(year: str) -> Path:
    return CORE_DATA / f"dong_to_leiden_{year}_mapping_424.csv"


def stability_dir(year: str) -> Path:
    return CORE_OUT / "leiden" / year / "stability"


# 방법 민감도용 대안 구획(코어엔진 s06이 만든 것). 없으면 건너뛴다.
ALT_RUNS = {
    "tau0.4": lambda y: CORE_OUT / "leiden" / f"{y}_tau0.4" / "metrics" / f"leiden_mapping_{y}.csv",
    "tau0.6": lambda y: CORE_OUT / "leiden" / f"{y}_tau0.6" / "metrics" / f"leiden_mapping_{y}.csv",
    "ifr_primary": lambda y: CORE_OUT / "leiden" / f"{y}_ifr" / "metrics" / f"leiden_mapping_{y}.csv",
}

# ---- 출력 ---------------------------------------------------------------------
OUT = ROOT / "output"
TAB = OUT / "tables"
FIG = OUT / "figures"
MAN = OUT / "manuscript"
# 원고(md·docx·hwp·점검 기록) 폴더: 저장소는 output/manuscript_kpa, 공동연구자 패키지는 manuscript/ (k19·k22·k08·k11·시험이 모두 이 값을 쓴다)
MK = ROOT / "manuscript" if PKG_MODE else OUT / "manuscript_kpa"
for _p in (OUT, TAB, FIG, MAN, MK):
    _p.mkdir(parents=True, exist_ok=True)

# ---- 분석 상수 (연구설계 9절 권장안) -------------------------------------------
# D3-B: ΔD > 합의 변동 폭 이고 D_2025 >= 서울 전체 D_2025
SELECTION_RULE = "D3-B"
# 부호검정 유의수준 (H2, 한쪽 검정)
ALPHA = 0.05
# H4 귀무 분할: 같은 구·같은 개수·인접 제약의 무작위 분할 수와 시드
N_NULL = 1000
NULL_SEED = 20260924
# 합의 변동 폭이 0(모든 독립 반복 ARI=1)일 때 "변화 없음"으로 볼 최소 폭(%p). 0이면 부호만 본다.
MIN_BAND_PP = 0.0

FLOAT_TOL = 1e-6
