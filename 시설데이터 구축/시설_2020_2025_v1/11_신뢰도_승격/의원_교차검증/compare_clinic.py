# -*- coding: utf-8 -*-
"""의원: 인허가(주, HIRA 대조 ±1.2%) vs 상가업소 Q102(교차검증) — 행정동·격자·구 단위."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '일상소매_민감도'))
from _cmp_lib import prep_geo, load, spearman, pearson, kappa, covered, quintile_low, V1, SGIS

g, dt = prep_geo()
KIND = {'Q10210': '치과', 'Q10211': '한방'}
def sb(y):
    d = load(V1 / f'03_교육교통공원상가/clinic_sbiz/facilities_clinic_sbiz_{y}_01.parquet')
    d = d[d.facility_subtype.str[:4] == 'Q102'].copy()
    d['kind'] = d.facility_subtype.str[:6].map(KIND).fillna('의과'); return d
def lc(y):
    d = load(V1 / f'01_인허가/의원/facilities_의원_{y}_01.parquet')
    d = d[d.facility_subtype.isin(['의원', '치과의원', '한의원'])].copy()
    d['kind'] = d.facility_subtype.map({'의원': '의과', '치과의원': '치과', '한의원': '한방'}); return d
D = {}
raw = {}
for y in ['2020', '2025']:
    raw[f'sbiz_all_{y}'] = len(pd.read_parquet(V1 / f'03_교육교통공원상가/clinic_sbiz/facilities_clinic_sbiz_{y}_01.parquet'))
    raw[f'lic_all_{y}'] = len(pd.read_parquet(V1 / f'01_인허가/의원/facilities_의원_{y}_01.parquet'))
    D[('S', y)], D[('L', y)] = sb(y), lc(y)
    for k in ['의과', '치과', '한방']:
        D[(f'S_{k}', y)] = D[('S', y)][D[('S', y)].kind == k]; D[(f'L_{k}', y)] = D[('L', y)][D[('L', y)].kind == k]

def dc(k, y): return dt.adm_dong_cd.map(D[(k, y)].adm_dong_cd.value_counts()).fillna(0).to_numpy()
def gc(k, y): return g.grid100_cd.map(D[(k, y)].grid100_cd.value_counts()).fillna(0).to_numpy()
def sign(v, tol): return np.where(v > tol, 1, np.where(v < -tol, -1, 0))
R = {}
dong_out = dt.copy()
for a, b in [('S', 'L'), ('S_의과', 'L_의과'), ('S_치과', 'L_치과'), ('S_한방', 'L_한방')]:
    key = f'{a}_vs_{b}'; R[key] = {}
    for y in ['2020', '2025']:
        pop = dt[f'pop{y}'].to_numpy(); na, nb = dc(a, y), dc(b, y)
        dong_out[f'n_{a}_{y}'] = na; dong_out[f'n_{b}_{y}'] = nb
        gm = g[f'pop{y}'].to_numpy() > 0; gp = g[f'pop{y}'].to_numpy(); ga, gb = gc(a, y), gc(b, y)
        rr = dict(total_a=int(len(D[(a, y)])), total_b=int(len(D[(b, y)])), ratio_a_b=round(len(D[(a, y)]) / len(D[(b, y)]), 3),
                  dong_pearson=round(pearson(na, nb), 3), dong_spearman=round(spearman(na, nb), 3),
                  dong_spearman_per10k=round(spearman(na / pop, nb / pop), 3),
                  dong_zero_a=int((na == 0).sum()), dong_zero_b=int((nb == 0).sum()),
                  dong_zero_kappa=kappa(na == 0, nb == 0),
                  dong_abs_diff_median=float(np.median(np.abs(na - nb))), dong_ratio_p10_p90=[round(float(x), 3) for x in np.nanpercentile(na / np.where(nb == 0, np.nan, nb), [10, 50, 90])],
                  dong_lowQ_density=kappa(quintile_low(na / pop), quintile_low(nb / pop)),
                  grid_presence_popw=kappa(ga[gm] > 0, gb[gm] > 0, gp[gm]))
        gu_a = pd.Series(na).groupby(dt.gu_name.to_numpy()).sum(); gu_b = pd.Series(nb).groupby(dt.gu_name.to_numpy()).sum()
        rr['gu_pearson'] = round(pearson(gu_a, gu_b), 3); rr['gu_max_abs_pct_diff'] = round(float(((gu_a / gu_b - 1) * 100).abs().max()), 1)
        rr['gu_ratio_range'] = [round(float((gu_a / gu_b).min()), 3), round(float((gu_a / gu_b).max()), 3)]
        for r in [500, 800]:
            ca, cb = covered(g, D[(a, y)].grid100_cd.unique(), r)[gm], covered(g, D[(b, y)].grid100_cd.unique(), r)[gm]
            rr[f'cov{r}'] = kappa(ca, cb, gp[gm])
            num_a = pd.Series(gp[gm] * ca).groupby(g.adm_dong_cd.to_numpy()[gm]).sum(); num_b = pd.Series(gp[gm] * cb).groupby(g.adm_dong_cd.to_numpy()[gm]).sum()
            den = pd.Series(gp[gm]).groupby(g.adm_dong_cd.to_numpy()[gm]).sum()
            rr[f'cov{r}_dong_pearson'] = round(pearson(num_a / den, num_b / den), 3); rr[f'cov{r}_dong_spearman'] = round(spearman(num_a / den, num_b / den), 3)
            rr[f'cov{r}_dong_lt90'] = [int(((num_a / den) < .9).sum()), int(((num_b / den) < .9).sum())]
        R[key][y] = rr
    na0, na1, nb0, nb1 = dc(a, '2020'), dc(a, '2025'), dc(b, '2020'), dc(b, '2025')
    ch = dict(seoul_change_a_pct=round((na1.sum() / na0.sum() - 1) * 100, 1), seoul_change_b_pct=round((nb1.sum() / nb0.sum() - 1) * 100, 1),
              delta_pearson=round(pearson(na1 - na0, nb1 - nb0), 3), delta_spearman=round(spearman(na1 - na0, nb1 - nb0), 3))
    for tol in [0, 2]:
        sA, sB = sign(na1 - na0, tol), sign(nb1 - nb0, tol); m = (sA != 0) & (sB != 0)
        ch[f'sign_agree_tol{tol}'] = round(float((sA == sB).mean()), 3); ch[f'sign_agree_both_nonzero_tol{tol}'] = round(float((sA[m] == sB[m]).mean()), 3); ch[f'n_both_nonzero_tol{tol}'] = int(m.sum())
    R[key]['change'] = ch
# 상가 2020 재작성 플래그
S20 = D[('S', '2020')]; ym = S20.id_issue_ym.astype(str)
rw = dict(rows=len(S20), id_issued_2025plus=int((ym >= '202501').sum()), nonbulk=int(S20.flag_nonbulk_id.sum()), nonbulk_pct=round(S20.flag_nonbulk_id.mean() * 100, 2))
# 국세청 의원계열(구 단위)
RAWR = V1 / '03_교육교통공원상가/retail_daily/raw'
def nts(p, col):
    t = pd.read_csv(p, encoding='cp949', dtype=str); t.columns = [c.strip() for c in t.columns]
    t = t[t['시도'].str.strip() == '서울특별시']; t['v'] = pd.to_numeric(t[col].str.strip(), errors='coerce'); t['업종'] = t['업종'].str.replace(' ', '', regex=False).str.strip(); return t
n20, n25 = nts(RAWR / 'nts_100대생활업종_202101.csv', '전년동월'), nts(RAWR / 'nts_100대생활업종_202412.csv', '당월')
ITEMS = {'의과': ['기타일반의원', '내과ㆍ소아과의원', '산부인과의원', '성형외과의원', '신경정신과의원', '안과의원', '이비인후과의원', '일반외과의원', '피부ㆍ비뇨기과의원'],
         '치과': ['치과의원', '치과병원ㆍ의원'], '한방': ['한방병원ㆍ한의원']}
ITEMS['전체'] = sum(ITEMS.values(), [])
nt = {}
gus = sorted(dt.gu_name.unique())
gtab = pd.DataFrame(index=gus)
for k, items in ITEMS.items():
    for y, t in [('2020', n20), ('2025', n25)]:
        x = t[t['업종'].isin(items)].groupby(t['시군구'].str.strip())['v'].sum().reindex(gus)
        sk, lk = ('S', 'L') if k == '전체' else (f'S_{k}', f'L_{k}')
        gmap = dict(zip(dt.gu_cd, dt.gu_name))
        s = D[(sk, y)].adm_dong_cd.str[:5].map(gmap).value_counts().reindex(gus).fillna(0)
        l = D[(lk, y)].adm_dong_cd.str[:5].map(gmap).value_counts().reindex(gus).fillna(0)
        gtab[f'NTS_{k}_{y}'] = x; gtab[f'sbiz_{k}_{y}'] = s; gtab[f'lic_{k}_{y}'] = l
        nt[f'{k}_{y}'] = dict(nts=int(x.sum()), sbiz=int(s.sum()), lic=int(l.sum()), gu_r_sbiz_nts=round(pearson(s, x), 3), gu_r_lic_nts=round(pearson(l, x), 3), gu_r_sbiz_lic=round(pearson(s, l), 3))
gtab.to_csv(HERE / 'gu_compare_clinic.csv', encoding='utf-8-sig')
dong_out.to_csv(HERE / 'dong_compare_clinic.csv', index=False, encoding='utf-8-sig')
res = dict(raw_rows=raw, compared_rows={f'{k}_{y}': len(v) for (k, y), v in D.items()}, pairs=R, sbiz2020_rewrite=rw, nts_gu=nt,
           notes=['상가: Q102 의원(치과·한의원·방사선 포함), 병원급 Q101 제외', '인허가: 의원·치과의원·한의원(보건소·보건지소·조산원 제외)',
                  '국세청 100대 생활업종(사업자 수, 공동개원 등으로 기관 수와 다름): 의과 9업종·치과의원·한방병원ㆍ한의원(한방병원 포함)'])
json.dump(res, open(HERE / 'compare_summary_clinic.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print({k: v for k, v in nt.items()})
