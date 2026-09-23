"""Read-only input locations and explicit scenario assumptions."""
from pathlib import Path
ROOT = Path(r"D:\Research")
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FACILITIES = ROOT / "00_공통_데이터/facility_clean_2020_2025"
RAW_FACILITIES = ROOT / "999_논문/living_zone_integrated_thesis_project_20260730/facility_panel_8types_2020_2026/raw"
CORE = ROOT / "00_박사논문_연구체계/00_공통_코어엔진/data"
GRID_DIR = ROOT / "1_OUTPUT/community_detection/OD 데이터(승훈이데이터)/종하_row_data/3. row_data"
ORIGINS = GRID_DIR / "서울_인구격자_생활권_매칭결과_4326.gpkg"
GRID = GRID_DIR / "서울_격자_250_5179_clean.gpkg"
OFFICIAL = ROOT / "0_RAW/UPIS_SHP_ZON100/seoul_living_zone.shp"
GU = ROOT / "0_RAW/seoul_gu.shp"
PBF = ROOT / "2_symposium/project/data/data_seoul/osrm/south-korea-latest.osm.pbf"
YEARS = (2020, 2025)
CATEGORIES = ("RETAIL_DAILY", "CLINIC_PRIMARY", "SCHOOL_BASIC", "LIBRARY_PUBLIC")
METRIC_CRS = 5179
SPEED_KMH = 4.0
THRESHOLDS_MIN = (10, 15)
SNAP_CAPS_M = (100.0, 200.0)
PRIMARY_SNAP_CAP_M = 100.0
# Seoul plus a substantial buffer; routes may cross city / zone borders.
NETWORK_BBOX = (126.65, 37.30, 127.35, 37.85)
MAX_RUNTIME_SECONDS = 3600
# Independent read-only HTTPS verification performed by the coordinating agent.
# This certifies today's official payload match, not historical content accuracy.
RETAIL_SOURCE_VERIFICATION = {
    'year_label': 2020,
    'verification_date': '2026-09-23',
    'url': 'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003547804&fileDetailSn=1',
    'method': 'Coordinator HTTP GET, in-memory streaming SHA256; no raw-file write',
    'http_status': 200,
    'content_type': 'application/octet-stream',
    'content_disposition_filename': '소상공인시장진흥공단_상가(상권)정보_20191231.zip',
    'bytes': 293466529,
    'magic_hex': '504b',
    'sha256': '3aaac1b08fd21eaf42fbdfd3e78163c9b82fb026f351a19db06c43a2fb42d21f',
    'current_official_payload_match': True,
    'historical_vintage_certified': False,
}
RETAIL_SOURCE_VERIFICATIONS = [RETAIL_SOURCE_VERIFICATION, {
    'year_label': 2025,
    'verification_date': '2026-09-23',
    'url': 'https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003676580&fileDetailSn=1',
    'method': 'Coordinator HTTP GET, in-memory streaming SHA256; no raw-file write',
    'http_status': 200,
    'content_type': 'application/octet-stream',
    'content_disposition_filename': '소상공인시장진흥공단_상가(상권)정보_20241231.zip',
    'bytes': 331029189,
    'sha256': '143be21bf7aee3958b6c4e6c4ed3fc6b0f8ac8380a6d47d0bfcfd4745763bf1a',
    'current_official_payload_match': True,
    'historical_vintage_certified': False,
}]
