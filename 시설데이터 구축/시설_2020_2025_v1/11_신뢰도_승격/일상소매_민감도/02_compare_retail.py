# -*- coding: utf-8 -*-
"""일상소매 두 버전(상가업소 vs 인허가 식료품소매[+대형마트·SSM]) 민감도 비교.
출력: work/*.csv, compare_summary_retail.json"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cmp_lib import *

OUT = HERE
g, dt = prep_geo()
F = {
 'S':  lambda y: load(V1 / f'03_교육교통공원상가/retail_daily/facilities_retail_daily_{y}_01.parquet'),
 'L':  lambda y: load(V1 / f'01_인허가/식료품소매/facilities_식료품소매_{y}_01.parquet'),
 'M':  lambda y: load(V1 / f'01_인허가/대규모점포/facilities_대규모점포_{y}_01.parquet',
                      lambda d: (d.attr_business_type == '대형마트') | (d.facility_subtype == '준대규모점포')),
}
D = {}
for y in ['2020', '2025']:
    S, L, M = F['S'](y), F['L'](y), F['M'](y)
    D[('S', y)] = S
    D[('S_bulk', y)] = S[~S.flag_nonbulk_id.astype(bool)] if y == '2020' else S   # 2020 비일괄번호 제외
    D[('S_core', y)] = S[S.facility_subtype.str[:6].isin(['G20404', 'G20405'])]    # 슈퍼+편의점
    D[('S_fresh', y)] = S[~S.facility_subtype.str[:6].isin(['G20404', 'G20405'])]  # 신선·식료품 7종
    D[('S_meat', y)] = S[S.facility_subtype.str[:6] == 'G20503']
    D[('L', y)] = L
    D[('LM', y)] = pd.concat([L, M])
    D[('L_meat', y)] = L[L.facility_subtype == '축산판매업']
    D[('M', y)] = M
    D[('S+LM', y)] = pd.concat([S, L, M])

raw_rows = {f'{k}_{y}': len(v) for (k, y), v in D.items()}
cnt_all = {}
for y in ['2020','2025']:
    for nm, fn in [('S', 'F["S"]'), ('L', 'F["L"]')]:
        pass

def dong_counts(k, y):
    return dt.adm_dong_cd.map(D[(k, y)].adm_dong_cd.value_counts()).fillna(0).to_numpy()

def grid_counts(k, y):
    return g.grid100_cd.map(D[(k, y)].grid100_cd.value_counts()).fillna(0).to_numpy()

PAIRS = [('S', 'L'), ('S', 'LM'), ('S_bulk', 'L'), ('S_core', 'L'), ('S_fresh', 'L'), ('S_meat', 'L_meat'), ('S', 'S+LM')]
R = {}
RADII = [500, 800]
covc = {}
for k in set([a for p in PAIRS for a in p]):
    for y in ['2020', '2025']:
        for r in RADII:
            covc[(k, y, r)] = covered(g, D[(k, y)].grid100_cd.dropna().unique(), r)

dong_rows = dt.copy()
for (k, y) in D:
    if k in set([a for p in PAIRS for a in p]):
        dong_rows[f'n_{k}_{y}'] = dong_counts(k, y)
# 동별 커버리지(인구가중)
for k in set([a for p in PAIRS for a in p]):
    for y in ['2020', '2025']:
        for r in RADII:
            pp = g[f'pop{y}'].to_numpy()
            num = pd.Series(pp * covc[(k, y, r)]).groupby(g.adm_dong_cd.to_numpy()).sum()
            den = pd.Series(pp).groupby(g.adm_dong_cd.to_numpy()).sum()
            dong_rows[f'cov{r}_{k}_{y}'] = dong_rows.adm_dong_cd.map(num / den.replace(0, np.nan))

def sign(v, tol):
    return np.where(v > tol, 1, np.where(v < -tol, -1, 0))

for a, b in PAIRS:
    key = f'{a}_vs_{b}'; R[key] = {}
    for y in ['2020', '2025']:
        pop = dt[f'pop{y}'].to_numpy()
        na, nb = dong_counts(a, y), dong_counts(b, y)
        da, db = na / pop * 1e4, nb / pop * 1e4
        ga, gb = grid_counts(a, y), grid_counts(b, y)
        gm = g[f'pop{y}'].to_numpy() > 0; gp = g[f'pop{y}'].to_numpy()
        rr = dict(total_a=int(len(D[(a, y)])), total_b=int(len(D[(b, y)])),
                  dong_pearson_n=round(pearson(na, nb), 3), dong_spearman_n=round(spearman(na, nb), 3),
                  dong_spearman_per10k=round(spearman(da, db), 3),
                  dong_zero_a=int((na == 0).sum()), dong_zero_b=int((nb == 0).sum()),
                  dong_lowQ_density=kappa(quintile_low(da), quintile_low(db)),
                  grid_spearman_n_popcells=round(spearman(ga[gm], gb[gm]), 3),
                  grid_presence_cell=kappa(ga[gm] > 0, gb[gm] > 0),
                  grid_presence_cell_popw=kappa(ga[gm] > 0, gb[gm] > 0, gp[gm]))
        for cs in [5, 10]:   # 500m, 1km 셀(SGIS 격자 정렬)
            ka = set(zip(g.gi[gm][ga[gm] > 0] // cs, g.gj[gm][ga[gm] > 0] // cs)); kb = set(zip(g.gi[gm][gb[gm] > 0] // cs, g.gj[gm][gb[gm] > 0] // cs))
            allc = sorted(set(zip(g.gi[gm] // cs, g.gj[gm] // cs)))
            rr[f'presence_cell{cs*100}m'] = kappa([c in ka for c in allc], [c in kb for c in allc])
            rr[f'presence_cell{cs*100}m']['n_cells'] = len(allc)
        for r in RADII:
            ca, cb = covc[(a, y, r)][gm], covc[(b, y, r)][gm]
            dca, dcb = dong_rows[f'cov{r}_{a}_{y}'].to_numpy(), dong_rows[f'cov{r}_{b}_{y}'].to_numpy()
            rr[f'cov{r}_popw'] = kappa(ca, cb, gp[gm])
            rr[f'cov{r}_uncovered_pop_a'] = int(gp[gm][~ca].sum()); rr[f'cov{r}_uncovered_pop_b'] = int(gp[gm][~cb].sum())
            rr[f'cov{r}_seoul_a'] = round(float((gp[gm] * ca).sum() / gp[gm].sum()), 4)
            rr[f'cov{r}_seoul_b'] = round(float((gp[gm] * cb).sum() / gp[gm].sum()), 4)
            rr[f'cov{r}_dong_pearson'] = round(pearson(dca, dcb), 3)
            rr[f'cov{r}_dong_spearman'] = round(spearman(dca, dcb), 3)
            rr[f'cov{r}_dong_lowQ'] = kappa(quintile_low(np.nan_to_num(dca, nan=1)), quintile_low(np.nan_to_num(dcb, nan=1)))
            rr[f'cov{r}_dong_lt90_a'] = int((dca < 0.9).sum()); rr[f'cov{r}_dong_lt90_b'] = int((dcb < 0.9).sum())
        R[key][y] = rr
    # 변화 방향
    na0, na1, nb0, nb1 = dong_counts(a, '2020'), dong_counts(a, '2025'), dong_counts(b, '2020'), dong_counts(b, '2025')
    dA, dB = na1 - na0, nb1 - nb0
    ch = {}
    for tol in [0, 2]:
        sA, sB = sign(dA, tol), sign(dB, tol)
        ch[f'sign_agree_tol{tol}'] = round(float((sA == sB).mean()), 3)
        m = (sA != 0) & (sB != 0)
        ch[f'sign_agree_both_nonzero_tol{tol}'] = round(float((sA[m] == sB[m]).mean()), 3) if m.any() else None
        ch[f'n_nonzero_tol{tol}'] = int(m.sum())
    ch['delta_pearson'] = round(pearson(dA, dB), 3); ch['delta_spearman'] = round(spearman(dA, dB), 3)
    pa = np.log((na1 + 1) / (na0 + 1)); pb = np.log((nb1 + 1) / (nb0 + 1))
    ch['dlog_spearman'] = round(spearman(pa, pb), 3)
    ch['seoul_change_a_pct'] = round((na1.sum() / na0.sum() - 1) * 100, 1); ch['seoul_change_b_pct'] = round((nb1.sum() / nb0.sum() - 1) * 100, 1)
    for r in RADII:
        ca = dong_rows[f'cov{r}_{a}_2025'] - dong_rows[f'cov{r}_{a}_2020']
        cb = dong_rows[f'cov{r}_{b}_2025'] - dong_rows[f'cov{r}_{b}_2020']
        sA, sB = sign(ca.to_numpy(), 0.01), sign(cb.to_numpy(), 0.01)
        ch[f'cov{r}_change_sign_agree_tol1pp'] = round(float((sA == sB).mean()), 3)
        ch[f'cov{r}_change_spearman'] = round(spearman(ca, cb), 3)
        ch[f'cov{r}_change_dist_a'] = {'up': int((sA == 1).sum()), 'flat': int((sA == 0).sum()), 'down': int((sA == -1).sum())}
        ch[f'cov{r}_change_dist_b'] = {'up': int((sB == 1).sum()), 'flat': int((sB == 0).sum()), 'down': int((sB == -1).sum())}
    R[key]['change'] = ch

# ---------- 재작성 의심 정량화 ----------
S20, S25 = D[('S', '2020')], D[('S', '2025')]
ym = S20.id_issue_ym.astype(str)
rw = dict(rows=len(S20), id_issued_2025plus=int((ym >= '202501').sum()), id_issued_after_202412=int((ym > '202412').sum()),
          nonbulk=int(S20.flag_nonbulk_id.sum()), nonbulk_pct=round(S20.flag_nonbulk_id.mean() * 100, 2),
          id_issued_2025plus_pct=round((ym >= '202501').mean() * 100, 2),
          id_2023_2024_nonbulk=int(((ym >= '202301') & (ym <= '202412') & S20.flag_nonbulk_id.astype(bool)).sum()),
          ids_also_in_202412=int(S20.facility_id.isin(S25.facility_id).sum()))
rw['ids_also_in_202412_pct'] = round(rw['ids_also_in_202412'] / len(S20) * 100, 1)
# 2025 발급 번호가 2019판에 있다 = 2024-12 이후 조사된 업소를 과거판에 넣음
f25 = S20[ym >= '202501']
rw['id2025_by_subtype'] = f25.facility_subtype.value_counts().to_dict()
rw['id2025_by_gu'] = f25.gu_name.value_counts().to_dict()
# 비일괄 번호의 구별 편중
t = S20.groupby('gu_name').agg(n=('facility_id', 'size'), nb=('flag_nonbulk_id', 'sum'))
t['nb_pct'] = (t.nb / t.n * 100).round(2)
rw['nonbulk_by_gu_pct'] = t.nb_pct.sort_values(ascending=False).to_dict()
rw['nonbulk_gu_dissimilarity'] = round(0.5 * float(np.abs(t.nb / t.nb.sum() - t.n / t.n.sum()).sum()), 3)
rw['nonbulk_gu_pct_range'] = [float(t.nb_pct.min()), float(t.nb_pct.max())]
t.to_csv(OUT / 'work' / 'nonbulk_by_gu.csv', encoding='utf-8-sig')
# 동 단위 불일치의 공간 집중: 2020과 2025의 log 비(S/L) 비교
for k in ['S', 'L', 'S_meat', 'L_meat']:
    for y in ['2020', '2025']:
        dong_rows[f'n_{k}_{y}'] = dong_counts(k, y)
lr = {}
for a, b in [('S', 'L'), ('S_meat', 'L_meat')]:
    r20 = np.log((dong_rows[f'n_{a}_2020'] + 1) / (dong_rows[f'n_{b}_2020'] + 1))
    r25 = np.log((dong_rows[f'n_{a}_2025'] + 1) / (dong_rows[f'n_{b}_2025'] + 1))
    dd = r20 - r25   # >0 : 2020에 상가가 인허가보다 상대적으로 많음(2025 대비)
    dong_rows[f'dlr_{a}_{b}'] = dd
    lr[f'{a}_{b}'] = dict(logratio_corr_2020_2025=round(pearson(r20, r25), 3),
                         dlr_mean=round(float(dd.mean()), 3), dlr_sd=round(float(dd.std()), 3),
                         seoul_logratio_2020=round(float(np.log(dong_rows[f'n_{a}_2020'].sum() / dong_rows[f'n_{b}_2020'].sum())), 3),
                         seoul_logratio_2025=round(float(np.log(dong_rows[f'n_{a}_2025'].sum() / dong_rows[f'n_{b}_2025'].sum())), 3),
                         gu_mean_dlr=dong_rows.groupby('gu_name')[f'dlr_{a}_{b}'].mean().round(3).sort_values().to_dict())
    # 구 간 분산 비율(eta^2)
    gm_ = dong_rows.groupby('gu_name')[f'dlr_{a}_{b}'].transform('mean')
    lr[f'{a}_{b}']['eta2_gu'] = round(float(((gm_ - dd.mean()) ** 2).sum() / ((dd - dd.mean()) ** 2).sum()), 3)
rw['dong_logratio'] = lr
# Moran's I (queen) for dlr
try:
    import geopandas as gpd
    dg = gpd.read_file(SGIS / '03_행정구역' / '경계_2025_2Q' / 'bnd_dong_00_2025_2Q' / 'bnd_dong_00_2025_2Q.shp')
    dg = dg[dg['ADM_CD'].astype(str).str.startswith('11')].to_crs(5179)
    dg['adm_dong_cd'] = dg.ADM_CD.astype(str)
    dg = dg.set_index('adm_dong_cd').loc[dong_rows.adm_dong_cd]
    geoms = list(dg.geometry.buffer(1))
    from shapely.strtree import STRtree
    tr = STRtree(geoms); n = len(geoms); W = np.zeros((n, n))
    for i, gg in enumerate(geoms):
        for j in tr.query(gg, predicate='intersects'):
            if j != i: W[i, j] = 1
    W = W / W.sum(1, keepdims=True).clip(1)
    np.save(OUT / 'work' / 'W_queen_row.npy', W)
    rng = np.random.default_rng(1)
    def moran(x):
        z = x - x.mean(); return float(n / W.sum() * (z @ W @ z) / (z @ z))
    mi = {}
    for c in ['dlr_S_L', 'dlr_S_meat_L_meat']:
        x = dong_rows[c].to_numpy(float); I = moran(x)
        perm = np.array([moran(rng.permutation(x)) for _ in range(499)])
        mi[c] = dict(I=round(I, 3), p_perm=round(float((np.sum(perm >= I) + 1) / 500), 3), E=round(-1 / (n - 1), 4))
    rw['moran_dlr'] = mi
except Exception as e:
    rw['moran_dlr'] = f'error {e}'

# ---------- 국세청(구 단위) 제3원천 대조 ----------
def nts_read(p, col):
    t = pd.read_csv(p, encoding='cp949', dtype=str)
    t.columns = [c.strip() for c in t.columns]
    t['v'] = pd.to_numeric(t[col].str.strip(), errors='coerce')
    return t
RAWR = V1 / '03_교육교통공원상가/retail_daily/raw'
n20 = nts_read(RAWR / 'nts_100대생활업종_202101.csv', '전년동월'); n25 = nts_read(RAWR / 'nts_100대생활업종_202412.csv', '당월')
def nts_gu(t, items):
    t = t[t['시도'].str.strip() == '서울특별시']
    x = t[t['업종'].str.strip().isin(items)].groupby(t['시군구'].str.strip())['v'].sum()
    return x
gus = sorted(dt.gu_name.unique())
NTSMAP = {'S': ['편의점', '슈퍼마켓', '정육점', '채소가게', '과일가게', '생선가게', '식료품가게', '건어물가게', '곡물가게'],
          'S_core': ['편의점', '슈퍼마켓'], 'S_meat': ['정육점'], 'L_meat': ['정육점'],
          'L': ['정육점', '식료품가게', '제과점'], 'L_bak': ['제과점']}
D[('L_bak', '2020')] = D[('L', '2020')][D[('L', '2020')].facility_subtype == '제과점영업']
D[('L_bak', '2025')] = D[('L', '2025')][D[('L', '2025')].facility_subtype == '제과점영업']
ntsr = {}
gu_tab = pd.DataFrame(index=gus)
for k, items in NTSMAP.items():
    a0 = D[(k, '2020')].groupby(D[(k, '2020')].adm_dong_cd.str[:5]).size()
    a1 = D[(k, '2025')].groupby(D[(k, '2025')].adm_dong_cd.str[:5]).size()
    gmap = dict(zip(dt.gu_cd, dt.gu_name))
    a0.index = a0.index.map(gmap); a1.index = a1.index.map(gmap)
    a0, a1 = a0.reindex(gus).fillna(0), a1.reindex(gus).fillna(0)
    b0, b1 = nts_gu(n20, items).reindex(gus), nts_gu(n25, items).reindex(gus)
    gu_tab[f'{k}_2020'] = a0; gu_tab[f'{k}_2025'] = a1; gu_tab[f'NTS[{k}]_2020'] = b0; gu_tab[f'NTS[{k}]_2025'] = b1
    ntsr[k] = dict(items=items, sum_fac_2020=int(a0.sum()), sum_nts_2020=int(b0.sum()), sum_fac_2025=int(a1.sum()), sum_nts_2025=int(b1.sum()),
                   ratio_2020=round(a0.sum() / b0.sum(), 3), ratio_2025=round(a1.sum() / b1.sum(), 3),
                   gu_pearson_2020=round(pearson(a0, b0), 3), gu_pearson_2025=round(pearson(a1, b1), 3),
                   gu_spearman_2020=round(spearman(a0, b0), 3), gu_spearman_2025=round(spearman(a1, b1), 3),
                   change_fac_pct=round((a1.sum() / a0.sum() - 1) * 100, 1), change_nts_pct=round((b1.sum() / b0.sum() - 1) * 100, 1),
                   gu_change_pearson=round(pearson(np.log(a1 / a0), np.log(b1 / b0)), 3),
                   gu_change_spearman=round(spearman(a1 / a0, b1 / b0), 3),
                   gu_change_sign_agree=round(float((np.sign(a1 - a0) == np.sign(b1 - b0)).mean()), 3))
gu_tab.to_csv(OUT / 'work' / 'gu_vs_nts.csv', encoding='utf-8-sig')

dong_rows.to_csv(OUT / 'work' / 'dong_compare_retail.csv', index=False, encoding='utf-8-sig')
res = dict(rows=raw_rows, pairs=R, rewrite=rw, nts_gu=ntsr,
           subtype={f'{k}_{y}': D[(k, y)].facility_subtype.value_counts().to_dict() for k in ['S', 'L', 'M'] for y in ['2020', '2025']},
           notes=['반경 내 존재는 100m 격자 중심 간 유클리드 거리 근사(500m≈도보 10분·우회계수 1.3·4km/h, 800m 상한)',
                  '인구격자 = SGIS 2019/2024 총인구, 중심점이 2025_2Q 동 안인 32,146개 셀; 각 연도 인구>0 셀만 사용'])
json.dump(res, open(OUT / 'compare_summary_retail.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('ok')
