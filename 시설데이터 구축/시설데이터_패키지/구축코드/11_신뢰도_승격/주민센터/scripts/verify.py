# -*- coding: utf-8 -*-
"""주민센터: (1) 행정동 수 대조 — 행안부 하부행정기관 현황 4개 판(20190630/20201231/20240731/20251231)과 SGIS 경계(2019_4Q, 2025_2Q)로
목표일(2019-12-31, 2024-12-31) 행정동 집합을 확정하고 명부와 1:1 대응 확인, 기준일~목표일 사이 동 변동 점검.
(2) 좌표 보완 — ① 서울시 공중화장실 위치정보(OA-22586, 주민센터 개방화장실)의 도로명주소가 명부 주소와 정확히 같고 건물명이 해당 주민센터인 경우
그 지번으로 Kakao/VWorld 번지 일치 지오코딩, ② 주소 표기 정규화 재시도, ③ Kakao 키워드(동 주민센터) 결과 중 도로명+건물번호 일치.
원본(03_교육교통공원상가/community_center)은 읽기만."""
import sys, json, re
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11, geo11
import pandas as pd
V1 = u11.V1; GU = u11.GU; fac = u11.fac; mb = u11.mb
SRC = V1 / '03_교육교통공원상가' / 'community_center'


def nd(x):
    x = re.sub(r'\(.*?\)', '', str(x))
    x = re.sub(r'(주민센터|주민센토|행정복지센터|[·.\s제\-])', '', x)
    return x.replace('성복구', '성북구')


def ng(x): return re.sub(r'\s', '', str(x)).replace('성복구', '성북구')


# ---- (1) 행정동 집합
L = {}
for k in ['20190630', '20201231', '20240731', '20251231']:
    d = fac.read_csv_any(SRC / 'raw' / f'mois_하부행정기관_{k}.csv'); d = d[d['시도'].astype(str).str.contains('서울')]
    L[k] = set(d['시군구'].map(ng) + '_' + d['읍면동'].map(nd))
S = {}
for q in ['2019_4Q', '2025_2Q']:
    s = u11.sgis_dongs(q); S[q] = set(s.gu + '_' + s.NM.map(nd))
chg = dict(
    mois_0630_vs_sgis_2019_4Q=dict(only_mois=sorted(L['20190630'] - S['2019_4Q']), only_sgis=sorted(S['2019_4Q'] - L['20190630'])),
    mois_2019_0630_to_2020_1231=dict(removed=sorted(L['20190630'] - L['20201231']), added=sorted(L['20201231'] - L['20190630'])),
    mois_0731_vs_sgis_2025_2Q=dict(only_mois=sorted(L['20240731'] - S['2025_2Q']), only_sgis=sorted(S['2025_2Q'] - L['20240731'])),
    mois_2024_0731_to_2025_1231=dict(removed=sorted(L['20240731'] - L['20251231']), added=sorted(L['20251231'] - L['20240731'])),
    counts={k: len(v) for k, v in L.items()} | {'sgis_' + k: len(v) for k, v in S.items()})
