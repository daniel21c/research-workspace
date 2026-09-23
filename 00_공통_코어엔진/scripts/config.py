"""
config.py — 박사논문 연구 전체 경로 중앙 관리
============================================================
모든 스크립트에서 이 파일만 import 하면 경로 문제 없음.

사용법:
    from config import RAW_DIR, COMMON_DATA_DIR, PRE_PKL_DIR
"""

from pathlib import Path

# ============================================================
# 최상위 경로
# ============================================================
RESEARCH_ROOT = Path(r"D:\Research")

# ============================================================
# 로우 데이터 (절대 수정 금지 — 읽기 전용)
# ============================================================
RAW_DIR = RESEARCH_ROOT / "0_RAW"

# SKT 이동 빅데이터 원천 폴더 (연도별 하위 폴더 있음)
RAW_FLOW_DIR = RAW_DIR / "이동데이터"

# 행정경계 원천 GIS 파일
RAW_GIS_DIR  = RAW_DIR / "GIS"

# ============================================================
# 전처리 캐시 (PKL) — 빠른 로드용, 재생성 가능
# ============================================================
PRE_PKL_DIR = RESEARCH_ROOT / "1_OUTPUT" / "0_preprocessed_data"

# ============================================================
# 박사논문 연구체계 루트
# ============================================================
THESIS_ROOT = RESEARCH_ROOT / "00_박사논문_연구체계"

# ── 00 공통 코어엔진
COMMON_DIR       = THESIS_ROOT / "00_공통_코어엔진"
COMMON_DATA_DIR  = COMMON_DIR  / "data"
COMMON_SCRIPT_DIR= COMMON_DIR  / "scripts"

# 정본 공간 데이터 경로 (직접 참조용 단축키)
DONG_423_GPKG          = COMMON_DATA_DIR / "seoul_dong_423_dissolved.gpkg"
LZ_116_GPKG            = COMMON_DATA_DIR / "seoul_official_livingzone_116.gpkg"
BOUNDARIES_ALL_GPKG    = COMMON_DATA_DIR / "seoul_boundaries_all.gpkg"
DONG_LZ_MAPPING        = COMMON_DATA_DIR / "dong_to_official_livingzone_mapping_423.csv"
DONG_LEIDEN_2020_MAPPING = COMMON_DATA_DIR / "dong_to_leiden_2020_mapping_423.csv"
DONG_LEIDEN_2025_MAPPING = COMMON_DATA_DIR / "dong_to_leiden_2025_mapping_423.csv"

# ── 01 생활권 필요성 실증
PAPER_01_DIR  = THESIS_ROOT / "01_생활권_필요성_실증"
PAPER_01_OUT  = PAPER_01_DIR / "output"

# ── 02 JTG 커뮤니티 구획 (게재 논문 검증)
PAPER_02_DIR  = THESIS_ROOT / "02_JTG_커뮤니티구획"
PAPER_02_OUT  = PAPER_02_DIR / "output"

# ── 03 AG 서비스 접근성 연계
PAPER_03_DIR  = THESIS_ROOT / "03_AG_서비스접근성연계"
PAPER_03_OUT  = PAPER_03_DIR / "output"

# ── 04 KPA 시계열 불일치 진단
PAPER_04_DIR  = THESIS_ROOT / "04_KPA_시계열_불일치진단"
PAPER_04_OUT  = PAPER_04_DIR / "output"

# ── 05 통합 패키지
PAPER_05_DIR  = THESIS_ROOT / "05_통합_박사학위논문_패키지"

# ============================================================
# 이동 데이터 필터 기본값 (common_flow_loader.py 와 동기화)
# ============================================================
FLOW_HOUR_START = 9   # 09시 이상
FLOW_HOUR_END   = 21  # 21시 미만
FLOW_PURPOSE_EXCLUDE = ["통근"]  # 제외 목적 코드

# ============================================================
# 좌표계
# ============================================================
CRS_PROJECTED = "EPSG:5179"   # TM중부원점 (면적 계산용)
CRS_GEOGRAPHIC = "EPSG:4326"  # WGS84 (범용)


# ── 간단한 경로 존재 확인 (import 시 자동 실행)
def _check_critical_paths():
    critical = [RAW_DIR, COMMON_DATA_DIR, DONG_423_GPKG, LZ_116_GPKG]
    missing  = [str(p) for p in critical if not p.exists()]
    if missing:
        import warnings
        warnings.warn(
            f"[config.py] 아래 경로가 존재하지 않습니다:\n" +
            "\n".join(f"  - {m}" for m in missing),
            stacklevel=2
        )


_check_critical_paths()
