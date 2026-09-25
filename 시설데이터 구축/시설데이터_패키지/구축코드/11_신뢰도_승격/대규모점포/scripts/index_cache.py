"""지오코딩 캐시(JSON 다수)를 한 번 읽어 key→(lon,lat,method) 색인(parquet)으로 요약. 체크포인트로 이어서 실행.
사용: python index_cache.py <시설> <budget_sec>"""
import sys, time, json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists())
sys.path.insert(0, str(V1 / '01_인허가/_common'))
from lic_common import geocode_one
FAC = sys.argv[1]; B = float(sys.argv[2]); t0 = time.time()
CACHE = V1 / '11_신뢰도_승격' / FAC / 'raw/geocoding'; IDX = CACHE.parent / 'geocode_index.parquet'
done = pd.read_parquet(IDX) if IDX.exists() else pd.DataFrame(columns=['file', 'key', 'lon', 'lat', 'method'])
seen = set(done.file); rows = []
for p in sorted(CACHE.glob('*.json')):
    if p.name in seen: continue
    if time.time() - t0 > B: break
    r = json.loads(p.read_text(encoding='utf-8')); g = geocode_one(r['address_key'], {}, CACHE)
    rows.append({'file': p.name, 'key': r['address_key'], 'lon': g[0] if g else None, 'lat': g[1] if g else None, 'method': g[2] if g else None})
out = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
out.to_parquet(IDX, index=False)
print(len(out), 'indexed;', len(list(CACHE.glob('*.json'))) - len(out), 'left')
