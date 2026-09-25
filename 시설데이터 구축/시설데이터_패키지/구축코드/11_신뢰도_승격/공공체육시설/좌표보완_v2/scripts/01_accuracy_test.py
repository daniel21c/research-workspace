# -*- coding: utf-8 -*-
"""1단계 정확도 시험(사전 등록): 주소 정확 지오코딩 좌표(coord_method=geocode_kakao_exact/geocode_vworld_exact)가 있는 핵심종목 50곳을
구·종목 층화로 뽑아(2025_01 명부, seed=20260924: 구마다 2곳, 같은 구 안에서는 다른 종목, 전체적으로 덜 뽑힌 종목 우선),
좌표·주소를 모른다고 보고 이름+구+종목만으로 v2lib.search 를 적용 → 기존 좌표와 EPSG:5179 거리.
PASS = 채택된 결과의 거리 중앙값 < 100 m AND 90백분위 < 250 m. (채택률·결과없음 비율도 보고)"""
import sys, json; sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import v2lib as L

d = pd.read_parquet(L.PUB / 'facilities_공공체육시설_2025_01.parquet')
pool = d[(d.scope_flag == '핵심종목') & d.coord_method.isin(['geocode_kakao_exact', 'geocode_vworld_exact']) & (d.inside_seoul == True)].copy()
rng = np.random.default_rng(20260924)
pool = pool.iloc[rng.permutation(len(pool))]
cnt = {}; picked = []; per_gu = {g: [] for g in L.GU}
for rnd in range(2):
    for g in [L.GU[i] for i in rng.permutation(25)]:
        c = pool[(pool.gu == g) & ~pool.index.isin(picked) & ~pool.facility_subtype.isin(per_gu[g])]
        if len(c) == 0: continue
        c = c.assign(_n=c.facility_subtype.map(lambda s: cnt.get(s, 0))).sort_values('_n', kind='stable')
        i = c.index[0]; picked.append(i); per_gu[g].append(c.at[i, 'facility_subtype'])
        cnt[c.at[i, 'facility_subtype']] = cnt.get(c.at[i, 'facility_subtype'], 0) + 1
while len(picked) < 50:  # 구에 후보가 모자라면 종목 균형으로 보충
    c = pool[~pool.index.isin(picked)]; c = c.assign(_n=c.facility_subtype.map(lambda s: cnt.get(s, 0))).sort_values('_n', kind='stable')
    i = c.index[0]; picked.append(i); cnt[c.at[i, 'facility_subtype']] = cnt.get(c.at[i, 'facility_subtype'], 0) + 1
t = pool.loc[picked[:50]]
rows = []
for i, r in t.iterrows():
    s = L.search(r['name'], r['gu'], r['facility_subtype'])
    dm = round(L.dist(s['lon'], s['lat'], r.lon, r.lat), 1) if s['result'] == 'accepted' else None
    rows.append(dict(facility_id=r.facility_id, name=r['name'], 구=r.gu, 종목=r.facility_subtype, dist_m=dm, matched=s['result'] == 'accepted',
                     result=s['result'], coord_precision=s['precision'], query=s['query'], place_name=s['place_name'], place_addr=s['place_addr'],
                     category=s['category'], score=s['score'], reason=s['reason'], trace=s['trace']))
o = pd.DataFrame(rows); o.to_csv(L.V2 / 'accuracy_test_공공체육시설.csv', index=False, encoding='utf-8-sig')
m = o[o.matched]; dd = m.dist_m
res = dict(n=len(o), matched=int(o.matched.sum()), match_rate=round(o.matched.mean() * 100, 1),
           no_result=int((o.result == 'no_result').sum()), rejected=int((o.result == 'rejected').sum()),
           no_accept_rate=round((~o.matched).mean() * 100, 1),
           median_m=round(float(dd.median()), 1), p90_m=round(float(dd.quantile(.9)), 1), mean_m=round(float(dd.mean()), 1), max_m=round(float(dd.max()), 1),
           share_within_100m=round(float((dd < 100).mean() * 100), 1), share_within_250m=round(float((dd < 250).mean() * 100), 1),
           n_over_250m=int((dd >= 250).sum()), precision=m.coord_precision.value_counts().to_dict(),
           by_precision={k: dict(n=int(len(g)), median=round(float(g.dist_m.median()), 1), p90=round(float(g.dist_m.quantile(.9)), 1)) for k, g in m.groupby('coord_precision')},
           n_gu=int(o['구'].nunique()), n_type=int(o['종목'].nunique()), type_counts=o['종목'].value_counts().to_dict())
res['PASS'] = bool(res['median_m'] < 100 and res['p90_m'] < 250)
json.dump(res, open(L.V2 / 'accuracy_test_summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
print(o[['name', '구', '종목', 'result', 'coord_precision', 'dist_m', 'place_name', 'reason']].to_string())
