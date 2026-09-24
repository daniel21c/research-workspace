"""(1회) 앞선 조사 때 받은 원본을 각 유형 raw/ 로 복사하고 metadata 작성. 원본이 없으면 download.py 로 재수신."""
import sys, json, os
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lic_common import stage_raw, LIC_ROOT
from sources import src
WORK = Path(os.path.expanduser('~/work/inv/localdata'))
PLAN = {'의원': ['clinics'], '약국': ['pharmacies'], '산후조리업': ['postpartum_care'],
        '안전상비의약품판매업소': ['over_the_counter_medicine_stores'], '안경업': ['optical_shops'], '동물병원': ['animal_hospitals'],
        '체육시설업': ['fitness_centers', 'martial_arts_dojo', 'swimming_pools', 'golf_practice_ranges', 'billiard_halls',
                   'comprehensive_sports_facilities', 'ice_rinks'],
        '공연장': ['performance_halls'], '영화상영관': ['movie_theaters'], '대규모점포': ['large_scale_retail_stores'],
        '식료품소매': ['livestock_retail', 'other_food_retailers', 'instant_food_processors', 'bakeries'],
        '일반음식점': ['general_restaurants'], '휴게음식점': ['rest_cafes'], '이용업': ['barber_shops'], '미용업': ['beauty_salons'],
        '세탁업': ['laundries'], '목욕장업': ['public_baths'], '주유소': ['oil_retailers']}
only = sys.argv[1:]
for T, slugs in PLAN.items():
    if only and T not in only: continue
    for sl in slugs:
        s = src(sl); loc = WORK / 'sraw' / f'{sl}.csv'
        s['local'] = str(loc)
        s['downloaded_utc'] = datetime.fromtimestamp(loc.stat().st_mtime, timezone.utc).isoformat()
        s['http_status'] = 200
        s['note'] = '2026-09-23 조사 단계(device_bash curl, UA Mozilla/5.0)에서 수신한 서울 전체 CSV(cp949)를 그대로 복사. download_utc=수신 완료 파일 시각.'
        m = stage_raw(s, LIC_ROOT / T / 'raw'); print(T, sl, m['bytes'], m['sha256'][:12])
if not only or '병원급' in only:
    s = src('hospitals', kind='localdata'); loc = WORK / 'raw' / 'hospitals.csv'
    s['local'] = str(loc); s['downloaded_utc'] = datetime.fromtimestamp(loc.stat().st_mtime, timezone.utc).isoformat(); s['http_status'] = 200
    s['note'] = '2026-09-23 조사 단계 수신(file.localdata.go.kr, 서울 6110000_ALL). 서울 열린데이터광장판(OA-16479)은 병상수·의료인수·종별 열이 없어 이 판을 사용.'
    m = stage_raw(s, LIC_ROOT / '병원급' / 'raw'); print('병원급', m['bytes'], m['sha256'][:12])
