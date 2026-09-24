"""공연장 좌표 미해결 행 재지오코딩: 원 빌드는 도로명 키만 조회(도로명 없으면 지번). 여기서는 두 키를 모두(도로명→지번) 조회.
Kakao 우선, VWorld 보조, 건물번호/번지 정확 일치만 채택(lic_common.geocode_one). 캐시: raw/geocoding/. 키 값은 출력하지 않음."""
import sys, json, time
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '01_인허가/공연장'
sys.path.insert(0, str(V1 / '01_인허가/_common'))
from lic_common import address_key, geocode_one, load_keys
raw = pd.read_csv(SRC / 'raw/performance_halls_seoul_OA-16021.csv', encoding='cp949', dtype=str)
raw['facility_id'] = 'LIC-performance_halls-' + raw['개방자치단체코드'].fillna('') + '-' + raw['관리번호'].fillna('')
R = raw.drop_duplicates('facility_id').set_index('facility_id')
need = set()
for k in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_공연장_{k}.parquet'); need |= set(d.loc[d.coord_method == 'unresolved', 'facility_id'])
secret = load_keys(); cache = HERE / 'raw/geocoding'; out = {}; t0 = time.time(); n_q = 0
for fid in sorted(need):
    if fid not in R.index: out[fid] = dict(status='no_raw'); continue
    keys = [x for x in (address_key(R.at[fid, '도로명주소'] or ''), address_key(R.at[fid, '지번주소'] or '')) if x]
    res = None
    for kk in keys:
        res = geocode_one(kk, secret, cache); n_q += 1
        if res: out[fid] = dict(status='ok', key_kind=kk.split(':')[0], lon=res[0], lat=res[1], method=res[2]); break
    if not res: out[fid] = dict(status='fail' if keys else 'no_parsable_address', n_keys=len(keys))
    if time.time() - t0 > 160: break
json.dump(out, open(HERE / 'geocode_retry_공연장.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
s = pd.Series([v['status'] for v in out.values()]).value_counts().to_dict()
print('need', len(need), 'done', len(out), s, 'queries', n_q, round(time.time() - t0, 1), 's')