# ---- (2) 좌표
toilet = pd.read_csv(FD / 'raw' / 'seoul_OA-22586_공중화장실.csv', encoding='cp949', dtype=str)
toilet['k'] = toilet['도로명주소'].map(lambda a: re.sub(r'\s', '', re.sub(r'\(.*?\)', '', str(a))).replace('서울특별시', ''))
summ = dict(dong_check=chg)
for snap, ref, tgt in [('2020_01', '20190630', '2019_4Q'), ('2025_01', '20240731', '2025_2Q')]:
    d = pd.read_parquet(SRC / f'facilities_community_center_{snap}.parquet')
    before = round(float(d.x_5179.notna().mean()), 4)
    d['coord_stage'] = d.lon.notna().map({True: 'original', False: 'missing'}); d['geocode_detail2'] = ''
    for i in d.index[d.lon.isna()]:
        k = re.sub(r'\s', '', re.sub(r'\(.*?\)', '', d.at[i, 'address'])).replace('서울특별시', '')
        dn = nd(d.at[i, 'dong_name']) if 'dong_name' in d else nd(d.at[i, 'name'])
        h = toilet[(toilet.k == k) & toilet['건물명'].fillna('').map(lambda b: '주민센터' in b and nd(b)[:2] == dn[:2])]
        if len(h):
            j = h.iloc[0]['지번주소']
            lon, lat, meth, det = mb.geocode(j, FD / 'raw' / 'geocoding')
            if lon is not None:
                d.at[i, 'lon'] = lon; d.at[i, 'lat'] = lat; d.at[i, 'coord_method'] = meth + '_via_toilet_jibun'
                d.at[i, 'coord_stage'] = 'filled_11'; d.at[i, 'geocode_detail2'] = f'OA-22586 도로명 일치({h.iloc[0]["건물명"]}) → 지번 {j} → {det}'
    d = geo11.fill(d, FD / 'raw' / 'geocoding', gu_col='gu_name')
    d = geo11.respatial(d, lib='fac')
    d['scope_flag'] = 'all'
    # 명부 ↔ 목표일 행정동 1:1
    key = set(d.gu_name.map(ng) + '_' + d.dong_name.map(nd))
    cov = geo11.coord_rate_by_gu(d, 'gu_name'); cov.to_csv(FD / f'coord_by_gu_주민센터_{snap}.csv', encoding='utf-8-sig')
    # 점이 떨어진 행정동 명칭 일치
    s = u11.sgis_dongs('2025_2Q'); cd2nm = dict(zip(s.CD.astype(str), s.NM.map(nd)))
    pin = d.adm_dong_cd.fillna('').astype(str).map(cd2nm)
    same = (pin == d.dong_name.map(nd))
    summ[snap] = dict(rows=len(d), target_dongs=len(S[tgt]), rows_vs_target_equal=len(d) == len(S[tgt]),
                      list_minus_target=sorted(key - S[tgt]), target_minus_list=sorted(S[tgt] - key),
                      coord_rate_before=before, coord_rate_after=round(float(d.x_5179.notna().mean()), 4),
                      filled=int((d.coord_stage == 'filled_11').sum()), filled_by=d[d.coord_stage == 'filled_11'].coord_method.value_counts().to_dict(),
                      still_missing=d[d.x_5179.isna()][['gu_name', 'name', 'address']].values.tolist(),
                      min_gu_rate=float(cov.rate.min()), min_gu=str(cov.rate.idxmin()), gu_below_85=cov.index[cov.rate < 0.85].tolist(),
                      point_in_same_named_dong_2025bnd=int(same.sum()), points=int(d.x_5179.notna().sum()))
    fac.write_out(d, FD, '주민센터', snap)
    d[d.coord_stage == 'filled_11'][['facility_id', 'name', 'address', 'coord_method', 'geocode_detail2']].to_csv(
        FD / f'filled_coords_주민센터_{snap}.csv', index=False, encoding='utf-8-sig')
rows = []
for snap, y, D, tgt in [('2020_01', 2019, '2019-12-31', '2019_4Q'), ('2025_01', 2024, '2024-12-31', '2025_2Q')]:
    d = pd.read_parquet(FD / f'facilities_주민센터_{snap}.parquet'); s = u11.sgis_dongs(tgt)
    t, st = u11.compare(d.groupby('gu_name').size(), s.groupby('gu').size(), label=snap)
    rows.append(dict(year=y, ref_date=D, level='서울', key='계', built=len(d), official=len(s), diff=len(d) - len(s),
                     official_source=f'SGIS 행정동 경계 {tgt} = 행안부 하부행정기관 {"20190630" if y == 2019 else "20240731"}판 동 집합(목표일 전후판 비교로 변동 없음 확인)'))
    for g in GU:
        rows.append(dict(year=y, ref_date=D, level='구', key=g, built=int(t.loc[g, 'built']), official=int(t.loc[g, 'official']), diff=int(t.loc[g, 'diff'])))
    summ[snap]['gu_compare'] = st
pd.DataFrame(rows).to_csv(FD / 'official_compare_주민센터.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(FD / 'summary_주민센터.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
