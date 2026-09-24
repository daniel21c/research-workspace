# -*- coding: utf-8 -*-
"""공공체육 핵심종목 좌표 보완 양천구 시범 (2026-09-25). 규칙은 00_사전등록.md 그대로.
0 자치구 일치 검증 → 1 주소 정제·정확일치 재지오코딩 → 2 OA-21779 대조(R1·R2·R3) → 3 두 시점 연결 → 두 번째 근거(Kakao 키워드 POI) 거리.
입력은 읽기만 하고 결과는 이 폴더에만 쓴다. API 키는 mb.keys()로 읽기만 하고 출력·저장하지 않는다.
실행: python 01_pilot_yangcheon.py"""
import sys, json, shutil, re
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
PUB = HERE.parent; V2 = PUB / '좌표보완_v2'; V1 = PUB.parents[1]
sys.path.insert(0, str(V2 / 'scripts'))
import v2lib                                   # mb, coord_fill 경로도 함께 잡힘
from v2lib import mb
import coord_fill as CF

CACHE = HERE / 'cache'
CACHE.mkdir(exist_ok=True)
for p in (V2 / 'cache').glob('*.json'):        # v2 검색 캐시 재사용(v2 폴더는 건드리지 않음)
    if not (CACHE / p.name).exists(): shutil.copy2(p, CACHE / p.name)
v2lib.CACHE = CACHE

GU, GU_CD = '양천구', '11150'
BUILDING = {'수영장', '생활체육관', '구기체육관', '투기체육관', '빙상장'}
SNAPS = ['2020_01', '2025_01']


def gu_code_map():
    d = pd.concat([pd.read_parquet(V2 / f'facilities_공공체육시설_{s}.parquet') for s in SNAPS])
    d = d[d.adm_dong_cd.fillna('').astype(str).str.len() == 8]
    return d.assign(p=d.adm_dong_cd.astype(str).str[:5]).groupby('gu_seoul').p.agg(lambda s: s.value_counts().index[0]).to_dict()


def dong_of(lon, lat):
    s = mb.spatial(pd.DataFrame({'lon': [lon], 'lat': [lat]}))
    return str(s.at[0, 'adm_dong_cd'] or '')


def geocode_in_gu(addr):
    """정확일치 지오코딩 + 양천구 안. 반환 (lon, lat, method, detail, used_addr) 또는 None."""
    for v in [mb.clean(addr)] + CF.normalize_variants(addr):
        lon, lat, meth, det = mb.geocode(v, CACHE)
        if lon is None: continue
        if dong_of(lon, lat)[:5] != GU_CD: return ('OUT', lon, lat, meth, f'{det} (양천구 밖)', v)
        return ('OK', lon, lat, meth, det, v)
    return None


def oa_list():
    d = CF.oa21779()
    d = d[d.gu == GU].copy()
    d['addr'] = d['시설주소'].str.strip()
    return d


def match_list(row, L):
    st, nm = row.facility_subtype, row['name']
    ok = CF.TYPE_OK.get(st, set())
    nn = CF.nname(nm, GU)
    c = L[(L.nn == nn) & L['시설종류'].isin(ok)]
    if len(c) and c.addr.nunique() == 1: return 'R1', c.iloc[0]
    toks = [re.sub(r'\d+$', '', t) for t in v2lib.core_tokens(nm, GU)]
    toks = [t.replace(' ', '') for t in toks if len(t) >= 2]
    if toks:
        c = L[L['시설종류'].isin(ok) & L['시설명'].str.replace(' ', '').map(lambda s: all(t in s for t in toks))]
        if len(c) and c.addr.nunique() == 1: return 'R2', c.iloc[0]
    host, kind = v2lib.host_of(nm, GU)
    if host and kind == 'host_building':
        c = L[L.nn == CF.nname(host, GU)]
        if len(c) and c.addr.nunique() == 1: return 'R3', c.iloc[0]
    return None, None


