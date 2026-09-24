"""구축(역산) vs 공식 통계(서울시 기본통계, KOSIS orgId=201) 서울 합계·25개 자치구 비교 + 자치구별 좌표율.
사용: python compare.py <시설>   → ../<시설>/official_compare_<시설>.csv, compare_summary_<시설>.json, coord_by_gu_<시설>.csv
구축 파일: ../<시설>/facilities_*.parquet 가 있으면 그것(좌표 보완본), 없으면 01_인허가 원 빌드."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists()); R = V1 / '11_신뢰도_승격'
sys.path.insert(0, str(HERE)); from gu import add_gu, GU
FAC = sys.argv[1]
FOOD = R / FAC / 'raw/kosis_DT_201004_O110008_식품위생업현황_구별_2019_2024.csv'
PUB = R / FAC / 'raw/kosis_DT_201004_O110009_2015_공중위생업현황_구별_2019_2024.csv'
RET = R / FAC / 'raw/kosis_DT_201004_O080001_유통업체현황_구별_2019_2024.csv'
ALL = lambda d: pd.Series(True, index=d.index)
ST = lambda *s: (lambda d: d.facility_subtype.isin(s))
BT = lambda *s: (lambda d: (d.facility_subtype == '대규모점포') & d.attr_business_type.isin(s))
# scope 이름: (구축 필터, 공식 파일, 공식 열[합산])
CFG = {
 '일반음식점': {'전체': (ALL, FOOD, ['일반음식점'])},
 '휴게음식점': {'전체': (ALL, FOOD, ['휴게음식점'])},
 '식료품소매': {'즉석판매제조가공업': (ST('즉석판매제조가공업'), FOOD, ['즉석판매제조가공업']),
               '제과점영업': (ST('제과점영업'), FOOD, ['제과점']),
               '즉석판매+제과점(범위제한)': (ST('즉석판매제조가공업', '제과점영업'), FOOD, ['즉석판매제조가공업', '제과점'])},
 '미용업': {'전체': (ALL, PUB, ['미용업'])},
 '이용업': {'전체': (ALL, PUB, ['이용업'])},
 '세탁업': {'전체': (ALL, PUB, ['세탁업'])},
 '목욕장업': {'전체': (ALL, PUB, ['목욕장업'])},
 '대규모점포': {'점포구분=대규모점포': (ST('대규모점포'), RET, ['합계']),
               '점포구분=대규모점포+점포구분미상': (ST('대규모점포', '점포구분미상'), RET, ['합계']),
               '대형마트': (BT('대형마트'), RET, ['대형마트']), '백화점': (BT('백화점'), RET, ['백화점']),
               '쇼핑센터': (BT('쇼핑센터'), RET, ['쇼핑센터']), '전문점': (BT('전문점'), RET, ['전문점']),
               '복합쇼핑몰': (BT('복합쇼핑몰'), RET, ['복합쇼핑몰']),
               '주요4업태(대형마트·백화점·쇼핑센터·전문점, 범위제한)': (BT('대형마트', '백화점', '쇼핑센터', '전문점'), RET, ['대형마트', '백화점', '쇼핑센터', '전문점']),
               '그밖의(시장·구분없음 포함)': (BT('그 밖의 대규모점포', '시장', '구분없음'), RET, ['그밖의대규모점포'])},
}
FAC = sys.argv[1]; OUT = R / FAC; OUT.mkdir(exist_ok=True)
def load(k):
    p = OUT / f'facilities_{FAC}_{k}.parquet'
    d = pd.read_parquet(p if p.exists() else V1 / '01_인허가' / FAC / f'facilities_{FAC}_{k}.parquet')
    return d if 'gu' in d else add_gu(d)
D = {'2019': load('2020_01'), '2024': load('2025_01')}
rows, summ = [], {'facility': FAC, 'scopes': {}}
for sc, (flt, ofile, ocols) in CFG.get(FAC, {}).items():
    off = pd.read_csv(ofile); summ['official_file'] = ofile.name
    for y, d in D.items():
        s = d[flt(d)]
        b = s.gu.value_counts().reindex(GU, fill_value=0)
        o = off[off.year == int(y)].set_index('gu')[ocols].sum(axis=1)
        tot_b, tot_o = int(len(s)), int(o['서울합계'])
        og = o.reindex(GU)
        for g in GU:
            rows.append({'scope': sc, 'year_official': y, 'snapshot': '2020_01' if y == '2019' else '2025_01', 'gu': g, 'built': int(b[g]),
                         'official': int(og[g]), 'diff': int(b[g] - og[g]), 'diff_pct': round(100 * (b[g] - og[g]) / og[g], 2) if og[g] else None})
        rows.append({'scope': sc, 'year_official': y, 'snapshot': '2020_01' if y == '2019' else '2025_01', 'gu': '서울합계', 'built': tot_b,
                     'official': tot_o, 'diff': tot_b - tot_o, 'diff_pct': round(100 * (tot_b - tot_o) / tot_o, 2) if tot_o else None})
        pct = 100 * (b - og) / og.replace(0, np.nan)
        summ['scopes'].setdefault(sc, {})[y] = {
            'built': tot_b, 'official': tot_o, 'diff_pct': round(100 * (tot_b - tot_o) / tot_o, 2) if tot_o else None,
            'unassigned_gu_rows': int(s.gu.isna().sum()),
            'gu_pearson_r': round(float(np.corrcoef(b.values, og.values)[0, 1]), 4) if og.std() > 0 else None,
            'gu_max_abs_diff_pct': round(float(pct.abs().max()), 2) if pct.notna().any() else None,
            'gu_max_abs_diff_gu': pct.abs().idxmax() if pct.notna().any() else None,
            'gu_median_abs_diff_pct': round(float(pct.abs().median()), 2) if pct.notna().any() else None,
            'gu_n_within_5pct': int((pct.abs() <= 5).sum()), 'gu_n_within_10pct': int((pct.abs() <= 10).sum())}
        okc = (s.coord_method != 'unresolved') & (s.inside_seoul == True)
        gg = pd.DataFrame({'gu': s.gu, 'ok': okc}).groupby('gu').ok.mean()
        summ['scopes'][sc][y].update({'scope_coord_rate': round(float(okc.mean()), 4) if len(s) else None,
            'scope_min_gu_coord_rate': round(float(gg.min()), 4) if len(gg) else None, 'scope_n_gu_below_85': int((gg < 0.85).sum())})
pd.DataFrame(rows).to_csv(OUT / f'official_compare_{FAC}.csv', index=False, encoding='utf-8-sig')
# 자치구별 좌표율 (서울 안 좌표 보유율)
cr = []
for y, d in D.items():
    ok = (d.coord_method != 'unresolved') & (d.inside_seoul == True)
    g = pd.DataFrame({'gu': d.gu, 'ok': ok}).groupby('gu').ok.agg(['size', 'mean'])
    for gg, r in g.iterrows():
        cr.append({'snapshot': '2020_01' if y == '2019' else '2025_01', 'gu': gg, 'n': int(r['size']), 'coord_rate': round(float(r['mean']), 4)})
    summ.setdefault('coord', {})[y] = {'n': int(len(d)), 'coord_rate_inside_seoul': round(float(ok.mean()), 4),
        'min_gu_coord_rate': round(float(g['mean'].min()), 4), 'min_gu': g['mean'].idxmin(), 'n_gu_below_85': int((g['mean'] < 0.85).sum()),
        'n_gu_below_95': int((g['mean'] < 0.95).sum()),
        'coord_stage': d.coord_stage.value_counts().to_dict() if 'coord_stage' in d else d.coord_method.value_counts().to_dict()}
pd.DataFrame(cr).to_csv(OUT / f'coord_by_gu_{FAC}.csv', index=False, encoding='utf-8-sig')
(OUT / f'compare_summary_{FAC}.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(summ, ensure_ascii=False))
