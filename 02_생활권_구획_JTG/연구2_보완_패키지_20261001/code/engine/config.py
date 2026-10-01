# -*- coding: utf-8 -*-
"""
config.py — 연구2 보완 패키지의 Louvain 실행용 설정 (공통 코어엔진 scripts/config.py 의 사본)
=====================================================
원본: 00_공통_코어엔진/scripts/config.py (사본은 config.py.orig, 해시는 audit/source_manifest.json).
원본과 다른 곳은 세 가지뿐이다.
  ① 경로: 입력은 이 패키지의 inputs/ (S0에서 해시를 확인한 사본), 출력은 output/louvain/.  원자료(RAW_*) 경로는 쓰지 않아 뺐다.
  ② SEED: 2025 Leiden 정본의 base 시드(1089930980)로 고정. Louvain은 2025년만 실행한다.
  ③ env_info 에 python-louvain(community) 버전을 기록한다.
알고리즘 상수(해상도 격자, 반복 수, τ, 자기 루프, 선정 규칙, 목표 개수)는 원본과 같다.
결정 근거는 00_공통_코어엔진/결정기록.md 를 본다.
"""
import sys
from pathlib import Path

# Windows 콘솔(cp949)에서 한글·기호 로그가 깨지지 않게
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 경로 ────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).resolve().parent            # .../연구2_보완_패키지_20261001/code/engine
PACKAGE_DIR   = SCRIPT_DIR.parent.parent                   # .../연구2_보완_패키지_20261001

DATA_DIR      = PACKAGE_DIR / "inputs"                     # S0 에서 해시를 확인한 입력 사본
OUTPUT_DIR    = PACKAGE_DIR / "output"                     # 실행 산출물
OD_DIR        = DATA_DIR                                   # OD 집계표 (inputs/ 에 평평하게 둔다)
LEIDEN_OUT    = OUTPUT_DIR / "louvain"                     # Louvain 실행 결과 (연도별 하위 폴더). 원본의 Leiden 출력 위치 대신

# ── 정본 파일명 ──────────────────────────────────────────────────────────────
N_DONG        = 424        # 개포3동(1123074) 복원 후 서울 행정동 수
N_LZ          = 116        # 공식 지역생활권 수

DONG_GPKG     = DATA_DIR / f"seoul_dong_{N_DONG}_dissolved.gpkg"          # layers: epsg5179, epsg4326
LZ_GPKG       = DATA_DIR / f"seoul_official_livingzone_{N_LZ}.gpkg"       # layers: epsg5179, epsg4326
DONG_LZ_MAP   = DATA_DIR / f"dong_to_official_livingzone_mapping_{N_DONG}.csv"
BOUNDARIES_ALL_GPKG = DATA_DIR / "seoul_boundaries_all.gpkg"               # official_livingzone_116, leiden_2020_116, leiden_2025_116
MANIFEST_JSON = DATA_DIR / "manifest.json"                                 # 정본 파일 SHA-256

def dong_leiden_map(year: str) -> Path:
    return DATA_DIR / f"dong_to_leiden_{year}_mapping_{N_DONG}.csv"

def od_full_path(year: str) -> Path:
    return OD_DIR / f"od_full_{year}01.parquet"          # (요일, 도착시간, 이동유형, dong_O, dong_D) 단위 집계

def od_daily_path(year: str) -> Path:
    return OD_DIR / f"od_daily_{year}01.parquet"         # 일상통행 필터 후 (dong_O, dong_D) 단위 집계

def od_summary_path(year: str) -> Path:
    return OD_DIR / f"od_summary_{year}01.json"

# ── 좌표계 ──────────────────────────────────────────────────────────────────
CRS_PROJECTED  = "EPSG:5179"    # 면적·교차 계산
CRS_GEOGRAPHIC = "EPSG:4326"

# ── 동 코드 처리 규칙 (s01) ──────────────────────────────────────────────────
# 통계청 ADM_CD(8자리) → 생활이동 행정동코드(7자리) 는 기본적으로 앞 7자리.
# 예외: 개포3동은 ADM_CD 11230511 이라 앞 7자리가 신사동(1123051)과 겹친다.
#       생활이동 코드표(2021-09-07)에서 같은 구역은 일원2동 1123074 → 2021년 개포3동으로 명칭 변경.
ADM_CD_TO_DONG_OVERRIDE = {
    "11230511": 1123074,   # 개포3동 (옛 일원2동)
}
# 앞 7자리가 같은 SHP 폴리곤 여러 개를 하나의 동으로 합치는 경우 (실제 분할동)
#   11170680 오류2동 + 11170680 항동   → 1117068 (생활이동 코드표: 오류2동)
#   11250520 상일1동 + 11250520 상일2동 → 1125052 (생활이동 코드표: 상일동)
# → 코드가 같으므로 dissolve 로 자연히 합쳐진다. 별도 규칙 불필요. 검증만 한다.

