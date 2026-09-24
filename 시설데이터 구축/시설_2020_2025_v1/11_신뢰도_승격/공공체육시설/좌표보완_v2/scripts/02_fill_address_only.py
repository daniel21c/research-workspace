# -*- coding: utf-8 -*-
"""2단계(1단계 FAIL 분기, 사전 등록 규칙): 검색 방법으로는 채우지 않고 주소 기반 보완만 적용.
주소 기반 후보 = 두 시점 같은 시설((구, 정규화 명칭 nname, 종목) 키가 두 시점 각각 1건)에서 다른 시점 행이 엄격(주소 정확 지오코딩·
공식 명부 주소 차용·한강 시설지도) 좌표를 가질 때 그 좌표 적용(coord_method='borrowed_same_facility_other_year').
원 빌드의 키워드 좌표(kakao_place_name_gu)는 검색 방법 불합격으로 재검증할 수 없으므로 좌표는 그대로 두되 coord_valid_v2=False.
좌표가 바뀐 행이 있으면 lic_common.spatial_attach(원 빌드·v1 승격과 같은 함수)로 x/y·inside_seoul·adm_dong_cd·oa_cd·grid100_cd 재계산."""
import sys, json; sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import v2lib as L
sys.path.insert(0, str(L.V1 / '01_인허가/_common')); from lic_common import spatial_attach, tf

STRICT = ['geocode_kakao_exact', 'geocode_vworld_exact', 'borrowed_official_list_name_gu', 'borrowed_hangang_facility_map', 'borrowed_same_facility_other_year']
PREC = {'geocode_kakao_exact': 'address_point', 'geocode_vworld_exact': 'address_point', 'borrowed_official_list_name_gu': 'address_point',
        'borrowed_hangang_facility_map': 'facility_poi', 'kakao_place_name_gu': 'keyword_poi_unverified', 'borrowed_same_facility_other_year': 'address_point'}
EVID = {'geocode_kakao_exact': 'Kakao 주소검색(명부 주소, 건물번호/번지 일치)', 'geocode_vworld_exact': 'VWorld 주소검색(명부 주소, 건물번호/번지 일치)',
        'borrowed_official_list_name_gu': '서울 열린데이터 OA-21779/OA-1115 주소(borrow_source 열) → 정확 지오코딩',
        'borrowed_hangang_facility_map': 'https://hangang.seoul.go.kr/www/facility/map.tab?opt2=SPORTS&opt3=DM_SPORTS',
        'kakao_place_name_gu': 'Kakao 키워드 검색(원 빌드 3단계, 미검증)'}
acc = json.load(open(L.V2 / 'accuracy_test_summary.json', encoding='utf-8'))
D = {k: pd.read_parquet(L.PUB / f'facilities_공공체육시설_{k}.parquet') for k in ['2020_01', '2025_01']}
for d in D.values(): d['_key'] = [f'{g}|{L.nname(n, g)}|{s}' for g, n, s in zip(d.gu, d.name, d.facility_subtype)]
log = []
for k, o in [('2020_01', '2025_01'), ('2025_01', '2020_01')]:
    d, e = D[k], D[o]; vc_d, vc_e = d._key.value_counts(), e._key.value_counts()
    ok_e = e[e.coord_method.isin(STRICT[:4]) & (e.inside_seoul == True)].set_index('_key')
    tgt = d.index[d.scope_flag.ne('서울밖소재(분석제외)') & ~(d.coord_method.isin(STRICT[:4]) & (d.inside_seoul == True))]
    for i in tgt:
        key = d.at[i, '_key']; both = vc_e.get(key, 0) >= 1
        rec = dict(snapshot=k, facility_id=d.at[i, 'facility_id'], name=d.at[i, 'name'], gu=d.at[i, 'gu'], subtype=d.at[i, 'facility_subtype'],
                   scope_flag=d.at[i, 'scope_flag'], address_blank=str(d.at[i, 'address'] or '').strip() == '', coord_method_before=d.at[i, 'coord_method'],
                   in_both_years=both, time_rule=('두 시점 모두' if both else ('2020만' if k == '2020_01' else '2025만')))
        if both and vc_d[key] == 1 and vc_e[key] == 1 and key in ok_e.index:
            r = ok_e.loc[key]; X, Y = tf(4326, 5179).transform(r.lon, r.lat)
            d.loc[i, ['lon', 'lat', 'x_5179', 'y_5179']] = [r.lon, r.lat, X, Y]; d.at[i, 'coord_method'] = 'borrowed_same_facility_other_year'
            d.at[i, 'coord_evidence_url'] = f'{o} {r.facility_id} {r.coord_method} {r.address}'; rec['result'] = 'filled_same_facility_other_year'
        else:
            rec['result'] = 'not_filled'
        rec['search_method'] = '미적용(정확도 시험 FAIL: p90 {:.0f} m ≥ 250 m)'.format(acc['p90_m'])
        rec['note'] = ('다른 시점 같은 키 없음' if not both else ('다른 시점도 엄격 좌표 없음' if key not in ok_e.index else '키 중복'))  if rec['result'] == 'not_filled' else ''
        log.append(rec)
