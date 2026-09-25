# -*- coding: utf-8 -*-
"""06_접근성분석 공통 설정. 경로·상수는 여기서만 정의한다. 정의 근거: 00_설계/지표정의_확정.md"""
from pathlib import Path
import os

HERE = Path(__file__).resolve().parent          # 02_scripts
ROOT = HERE.parent                                # 06_접근성분석
BASE = ROOT.parent                                # 00_박사논문_연구체계
# 로컬 VM(Cowork)에서는 mnt 경로, Windows PC에서는 D:\Research
_MNT = Path.home() / 'mnt'
def _pick(*cands):
    for c in cands:
        if c and Path(c).exists():
            return Path(c)
    return Path(cands[0])
CORE   = _pick(BASE / '00_공통_코어엔진', _MNT / '00_공통_코어엔진')
# 2026-09-25: 시설데이터는 패키지 하나로 정리됨 → 시설데이터 구축/시설데이터_패키지/ (데이터·문서·구축코드·SGIS)
FACPKG = _pick(BASE / '시설데이터 구축' / '시설데이터_패키지', _MNT / '시설데이터 구축' / '시설데이터_패키지')
FACDIR = FACPKG / '구축코드'
SGIS   = FACPKG / 'SGIS_인구경계_2019_2024'
GRID250_SRC = _pick(Path('D:/Research/1_OUTPUT/community_detection/OD 데이터(승훈이데이터)/종하_row_data/3. row_data/서울_격자_250_5179_clean.gpkg'),
                    _MNT / '1_OUTPUT/community_detection/OD 데이터(승훈이데이터)/종하_row_data/3. row_data/서울_격자_250_5179_clean.gpkg')
SECRETS = _pick(Path('D:/Research/_secrets/facility_api.env'), _MNT / '_secrets' / 'facility_api.env')

DATA = ROOT / '01_data'; OUT = ROOT / '03_output'; REC = ROOT / '04_구축기록'
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
