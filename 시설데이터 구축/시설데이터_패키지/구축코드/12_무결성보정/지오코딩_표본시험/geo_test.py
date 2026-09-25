# -*- coding: utf-8 -*-
"""지오코딩 검증 표본 시험 (읽기 전용, 결과는 이 폴더에만).
A: 원천 좌표 + 주소가 모두 있는 행 → 주소를 원 빌드 규칙(mb.geocode 정확일치)으로 지오코딩 → 원천 좌표와 거리 (지오코더 정확도)
B: 지오코딩·차용으로 채운 행 → Kakao 키워드 검색 '<구> <시설명>' 중 같은 구·이름 유사 POI → 거리 (채운 좌표의 독립 확인)
표본: 시설별 층화, seed 20260925. API 키는 mb.keys()로 읽기만 하고 출력·저장하지 않는다."""
import sys, re, json, time, glob, os, hashlib, difflib
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1]   # 구축코드
sys.path.insert(0, str(V1 / '02_명부' / '_lib'))
import mb
from pyproj import Transformer
TR = Transformer.from_crs(4326, 5179, always_xy=True)
CACHE = HERE / 'cache'; CACHE.mkdir(exist_ok=True)
GU_RE = r'((?:종로|중|용산|성동|광진|동대문|중랑|성북|강북|도봉|노원|은평|서대문|마포|양천|강서|구로|금천|영등포|동작|관악|서초|강남|송파|강동)구)'
rng = np.random.default_rng(20260925)
a = pd.read_parquet(V1.parent / '데이터' / '서울시설_2020_2025_분석용.parquet')
a = a[a['분석가능']].copy()
a['gu'] = a.address.str.extract(GU_RE, expand=False)


def dist(lo1, la1, lo2, la2):
    x1, y1 = TR.transform(lo1, la1); x2, y2 = TR.transform(lo2, la2)
    return float(np.hypot(x1 - x2, y1 - y2))


def strat(df, n_total):
    g = df.groupby('시설'); k = max(1, n_total // g.ngroups)
    return pd.concat([x.sample(min(len(x), k), random_state=int(rng.integers(1e9))) for _, x in g])


# ---------------- A
src = a[(a.coord_method == 'source') & a.address.notna() & a.gu.notna()]
sa = strat(src, 300)
ra = []
for _, r in sa.iterrows():
    lon, lat, meth, det = mb.geocode(r.address, CACHE)
    d = dist(r.lon, r.lat, lon, lat) if lon is not None else None
    ra.append(dict(시설=r['시설'], year=r.year, facility_id=r.facility_id, address=r.address, result=meth, dist_m=d))
A = pd.DataFrame(ra); A.to_csv(HERE / 'A_geocoder_vs_source.csv', index=False, encoding='utf-8-sig')


# ---------------- B
def kw(q):
    p = CACHE / f"kw_{hashlib.sha1(q.encode()).hexdigest()[:20]}.json"
    if p.exists(): return json.loads(p.read_text(encoding='utf-8'))
    time.sleep(0.12)
    r = mb._S.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': q, 'size': 15},
                  headers={'Authorization': 'KakaoAK ' + mb.keys()['KAKAO_REST_API_KEY']}, timeout=20)
    j = r.json().get('documents', []) if r.status_code == 200 else []
    p.write_text(json.dumps(j, ensure_ascii=False), encoding='utf-8'); return j


def nn(s): return re.sub(r'[^0-9A-Za-z가-힣]', '', re.sub(r'\([^)]*\)', '', str(s)))


geo = a[a.coord_method.str.contains('geocode|borrowed|search_verified', regex=True) & a.gu.notna() & a.name.notna()]
sb = strat(geo, 300)
rb = []
for _, r in sb.iterrows():
    name = re.sub(r'\s+', ' ', str(r['name'])).strip()
    docs = kw(f"{r.gu} {name}")
    key = nn(name); best = None
    for x in docs:
        if f'서울 {r.gu}' not in ((x.get('road_address_name') or '') + ' ' + (x.get('address_name') or '')): continue
        s = difflib.SequenceMatcher(None, key, nn(x.get('place_name'))).ratio()
        if s >= 0.6 and (best is None or s > best[0]): best = (s, x)
    if best:
        d = dist(r.lon, r.lat, float(best[1]['x']), float(best[1]['y']))
        rb.append(dict(시설=r['시설'], year=r.year, facility_id=r.facility_id, name=name, coord_method=r.coord_method, poi=best[1]['place_name'], sim=round(best[0], 2), dist_m=round(d, 1)))
    else:
        rb.append(dict(시설=r['시설'], year=r.year, facility_id=r.facility_id, name=name, coord_method=r.coord_method, poi='', sim=None, dist_m=None))
B = pd.DataFrame(rb); B.to_csv(HERE / 'B_geocoded_vs_poi.csv', index=False, encoding='utf-8-sig')


def summ(D):
    d = D.dist_m.dropna()
    return dict(n=len(D), matched=len(d), median_m=round(d.median(), 1), p90_m=round(d.quantile(.9), 1), within_50=round((d <= 50).mean() * 100, 1),
                within_100=round((d <= 100).mean() * 100, 1), within_250=round((d <= 250).mean() * 100, 1), over_500=int((d > 500).sum()))
out = dict(A=summ(A), B=summ(B), A_by_fac=A.groupby('시설').dist_m.median().round(1).to_dict(),
           B_by_method={k: summ(g) for k, g in B.groupby(B.coord_method.str.replace(r'_via.*|_reuse.*|_fix.*', '', regex=True))})
(HERE / 'summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