summ = {}; gurows = []
for k, d in D.items():
    changed = d.coord_method.eq('borrowed_same_facility_other_year')
    if changed.any(): d = spatial_attach(d)
    d['coord_valid_v2'] = d.coord_method.isin(STRICT) & (d.inside_seoul == True)
    d['coord_precision'] = d.coord_method.map(PREC)
    if 'coord_evidence_url' not in d: d['coord_evidence_url'] = None
    d['coord_evidence_url'] = d.coord_evidence_url.where(d.coord_evidence_url.notna(), d.coord_method.map(EVID))
    d['coord_second_source'] = None   # 검색 채움 없음 → 2차 출처 확인 대상 없음
    d['coord_v2_status'] = np.select([d.coord_valid_v2, d.coord_method.eq('kakao_place_name_gu'), d.coord_method.eq('unresolved')],
                                     ['엄격좌표(주소·공식목록)', '키워드좌표_미검증(검색법 시험 불합격, 점 분석 제외 권장)', '좌표없음'], '서울밖·기타')
    d = d.drop(columns=['_key']); D[k] = d
    d.to_parquet(L.V2 / f'facilities_공공체육시설_{k}.parquet', index=False); d.to_csv(L.V2 / f'facilities_공공체육시설_{k}.csv', index=False, encoding='utf-8-sig')
    c = d[d.scope_flag == '핵심종목']; allc = c.inside_seoul == True; st = c.coord_valid_v2
    before = c.coord_method.isin(STRICT[:4]) & (c.inside_seoul == True)
    rg = st.groupby(c.gu_seoul).mean() * 100; ra = allc.groupby(c.gu_seoul).mean() * 100
    for g in L.GU:
        m = c.gu_seoul == g
        gurows.append(dict(snapshot=k, gu=g, n_core=int(m.sum()), n_strict=int(st[m].sum()), rate_strict_v2=round(rg.get(g, np.nan), 1),
                           n_keyword_unverified=int((c[m].coord_method == 'kakao_place_name_gu').sum()), n_unresolved=int((c[m].coord_method == 'unresolved').sum()),
                           rate_incl_unverified_keyword=round(ra.get(g, np.nan), 1), below85_strict=bool(rg.get(g, 0) < 85)))
    summ[k] = dict(n_core=len(c), strict_before=round(before.mean() * 100, 1), strict_after=round(st.mean() * 100, 1),
                   incl_keyword_after=round(allc.mean() * 100, 1), filled=int(changed.sum()), n_gu_below85=int((rg < 85).sum()),
                   n_gu_below85_incl_keyword=int((ra < 85).sum()), min_gu=rg.idxmin(), min_gu_rate=round(rg.min(), 1),
                   min_gu_incl_keyword=ra.idxmin(), min_gu_rate_incl_keyword=round(ra.min(), 1),
                   n_unresolved=int((c.coord_method == 'unresolved').sum()), n_keyword_unverified=int((c.coord_method == 'kakao_place_name_gu').sum()),
                   judgment_S=('상' if st.mean() >= .95 and (rg >= 85).all() else '중'))
pd.DataFrame(log).to_csv(L.V2 / 'fill_log_공공체육시설.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(gurows).to_csv(L.V2 / 'coord_by_gu_공공체육시설_v2.csv', index=False, encoding='utf-8-sig')
json.dump(dict(accuracy=acc, coverage=summ), open(L.V2 / 'summary_v2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1)); lg = pd.DataFrame(log)
print(lg.groupby(['snapshot', 'scope_flag', 'coord_method_before', 'time_rule', 'result']).size())
print(pd.DataFrame(gurows).to_string())
