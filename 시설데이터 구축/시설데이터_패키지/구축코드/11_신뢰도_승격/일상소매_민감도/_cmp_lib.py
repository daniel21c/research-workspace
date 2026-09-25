# -*- coding: utf-8 -*-
"""두 시설 버전 비교 공통 함수 (행정동·100m 격자·반경 내 존재).
scipy/sklearn 없음 → 순위상관은 평균순위 후 Pearson, kappa는 직접 계산."""
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
V1 = HERE.parents[1]                      # 시설_2020_2025_v1
SGIS = V1.parent / 'SGIS_인구경계_2019_2024'
WORK = HERE / 'work'
YEARS = {'2020': '2019', '2025': '2024'}  # 스냅샷 → 인구 통계 연도


def prep_geo(force=False):
    """행정동(2025_2Q, 426) 표와 서울 100m 인구격자(중심점→동) 표를 만든다."""
    gp, dp = WORK / 'grid_pop.parquet', WORK / 'dong.parquet'
    if gp.exists() and dp.exists() and not force:
        return pd.read_parquet(gp), pd.read_parquet(dp)
    import geopandas as gpd
    dong = gpd.read_file(SGIS / '03_행정구역' / '경계_2025_2Q' / 'bnd_dong_00_2025_2Q' / 'bnd_dong_00_2025_2Q.shp')
    dong = dong[dong['ADM_CD'].astype(str).str.startswith('11')].to_crs(5179)
    dong['adm_dong_cd'] = dong['ADM_CD'].astype(str)
    sg = gpd.read_file(SGIS / '03_행정구역' / '경계_2025_2Q' / 'bnd_sigungu_00_2025_2Q' / 'bnd_sigungu_00_2025_2Q.shp')
    sg = sg[sg['SIGUNGU_CD'].astype(str).str.startswith('11')]
    gmap = dict(zip(sg['SIGUNGU_CD'].astype(str), sg['SIGUNGU_NM']))
    dong['gu_cd'] = dong['adm_dong_cd'].str[:5]
    dong['gu_name'] = dong['gu_cd'].map(gmap)
    dong['dong_name'] = dong['ADM_NM']
    # 동 인구(행정구역 통계, 총인구 to_in_001)
    dt = dong[['adm_dong_cd', 'gu_cd', 'gu_name', 'dong_name']].copy()
    for s, y in YEARS.items():
        p = SGIS / '03_행정구역' / '통계_2019_2024' / f'(행정구역)11_{y}년_인구총괄(총인구).csv'
        t = pd.read_csv(p, header=None, encoding='cp949', dtype=str, names=['yr', 'cd', 'item', 'val'])
        t = t[(t.item == 'to_in_001') & (t.cd.str.len() == 8)]
        dt[f'pop{s}'] = dt['adm_dong_cd'].map(dict(zip(t.cd, pd.to_numeric(t.val, errors='coerce')))).fillna(0)
    # 격자 인구
    frames = []
    for s, y in YEARS.items():
        p = SGIS / '01_격자100m' / '통계_2019_2024' / f'{y}년_인구_다사_100M.csv'
        t = pd.read_csv(p, header=None, encoding='cp949', dtype=str, names=['yr', 'cd', 'item', 'val'])
        t = t[t.item == 'to_in_001'][['cd', 'val']]
        t[f'pop{s}'] = pd.to_numeric(t.val, errors='coerce').fillna(0); frames.append(t.set_index('cd')[[f'pop{s}']])
    g = pd.concat(frames, axis=1).fillna(0).reset_index().rename(columns={'cd': 'grid100_cd'})
    g['gi'] = g.grid100_cd.str[2:5].astype(int); g['gj'] = g.grid100_cd.str[5:8].astype(int)
    pts = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(900000 + g.gi * 100 + 50, 1900000 + g.gj * 100 + 50), crs=5179)
    j = gpd.sjoin(pts, dong[['adm_dong_cd', 'geometry']], how='inner', predicate='within')
    g = pd.DataFrame(j.drop(columns=['geometry', 'index_right']))
    g = g.drop_duplicates('grid100_cd')
    WORK.mkdir(exist_ok=True)
    g.to_parquet(gp, index=False); dt.to_parquet(dp, index=False)
    return g, dt


def rank(a):
    return pd.Series(a).rank(method='average').to_numpy()


def pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b)); a, b = a[m], b[m]
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    return pearson(rank(a[m]), rank(b[m]))


def kappa(a, b, w=None):
    """이진 a,b의 (가중) Cohen kappa와 일치율."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    w = np.ones(len(a)) if w is None else np.asarray(w, float)
    W = w.sum()
    po = w[a == b].sum() / W
    pa, pb = w[a].sum() / W, w[b].sum() / W
    pe = pa * pb + (1 - pa) * (1 - pb)
    k = (po - pe) / (1 - pe) if pe < 1 else np.nan
    return dict(agree=round(po, 4), kappa=round(k, 4), share_a=round(pa, 4), share_b=round(pb, 4),
                both1=round(w[a & b].sum() / W, 4), a_only=round(w[a & ~b].sum() / W, 4),
                b_only=round(w[~a & b].sum() / W, 4), both0=round(w[~a & ~b].sum() / W, 4))


def offsets(r):
    k = int(np.ceil(r / 100))
    return [(dx, dy) for dx in range(-k, k + 1) for dy in range(-k, k + 1) if (dx * dx + dy * dy) * 1e4 <= r * r]


def covered(grid, fac_cells, r):
    """격자 중심에서 반경 r(m) 안에 시설 격자(중심)가 있는지 (100m 해상도 근사)."""
    fi = set(fac_cells)
    fac = np.zeros((1000, 1000), bool)
    for c in fi:
        if isinstance(c, str) and c.startswith('다사'):
            fac[int(c[2:5]), int(c[5:8])] = True
    cov = np.zeros((1000, 1000), bool)
    for dx, dy in offsets(r):
        cov |= np.roll(np.roll(fac, dx, 0), dy, 1)
    return cov[grid.gi.to_numpy(), grid.gj.to_numpy()]


def load(path, filt=None):
    d = pd.read_parquet(path)
    d = d[d['inside_seoul'].astype('boolean').fillna(False).astype(bool) & d['grid100_cd'].notna()].copy()
    if filt is not None:
        d = d[filt(d)]
    return d


def quintile_low(v, q=0.2):
    """하위 q 분위 여부(동률은 순위 평균 사용)."""
    r = rank(v) / len(v)
    return r <= q