def main():
    gmap = gu_code_map()
    assert gmap[GU] == GU_CD, gmap[GU]
    L = oa_list()
    frames = {s: pd.read_parquet(V2 / f'facilities_공공체육시설_{s}.parquet') for s in SNAPS}
    log = []
    res = {}
    for s in SNAPS:
        d = frames[s]
        q = d[(d.scope_flag == '핵심종목') & (d.gu_seoul == GU)].copy()
        q['p_strict'] = q.coord_valid_v2.fillna(False).astype(bool)
        q['p_step'] = np.where(q.p_strict, 'v2_strict', '')
        for c in ['p_lon', 'p_lat', 'p_method', 'p_detail', 'p_addr', 'p_list_rule', 'p_list_src', 'p_time_basis', 'p_second', 'p_second_m', 'p_accept']:
            q[c] = pd.NA
        # 0 자치구 일치
        q['p_gu_mismatch'] = False
        for i in q.index[q.p_strict]:
            if str(q.at[i, 'adm_dong_cd'] or '')[:5] != GU_CD:
                q.at[i, 'p_strict'] = False; q.at[i, 'p_step'] = 'gu_mismatch'; q.at[i, 'p_gu_mismatch'] = True
        # 1 주소 정제
        for i in q.index[~q.p_strict]:
            a = str(q.at[i, 'address'] or '').strip()
            if not a: continue
            r = geocode_in_gu(a)
            if r and r[0] == 'OK':
                q.loc[i, ['p_lon', 'p_lat', 'p_method', 'p_detail', 'p_addr']] = r[1:]
                q.at[i, 'p_step'] = 'M1_address'
            elif r and r[0] == 'OUT':
                q.at[i, 'p_detail'] = r[4]
        # 2 공식 목록
        for i in q.index[(~q.p_strict) & q.p_lon.isna()]:
            rule, m = match_list(q.loc[i], L)
            if rule is None: continue
            r = geocode_in_gu(m.addr)
            q.at[i, 'p_list_rule'] = rule
            q.at[i, 'p_list_src'] = f"OA-21779 체육시설일련번호={m['체육시설일련번호']} | {m['시설명']} | {m['시설종류']} | {m.addr}"
            if r and r[0] == 'OK':
                q.loc[i, ['p_lon', 'p_lat', 'p_method', 'p_detail', 'p_addr']] = r[1:]
                q.at[i, 'p_step'] = f'M2_{rule}'; q.at[i, 'p_time_basis'] = 'current_list'
            else:
                q.at[i, 'p_detail'] = r[4] if r else f'목록 주소 정확일치 실패({m.addr})'
        res[s] = q
    # 3 두 시점 연결
    for s, o in [('2020_01', '2025_01'), ('2025_01', '2020_01')]:
        q, r = res[s], res[o]
        for i in q.index[(~q.p_strict) & q.p_lon.isna()]:
            fid = q.at[i, 'facility_id']; a = str(q.at[i, 'address'] or '').strip()
            j = r.index[(r.facility_id == fid) & (r.p_step.isin(['v2_strict']) | r.p_step.str.startswith('M', na=False))]
            if len(j) != 1: continue
            j = j[0]; b = str(r.at[j, 'address'] or '').strip()
            if a and b and mb.clean(a) != mb.clean(b): continue
            lon = r.at[j, 'p_lon'] if pd.notna(r.at[j, 'p_lon']) else r.at[j, 'lon']
            lat = r.at[j, 'p_lat'] if pd.notna(r.at[j, 'p_lat']) else r.at[j, 'lat']
            q.loc[i, ['p_lon', 'p_lat']] = [float(lon), float(lat)]
            q.at[i, 'p_method'] = 'borrowed_same_facility_id_other_year'; q.at[i, 'p_step'] = 'M3_other_year'
            q.at[i, 'p_detail'] = f'{o} {r.at[j, "p_step"]}'
    # 두 번째 근거 + 채택
    for s in SNAPS:
        q = res[s]
        for i in q.index[q.p_step.str.startswith('M', na=False)]:
            row = q.loc[i]
            sr = v2lib.search(row['name'], GU, row.facility_subtype)
            if sr['result'] == 'accepted':
                dm = v2lib.dist(float(row.p_lon), float(row.p_lat), sr['lon'], sr['lat'])
                q.at[i, 'p_second'] = f"{sr['place_name']} ({sr['precision']}, {sr['place_addr']})"; q.at[i, 'p_second_m'] = round(dm, 1)
                q.at[i, 'p_accept'] = 'verified' if dm <= 250 else 'conflict'
            else:
                host, kind = v2lib.host_of(row['name'], GU)
                building = row.facility_subtype in BUILDING or row.p_list_rule == 'R3' or kind == 'host_building'
                q.at[i, 'p_second'] = f"없음({sr['result']}:{sr['reason']})"
                q.at[i, 'p_accept'] = 'address_only_building' if building else 'unverified_open_site'
            if q.at[i, 'p_accept'] in ('verified', 'address_only_building'): q.at[i, 'p_strict'] = True
        res[s] = q
    # 요약
    summ = {}
    for s in SNAPS:
        q = res[s]
        before = int(q.coord_valid_v2.fillna(False).astype(bool).sum())
        summ[s] = dict(n=len(q), strict_v2=before, rate_v2=round(before / len(q) * 100, 1),
                       gu_mismatch=int(q.p_gu_mismatch.sum()),
                       list_matched_but_no_exact_address=int((q.p_list_rule.notna() & ~q.p_step.str.startswith('M', na=False)).sum()),
                       filled_candidates=int(q.p_step.str.startswith('M', na=False).sum()),
                       by_step=q.loc[q.p_step.str.startswith('M', na=False), 'p_step'].value_counts().to_dict(),
                       by_accept=q.p_accept.value_counts().to_dict(),
                       strict_after=int(q.p_strict.sum()), rate_after=round(q.p_strict.mean() * 100, 1),
                       n_needed_95=int(np.ceil(0.95 * len(q))),
                       remaining=q.loc[~q.p_strict, 'name'].tolist(),
                       remaining_blank_address=int((~q.p_strict & q.address.fillna('').str.strip().eq('')).sum()))
    conflict = sum(summ[s]['by_accept'].get('conflict', 0) for s in SNAPS)
    summ['PASS'] = bool(all(summ[s]['rate_after'] >= 95 for s in SNAPS) and conflict == 0)
    # 부수 점검: 서울 전체 기존 엄격 좌표의 자치구 불일치
    side = {}
    for s in SNAPS:
        d = frames[s]
        k = d[(d.scope_flag == '핵심종목') & d.coord_valid_v2.fillna(False).astype(bool)].copy()
        k['coord_gu_cd'] = k.adm_dong_cd.fillna('').astype(str).str[:5]
        k['roster_gu_cd'] = k.gu_seoul.map(gmap)
        mm = k[k.coord_gu_cd != k.roster_gu_cd]
        n_core = int((d.scope_flag == '핵심종목').sum())
        side[s] = dict(n_core=n_core, strict_v2=len(k), gu_mismatch=len(mm),
                       rate_v2=round(len(k) / n_core * 100, 1), rate_if_mismatch_removed=round((len(k) - len(mm)) / n_core * 100, 1),
                       rows=[f"{r.facility_id} {r['name']} | 명부 {r.gu_seoul} | 주소 {r.address} | 좌표 구코드 {r.coord_gu_cd}" for _, r in mm.iterrows()])
    summ['seoul_gu_mismatch_check'] = side
    cols = ['year_snapshot', 'facility_id', 'name', 'facility_subtype', 'address', 'coord_method', 'coord_valid_v2', 'adm_dong_cd',
            'p_gu_mismatch', 'p_step', 'p_method', 'p_detail', 'p_addr', 'p_list_rule', 'p_list_src', 'p_time_basis', 'p_lon', 'p_lat', 'p_second', 'p_second_m', 'p_accept', 'p_strict']
    out = pd.concat([res[s][cols] for s in SNAPS])
    out.to_csv(HERE / 'pilot_양천구_행별.csv', index=False, encoding='utf-8-sig')
    (HERE / 'pilot_summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(json.dumps({s: {k: v for k, v in summ[s].items() if k != 'remaining'} for s in SNAPS}, ensure_ascii=False, indent=1))
    print('PASS', summ['PASS'])
    print(json.dumps({s: {k: v for k, v in side[s].items() if k != 'rows'} for s in SNAPS}, ensure_ascii=False))


if __name__ == '__main__':
    main()
