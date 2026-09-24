# -*- coding: utf-8 -*-
"""노인복지시설: 범위 제한(이용시설/입소시설/방문형 제외) + 같은 보고서 총괄표(시･군･구) 대조 + 좌표·구 점검·보완.
원본(02_명부/노인복지시설)은 읽기만."""
import sys, json
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11, geo11
import pandas as pd, numpy as np
V1 = u11.V1; GU = u11.GU
SRC = V1 / '02_명부' / '노인복지시설'
SCOPE = {'노인복지관': '이용시설', '주야간보호': '이용시설', '단기보호': '이용시설',
         '양로시설': '입소시설', '노인공동생활가정': '입소시설', '노인복지주택': '입소시설', '노인요양시설': '입소시설', '노인요양공동생활가정': '입소시설',
         '방문요양': '제외_방문형', '방문목욕': '제외_방문형', '방문간호': '제외_방문형', '복지용구지원': '제외_방문형', '재가노인지원': '제외_방문형'}
o = pd.read_csv(FD / 'raw' / 'official_노인복지시설_서울_구종류_2019_2024.csv')
o['scope_flag'] = o.facility_subtype.map(SCOPE)
dn = u11.sgis_dongs('2025_2Q'); cd2gu = dict(zip(dn.CD.astype(str).str[:5], dn.gu))
rows = []; summ = {}
for snap, y in [('2020_01', 2019), ('2025_01', 2024)]:
    d = pd.read_parquet(SRC / f'facilities_노인복지시설_{snap}.parquet')
    d['scope_flag'] = d.facility_subtype.map(SCOPE)
    assert d.scope_flag.notna().all()
    before = d.groupby('scope_flag').x_5179.apply(lambda s: round(float(s.notna().mean()), 4)).to_dict()
    tgt = d.scope_flag != '제외_방문형'
    d = geo11.fill(d, FD / 'raw' / 'geocoding', gu_col='gu', mask=tgt)
    d = geo11.respatial(d, lib='mb')
    # 구 점검: 명부 시군구 열 vs 주소 문자열 vs 좌표가 떨어진 구
    d['gu_addr'] = d.address.map(u11.gu_of)
    d['gu_point'] = d.adm_dong_cd.fillna('').astype(str).str[:5].map(cd2gu)
    # 서울 구에 등록됐지만 소재지가 서울 밖(시립 요양원 등) → 서울 내 좌표율 분모에서 제외, 플래그로 남김
    import re as _re
    d['location_outside_seoul'] = (d.inside_seoul.astype(str) == 'False') | d.address.fillna('').map(
        lambda a: bool(u11.mb.OTHER_SIDO.match(a) or _re.match(r'^서울특별시 \S+구 [가-힣]+시 [가-힣]+(구|군|읍|면) ', a)))
    ob = o[o.year == y]
    for sc in ['이용시설', '입소시설']:
        x = d[d.scope_flag == sc]
        # 종류별 서울 합계
        for t in sorted(x.facility_subtype.unique()):
            b = int((x.facility_subtype == t).sum()); off = int(ob[(ob.gu == '서울합계') & (ob.facility_subtype == t)].official.iloc[0])
            rows.append(dict(year=y, scope_flag=sc, level='서울_종류', key=t, built=b, official=off, diff=b - off,
                             diff_pct=round((b - off) / off * 100, 2) if off else None))
        offg = ob[(ob.scope_flag == sc) & (ob.gu != '서울합계')].groupby('gu').official.sum()
        t_, st = u11.compare(x.groupby('gu').size(), offg, label=f'{snap}_{sc}')
        rows.append(dict(year=y, scope_flag=sc, level='서울_합계', key='계', built=st['built_total'], official=st['official_total'],
                         diff=st['built_total'] - st['official_total'], diff_pct=st['diff_pct']))
        for g in GU:
            rows.append(dict(year=y, scope_flag=sc, level='구', key=g, built=int(t_.loc[g, 'built']), official=int(t_.loc[g, 'official']),
                             diff=int(t_.loc[g, 'diff']), diff_pct=t_.loc[g, 'diff_pct']))
        xin = x[~x.location_outside_seoul]
        cov = geo11.coord_rate_by_gu(xin, 'gu')
        cov.to_csv(FD / f'coord_by_gu_노인복지시설_{sc}_{snap}.csv', encoding='utf-8-sig')
        has = x.x_5179.notna()
        summ.setdefault(snap, {})[sc] = dict(
            gu_compare=st, coord_rate_before=before.get(sc), coord_rate_after=round(float(has.mean()), 4),
            located_outside_seoul=int(x.location_outside_seoul.sum()),
            coord_rate_after_seoul_located=round(float(xin.x_5179.notna().mean()), 4),
            min_gu_rate=float(cov.rate.min()), min_gu=str(cov.rate.idxmin()), gu_below_85=cov.index[cov.rate < 0.85].tolist(),
            filled=int((x.coord_stage == 'filled_11').sum()), still_missing=int((~has).sum()),
            outside_seoul=int((x.inside_seoul.astype(str) == 'False').sum()),
            gu_col_missing=int((x.gu.fillna('') == '').sum()), gu_col_not_seoul=int((~x.gu.isin(GU)).sum()),
            gu_col_vs_addr_mismatch=int(((x.gu_addr != '') & (x.gu_addr != x.gu)).sum()),
            gu_col_vs_point_mismatch=int((x.gu_point.notna() & (x.gu_point != x.gu)).sum()))
    d.drop(columns=['gu_addr']).pipe(lambda z: u11.mb.finalize(z, snap, FD, '노인복지시설'))
    d[d.coord_stage == 'filled_11'][['facility_id', 'facility_subtype', 'name', 'address', 'coord_method', 'geocode_detail2']].to_csv(
        FD / f'filled_coords_노인복지시설_{snap}.csv', index=False, encoding='utf-8-sig')
    d[(d.scope_flag != '제외_방문형') & d.x_5179.isna()][['facility_id', 'facility_subtype', 'gu', 'name', 'address', 'geocode_detail2']].to_csv(
        FD / f'unresolved_노인복지시설_{snap}.csv', index=False, encoding='utf-8-sig')
    mm = d[(d.scope_flag != '제외_방문형') & d.gu_point.notna() & (d.gu_point != d.gu)][['facility_id', 'facility_subtype', 'name', 'gu', 'gu_point', 'address']]
    if len(mm): print(snap, 'gu mismatch\n', mm.to_string())
pd.DataFrame(rows).to_csv(FD / 'official_compare_노인복지시설.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(FD / 'summary_노인복지시설.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
print(pd.DataFrame(rows).query("level!='구'").to_string())
