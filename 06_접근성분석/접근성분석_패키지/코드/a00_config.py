# -*- coding: utf-8 -*-
"""06_접근성분석 공통 설정. 경로·상수는 여기서만 정의한다. 정의 근거: 문서/지표정의_확정.md"""
from pathlib import Path
import os

HERE = Path(__file__).resolve().parent          # 06_접근성분석/접근성분석_패키지/코드
ROOT = HERE.parent                                # 06_접근성분석/접근성분석_패키지
BASE = ROOT.parent.parent                         # 00_박사논문_연구체계
# 모든 경로는 00_박사논문_연구체계(BASE) 안의 상대경로다(2026-09-26, 공동연구자 공유용 자기완결 구성).
CORE   = BASE / '00_공통_코어엔진'
# 2026-09-25: 시설데이터는 패키지 하나로 정리됨 → 시설데이터 구축/시설데이터_패키지/ (데이터·문서·구축코드·SGIS)
FACPKG = BASE / '시설데이터 구축' / '시설데이터_패키지'
FACDIR = FACPKG / '구축코드'
SGIS   = FACPKG / 'SGIS_인구경계_2019_2024'
# API 키(지오코딩 재호출 때만 필요, 공유본에 없음): 환경변수 FACILITY_API_ENV 또는 00_박사논문_연구체계/_secrets/facility_api.env
SECRETS = Path(os.environ.get('FACILITY_API_ENV', BASE / '_secrets' / 'facility_api.env'))

# 2026-09-25: 06 폴더를 패키지 하나로 정리 — 문서/(정의·구축기록), 코드/, 데이터/입력/(격자·시설·경계·보행망·소요시간표), 데이터/결과/
DATA = ROOT / '데이터' / '입력'; OUT = ROOT / '데이터' / '결과'; REC = ROOT / '문서'
# 250m 국가격자 기하(기하·gid만 사용; 원 출처는 김승훈 외 AG 자료의 서울 250m 격자, 2026-09-26 패키지 안으로 복사)
GRID250_SRC = DATA / 'grid' / 'source' / '서울_격자_250_5179_clean.gpkg'
MANIFEST = ROOT / '데이터' / 'manifest_sha256.csv'
for p in [DATA/'grid', DATA/'facility', DATA/'boundary', DATA/'network', DATA/'ttm', OUT, REC]:
    p.mkdir(parents=True, exist_ok=True)

# 입력 파일
FACILITY_PARQUET = FACPKG / '데이터' / '서울시설_2020_2025_분석용.parquet'
BOUND_GPKG = CORE / 'data' / 'seoul_boundaries_all.gpkg'           # layers: dong_424, official_livingzone_116_dongbased, leiden_2020_116, leiden_2025_116
DONG_LZ_MAP = CORE / 'data' / 'dong_to_official_livingzone_mapping_424.csv'
DONG_LD_MAP = {2020: CORE/'data'/'dong_to_leiden_2020_mapping_424.csv', 2025: CORE/'data'/'dong_to_leiden_2025_mapping_424.csv'}
GRID100_SHP = SGIS / '01_격자100m' / '경계_2025' / 'grid_다사_100M.shp'
GRID100_STATS = SGIS / '01_격자100m' / '통계_2019_2024'             # {year}년_{인구|가구|사업체|종사자}_다사_100M.csv (cp949, header 없음: year, GRID_CD, item, value)
OA_SHP = SGIS / '02_집계구' / '경계_2025_2Q' / 'bnd_oa_00_2025_2Q.shp'

# 시점
YEARS = {2020: dict(ref='2019-12-31', pop_year=2019, osm='south-korea-200101.osm.pbf', osm_date='2020-01-01'),
         2025: dict(ref='2024-12-31', pop_year=2024, osm='south-korea-250101.osm.pbf', osm_date='2025-01-01')}
OSM_URL = 'https://download.geofabrik.de/asia/{file}'

# 지표 상수 (지표정의_확정.md)
WALK_KMH = 4.0
T_SEC = 900            # 15분 본
T_SENS_SEC = 600       # 10분 민감도
TTM_MAX_SEC = 1800     # 소요시간표 저장 상한 30분
SEOUL_BUFFER_M = 2000  # 네트워크 자르기 버퍼
SNAP_MAX_M = 200       # 격자 중심 → 노드 연결 거리 표시 기준
CRS = 5179

# 33종 → 카테고리 (분석용 파일의 '시설' 값 기준)
CAT_A = {
 '교육': ['유치원','학교','청소년수련시설'],
 '보육·복지': ['어린이집','노인 이용시설','장애인 이용시설','가족센터(자치구 본소)'],
 '의료': ['의원','약국','병원급','보건소·보건지소','응급의료기관','산후조리원'],
 '문화': ['공공도서관','문화기반시설','등록공연장'],
 '체육': ['체육시설업'],
 '행정·안전': ['주민센터','소방서·119안전센터'],
 '소매': ['일상소매','식료품소매(즉석판매·제과)','대규모점포(주요4업태)'],
 '생활서비스': ['일반음식점','휴게음식점','미용업','이용업','세탁업','목욕장업'],
}
CAT_A4 = {'교육·복지': ['교육','보육·복지'], '의료': ['의료'], '체육·문화': ['체육','문화'], '소매·서비스·행정': ['소매','생활서비스','행정·안전']}
CONTROL = ['버스정류장','지하철역','따릉이 대여소','주유소','노인 입소시설']
# 묶음 B: (카테고리, 시설, 세부조건(None=전체), τ분)
CAT_B = [
 ('교육','유치원',None,10), ('교육','학교',lambda s: str(s).startswith('초등학교'),15),
 ('돌봄','어린이집',None,5),
 ('의료','의원',None,10), ('의료','약국',None,10),
 ('체육','체육시설업',lambda s: s in ('체력단련장','체육도장','수영장','종합체육시설'),10),
 ('편의','일상소매',None,10),
]
BOUNDARY_CONDS = ['none','dong','lz','ld','ku']
# 2SFCA 보고 우선 항목(공공시설 단일 종, 지표정의_확정.md 3.4)
SFCA_PUBLIC = ['공공도서관', '주민센터', '보건소·보건지소', '어린이집', '유치원', '학교', '노인 이용시설']
# 2SFCA 카테고리 공급에서 빼는 행: 다른 종과 같은 시설(문화기반시설의 공공도서관 = 공공도서관 종). 시설 항목에서는 빼지 않는다.
SUPPLY_CAT_EXCLUDE = {'문화기반시설': ['공공도서관']}

# 시설–경계 연결표(a02 산출)가 만들어진 원본의 해시 기록 — a02가 쓰고 a06·a10이 읽는다
UNITS_PARQUET = DATA / 'facility' / 'facility_2020_2025_units.parquet'
UNITS_SOURCE_JSON = DATA / 'facility' / 'facility_2020_2025_units.source.json'


def units_source_sha256():
    """연결표를 만든 시설 원본의 SHA-256 (기록이 없으면 None)."""
    import json
    try:
        return json.loads(UNITS_SOURCE_JSON.read_text(encoding='utf-8'))['source_sha256']
    except (OSError, KeyError, ValueError):
        return None


def runtime_env():
    """실행 환경(파이썬·핵심 라이브러리 판). 결과 재현 조건으로 run_meta에 남긴다."""
    import platform, sys
    import numpy, pandas, pyarrow
    return dict(python=sys.version.split()[0], platform=platform.platform(), numpy=numpy.__version__,
                pandas=pandas.__version__, pyarrow=pyarrow.__version__)
