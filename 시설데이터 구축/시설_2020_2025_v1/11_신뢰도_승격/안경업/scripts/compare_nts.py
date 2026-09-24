# -*- coding: utf-8 -*-
"""동물병원·안경업 역산 vs 국세청 100대 생활업종 가동사업자 수(data.go.kr 15061118, 시군구별).
2020_01 ↔ 20210131판 '전년동월'(=2020-01 말), 2025_01 ↔ 20241231판 '당월'(=2024-12 말).
정의 차이: 국세청=사업자등록 기준 주업종(동물병원/안경점) 가동사업자, 인허가=개설신고·등록 기준. '*'=비공개(소수) 셀."""
import json, sys, warnings
warnings.filterwarnings('ignore')
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import cmp_lib as C
fac, nts_kind = sys.argv[1], sys.argv[2]            # 예: 동물병원 동물병원 / 안경업 안경점
OUT = Path(__file__).resolve().parents[2] / fac
def nts(tag, col):
    d = pd.read_csv(OUT / f'raw/datagokr_15061118_국세청_100대생활업종_사업자현황_{tag}.csv', encoding='cp949', dtype=str)
    for c in d.columns: d[c] = d[c].str.strip()
    s = d[(d['시도'] == '서울특별시') & (d['업종'] == nts_kind)].set_index('시군구')[col]
    star = int((s == '*').sum())
    return pd.to_numeric(s.str.replace(',', ''), errors='coerce'), star
rows, summ = [], {}
for y, tag, col, ref in (('2020', '20210131', '전년동월', '2020-01-31'), ('2025', '20241231', '당월', '2024-12-31')):
    loc = OUT / f'facilities_{fac}_{y}_01.parquet'   # 11_신뢰도_승격에서 좌표 보완한 판이 있으면 사용
    d = C.add_gu(pd.read_parquet(loc)) if loc.exists() else C.load(fac, y)
    cov_orig = C.coverage(C.load(fac, y)); o, star = nts(tag, col); tot = int(o.sum())
    st, g = C.gu_compare(d.gu, o)
    act = d[d.src_status.isin(['영업/정상'])] if y == '2025' else None
    summ[y] = dict(ours=len(d), nts=tot, nts_suppressed_cells=star, diff=len(d) - tot, diff_pct=C.pct(len(d), tot), ratio=round(len(d) / tot, 4),
                   gu=st, cov=C.coverage(d), cov_original_build=cov_orig, used_file=str(loc.name if loc.exists() else '01_인허가 원본'), flag_admin_end=int(d.flag_admin_end.sum()),
                   sens_excl_flag_admin_end=C.pct(int((~d.flag_admin_end.astype(bool)).sum()), tot),
                   sens_excl_current_suspended=C.pct(int((d.src_status != '휴업').sum()), tot))
    rows.append(dict(level='서울', snapshot=f'{y}_01', official_date=ref, gu='서울합계', ours=len(d), official=tot, diff=len(d) - tot, diff_pct=C.pct(len(d), tot)))
    for gu, r in g.iterrows():
        rows.append(dict(level='구', snapshot=f'{y}_01', official_date=ref, gu=gu, ours=int(r.ours), official=r.official, diff=r['diff'], diff_pct=r.diff_pct))
pd.DataFrame(rows).assign(source=f'국세청 사업자현황_100대 생활업종({nts_kind}) data.go.kr 15061118 (20210131판 전년동월 / 20241231판 당월)').to_csv(
    OUT / f'official_compare_{fac}.csv', index=False, encoding='utf-8-sig')
(OUT / f'summary_{fac}.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps(summ, ensure_ascii=False, default=str))
df = pd.DataFrame(rows); print(df[df.level == '구'].pivot(index='gu', columns='snapshot', values='diff_pct').T.to_string())
