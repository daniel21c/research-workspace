# -*- coding: utf-8 -*-
"""어린이집: 공식 보육통계(12.31) 대조 + 민감도(D 이후 3개월 내 폐지 제외) + 미해결 좌표 보완.
원본(03_교육교통공원상가/childcare)은 읽기만. 출력은 이 폴더."""
import sys, json
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11, geo11
import pandas as pd, numpy as np
V1 = u11.V1; GU = u11.GU
SRC = V1 / '03_교육교통공원상가' / 'childcare'
T = ['국공립', '사회복지법인', '법인·단체등', '민간', '가정', '협동', '직장']
o = pd.read_csv(FD / 'raw' / 'official_보육통계_서울_구유형_2019_2024.csv')
rows = []; summ = {}
for snap, y, D in [('2020_01', 2019, '2019-12-31'), ('2025_01', 2024, '2024-12-31')]:
    d = pd.read_parquet(SRC / f'facilities_childcare_{snap}.parquet')
    before = float(d.x_5179.notna().mean())
    # 좌표 보완
    d = geo11.fill(d, FD / 'raw' / 'geocoding', gu_col='gu_name')
    d = geo11.respatial(d, lib='fac')
    d['scope_flag'] = 'all'
    cl = pd.to_datetime(d.close_date, errors='coerce'); Dt = pd.Timestamp(D)
    d['sens_closed_within_3m'] = (cl > Dt) & (cl <= Dt + pd.DateOffset(months=3))
    ob = o[o.year == y].set_index('gu')
    # 합계·유형
    for key, sel in [('계', slice(None))] + [(t, t) for t in T]:
        x = d if key == '계' else d[d.facility_subtype == key]
        b = len(x); bs = int((~x.sens_closed_within_3m).sum()); off = int(ob.loc['서울합계', key])
        rows.append(dict(year=y, ref_date=D, level='서울_유형' if key != '계' else '서울_합계', key=key, built=b, official=off,
                         diff=b - off, diff_pct=round((b - off) / off * 100, 2) if off else None,
                         built_sens_excl_closed3m=bs, diff_pct_sens=round((bs - off) / off * 100, 2) if off else None))
    bg = d.groupby('gu_name').size(); bgs = d[~d.sens_closed_within_3m].groupby('gu_name').size()
    t, st = u11.compare(bg, ob.loc[GU, '계'], label=snap)
    ts, sts = u11.compare(bgs, ob.loc[GU, '계'], label=snap + '_sens')
    for g in GU:
        rows.append(dict(year=y, ref_date=D, level='구', key=g, built=int(t.loc[g, 'built']), official=int(t.loc[g, 'official']),
                         diff=int(t.loc[g, 'diff']), diff_pct=t.loc[g, 'diff_pct'], built_sens_excl_closed3m=int(ts.loc[g, 'built']),
                         diff_pct_sens=ts.loc[g, 'diff_pct']))
    cov = geo11.coord_rate_by_gu(d, 'gu_name')
    cov.to_csv(FD / f'coord_by_gu_어린이집_{snap}.csv', encoding='utf-8-sig')
    summ[snap] = dict(gu_compare=st, gu_compare_sens=sts, coord_rate_before=round(before, 4),
                      coord_rate_after=round(float(d.x_5179.notna().mean()), 4), min_gu_rate=float(cov.rate.min()),
                      min_gu=str(cov.rate.idxmin()), filled=int((d.coord_stage == 'filled_11').sum()),
                      still_missing=int(d.x_5179.isna().sum()), sens_excluded=int(d.sens_closed_within_3m.sum()),
                      outside_seoul=int((d.inside_seoul.astype(str) == 'False').sum()))
    d.drop(columns=['sens_closed_within_3m']).pipe(lambda z: u11.fac.write_out(z, FD, '어린이집', snap))
    d[d.coord_stage == 'filled_11'][['facility_id', 'name', 'address', 'coord_method', 'geocode_detail2']].to_csv(
        FD / f'filled_coords_어린이집_{snap}.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(rows).to_csv(FD / 'official_compare_어린이집.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(FD / 'summary_어린이집.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
print(pd.DataFrame(rows).query("level!='구'").to_string())