# ── 이동데이터 필터 (s02) — JTG 게재본·2025-10 실행과 동일 ──────────────────
FLOW_ARRIVAL_HOURS   = (9, 20)          # 도착시간 09~20 (09:00~20:59 도착)  → "09~21시"
FLOW_EXCLUDE_TYPES   = ("HW", "WH")     # 집↔직장 통근 제외 (그 외 유형은 모두 포함)
FLOW_MASKED_VALUE    = 0.0              # 이동인구(합) '*'(3명 미만 비공개) → 0
FLOW_SEOUL_PREFIX    = 11               # 출발·도착 모두 서울(코드 11xxxxx)
CSV_ENCODING         = "cp949"
CSV_CHUNK_ROWS       = 500_000

# ── Leiden 합의 구획 (s03) ──────────────────────────────────────────────────
YEARS                = ("2025",)   # 원본은 ("2020", "2025"). 연구2 Louvain 은 2025 만 (inputs/ 에 2020 OD 가 없다)
RES_MIN, RES_MAX, RES_STEP = 0.01, 2.50, 0.01   # 해상도 전수 스캔 (250단계)
N_ITER               = 3000        # 해상도마다 Leiden 반복 횟수 (co-association 누적)
TAU                  = 0.5         # co-association 임계값
SEED                 = 1089930980  # 2025 Leiden 정본의 base 시드와 같게 고정(원본은 None = 실행마다 무작위). Louvain 은 2025 만 실행한다.
                                   # 구 i 의 해상도 j, k번째 반복 시드 = base + i×10^7 + j×N_ITER + k  (원본과 같은 규칙)
INCLUDE_SELF_LOOPS   = True        # 동 내부 통행(자기 루프)을 그래프에 포함 (결정기록 §4)
SELECTION_PRIMARY    = "modularity"  # 목표 개수 일치 해상도 중 1차 기준 ('modularity' | 'ifr')
FINE_SCAN_STEPS      = 100         # 전수 스캔에서 목표 개수 미달 시 세밀 스캔 단계 수
STABILITY_TRIALS     = 10          # 확정 해상도에서 합의를 독립 반복하는 횟수 (ARI 산출)
STABILITY_ITER       = N_ITER      # 독립 반복 1회당 Leiden 반복 횟수
N_WORKERS            = 4           # 구 단위 병렬 프로세스 수

# 구별 목표 커뮤니티 수 = 공식 지역생활권의 구별 개수 (합계 116). s01 매핑으로 검증한다.
TARGET_COMMUNITIES = {
    11010: 4, 11020: 3, 11030: 4, 11040: 4, 11050: 4,
    11060: 4, 11070: 3, 11080: 5, 11090: 4, 11100: 5,
    11110: 7, 11120: 5, 11130: 4, 11140: 5, 11150: 5,
    11160: 6, 11170: 4, 11180: 3, 11190: 5, 11200: 5,
    11210: 5, 11220: 4, 11230: 6, 11240: 7, 11250: 5,
}
assert sum(TARGET_COMMUNITIES.values()) == N_LZ

KU_NAME = {
    11010: '종로구', 11020: '중구', 11030: '용산구', 11040: '성동구', 11050: '광진구',
    11060: '동대문구', 11070: '중랑구', 11080: '성북구', 11090: '강북구', 11100: '도봉구',
    11110: '노원구', 11120: '은평구', 11130: '서대문구', 11140: '마포구', 11150: '양천구',
    11160: '강서구', 11170: '구로구', 11180: '금천구', 11190: '영등포구', 11200: '동작구',
    11210: '관악구', 11220: '서초구', 11230: '강남구', 11240: '송파구', 11250: '강동구',
}
KU_NAME_EN = {
    11010: 'Jongno', 11020: 'Jung', 11030: 'Yongsan', 11040: 'Seongdong', 11050: 'Gwangjin',
    11060: 'Dongdaemun', 11070: 'Jungnang', 11080: 'Seongbuk', 11090: 'Gangbuk', 11100: 'Dobong',
    11110: 'Nowon', 11120: 'Eunpyeong', 11130: 'Seodaemun', 11140: 'Mapo', 11150: 'Yangcheon',
    11160: 'Gangseo', 11170: 'Guro', 11180: 'Geumcheon', 11190: 'Yeongdeungpo', 11200: 'Dongjak',
    11210: 'Gwanak', 11220: 'Seocho', 11230: 'Gangnam', 11240: 'Songpa', 11250: 'Gangdong',
}


def ensure_dirs():
    for p in (DATA_DIR, OUTPUT_DIR, OD_DIR, LEIDEN_OUT):
        p.mkdir(parents=True, exist_ok=True)


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def save_gpkg_layers(path: Path, layers: dict):
    """GeoPackage를 임시 폴더에 만든 뒤 옮긴다.
    (네트워크/마운트 드라이브에서 SQLite 직접 쓰기가 실패하는 경우가 있어 우회) layers = {layer_name: GeoDataFrame}"""
    import tempfile, shutil, os
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / path.name
        for name, gdf in layers.items():
            gdf.to_file(tmp, layer=name, driver="GPKG")
        shutil.copyfile(tmp, path)   # 기존 파일이 있으면 내용을 덮어쓴다 (삭제 권한 없이도 동작)


def env_info() -> dict:
    """실행 환경 기록용"""
    import platform, sys, datetime
    info = {"timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("pandas", "numpy", "geopandas", "igraph", "leidenalg", "networkx", "pyarrow", "shapely", "community"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "?")
        except Exception:
            info[mod] = None
    return info
