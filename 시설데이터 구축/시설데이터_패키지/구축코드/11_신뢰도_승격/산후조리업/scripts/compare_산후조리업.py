# -*- coding: utf-8 -*-
"""산후조리업 역산 vs 서울시 시정통계 '산후조리원 현황'(DT_201004_B040007, 휴업·폐업 제외, 연말) 2019·2024."""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import cmp_lib as C
OUT = Path(__file__).resolve().parents[1]
off = pd.read_csv(OUT / 'raw/eseoul_DT_201004_B040007_산후조리원현황_구별_2018_2025.csv')
rows, summ = [], {}
for y, yr in (('2020', 2019), ('2025', 2024)):
    d = C.load('산후조리업', y); o = off[off.year == yr].set_index('gu')['산후조리원수']
    tot = int(o['서울합계']); st, g = C.gu_compare(d.gu, o.drop('서울합계'))
    # 민감도: 현재 상태 '휴업'(시점 휴업 여부 불명) 제외
    n_excl_susp = int((d.src_status != '휴업').sum())
    summ[y] = dict(ours=len(d), official=tot, diff=len(d) - tot, diff_pct=C.pct(len(d), tot), gu=st, cov=C.coverage(d),
                   sens_excl_current_suspended=dict(n=n_excl_susp, diff_pct=C.pct(n_excl_susp, tot)))
    rows.append(dict(level='서울', snapshot=f'{y}_01', official_year=yr, gu='서울합계', ours=len(d), official=tot, diff=len(d) - tot, diff_pct=C.pct(len(d), tot)))
    for gu, r in g.iterrows():
        rows.append(dict(level='구', snapshot=f'{y}_01', official_year=yr, gu=gu, ours=int(r.ours), official=int(r.official), diff=int(r['diff']), diff_pct=r.diff_pct))
pd.DataFrame(rows).assign(source='서울특별시 시정통계 산후조리원 현황(stat.eseoul.go.kr DT_201004_B040007; 휴업·폐업 제외)').to_csv(OUT / 'official_compare_산후조리업.csv', index=False, encoding='utf-8-sig')
(OUT / 'summary_산후조리업.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps(summ, ensure_ascii=False, default=str))
df = pd.DataFrame(rows); print(df[(df.level == '구') & (df['diff'].abs() >= 2)])
