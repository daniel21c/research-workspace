"""좌표 없는 행(2020_01·2025_01) 재지오코딩 — Kakao 우선, VWorld 보조, 건물번호/번지 정확 일치만 채택.
lic_common.address_key / geocode_one 을 그대로 사용(원 빌드와 동일 규칙). 캐시: ../raw/geocoding/ (키 미저장).
사용: python geocode_missing.py <시설> <budget_sec>   (캐시가 있으면 재조회하지 않으므로 반복 실행으로 이어서 진행)
"""
import sys, time, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
HERE = Path(__file__).resolve().parent
V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists())
sys.path.insert(0, str(V1 / '01_인허가/_common'))
from lic_common import address_key, geocode_one, load_keys, detect_enc
FAC = sys.argv[1]; BUDGET = float(sys.argv[2]) if len(sys.argv) > 2 else 150
OUT = V1 / '11_신뢰도_승격' / FAC
LIC = V1 / '01_인허가' / FAC
CACHE = OUT / 'raw/geocoding'
t0 = time.time()
cand_p = OUT / 'raw/geocode_candidates.parquet'
if not cand_p.exists():
    fr = []
    for k in ('2020_01', '2025_01'):
        d = pd.read_parquet(LIC / f'facilities_{FAC}_{k}.parquet')
        fr.append(d[d.coord_method == 'unresolved'][['facility_id', 'source_file', 'source_row_id', 'address']])
    u = pd.concat(fr).drop_duplicates('facility_id')
    u['org'] = u.facility_id.str.extract(r'-(3\d{6})-')[0]
    u['mgmt'] = u.source_row_id.str.split(':', n=1).str[1]
    want = set(zip(u.org, u.mgmt)); rows = []
    for sf in u.source_file.unique():
        p = LIC / sf; enc = detect_enc(p)
        for ch in pd.read_csv(p, encoding=enc, encoding_errors='replace', dtype=str, chunksize=200000,
                              usecols=lambda c: c.strip().lstrip('﻿') in ('개방자치단체코드', '관리번호', '도로명주소', '지번주소')):
            ch.columns = [c.strip().lstrip('﻿') for c in ch.columns]
            m = [(a, b) in want for a, b in zip(ch['개방자치단체코드'].str.strip(), ch['관리번호'].str.strip())]
            rows.append(ch[m])
    r = pd.concat(rows); r['org'] = r['개방자치단체코드'].str.strip(); r['mgmt'] = r['관리번호'].str.strip()
    u = u.merge(r[['org', 'mgmt', '도로명주소', '지번주소']].drop_duplicates(['org', 'mgmt']), on=['org', 'mgmt'], how='left')
    u['key_road'] = u['도로명주소'].fillna('').map(address_key)
    u['key_parcel'] = u['지번주소'].fillna('').map(address_key)
    u['key_addr'] = u['address'].fillna('').map(address_key)
    u.to_parquet(cand_p, index=False)
u = pd.read_parquet(cand_p)
keys = []
for c in ('key_road', 'key_addr', 'key_parcel', 'key_parcel2'):
    if c in u: keys += [k for k in u[c].tolist() if k]
keys = list(dict.fromkeys(keys))
import hashlib
todo = [k for k in keys if not (CACHE / (hashlib.sha256(k.encode()).hexdigest() + '.json')).exists()]
print(f'rows {len(u)}, unique keys {len(keys)}, todo {len(todo)}', flush=True)
secret = load_keys(); done = 0
# 전역 요청 속도 제한: 모든 스레드 합계 초당 약 9.5건(≤10) (Kakao·VWorld 요청 모두 포함)
import threading, urllib.request as _ur
_lock = threading.Lock(); _last = [0.0]; _orig = _ur.urlopen
def _limited(*a, **kw):
    with _lock:
        w = _last[0] + 0.105 - time.time()
        if w > 0: time.sleep(w)
        _last[0] = time.time()
    return _orig(*a, **kw)
_ur.urlopen = _limited
def work(k):
    geocode_one(k, secret, CACHE)
with ThreadPoolExecutor(max_workers=2) as pool:   # 각 스레드 요청 간 ≥0.05s+지연 → 합계 초당 10건 이하
    it = iter(todo)
    while time.time() - t0 < BUDGET:
        batch = [k for _, k in zip(range(20), it)]
        if not batch: break
        list(pool.map(work, batch)); done += len(batch)
        time.sleep(0.5)
left = len(todo) - done
print(json.dumps({'done_this_run': done, 'left': max(left, 0), 'sec': round(time.time() - t0, 1)}), flush=True)
