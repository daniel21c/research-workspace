# -*- coding: utf-8 -*-
"""P5 공통 접근성 엔진 (access-engine-v3.1: 도달시간·Coverage·MAI·2SFCA).

정의 출처: 문서/지표정의_확정.md (이 파일은 그 문서를 그대로 구현한다)
  - 도달시간  t_b(o,c) = min_{g: c in C_g, 단위_b(g)=단위_b(o)} t_og
  - Coverage  r_b(o,c) = 1[J_b(o,c) != {}],  J_b(o,c) = {g : t_og <= T, c in C_g, 단위_b(g)=단위_b(o)}
  - MAI       m_b(o,c) = max_{g in J_b(o,c)} |C_g|   (J 가 비면 정의 안 됨)
  - 합집합    U_b(o)   = |OR_{g : t_og <= T, 단위_b(g)=단위_b(o)} C_g|   (Nicoletti 방식, --union)
  - 단위 집계  COV = Σp·r/Σp,  MAI = Σp·r·m/Σp·r,  PWATT = Σ_{t<=T} p·t / Σ_{t<=T} p  (항상 분자합/분모합)
  - 종합      COV = K개 단순평균,  MAI·PWATT·UNI = 값이 있는 카테고리 단순평균
  - 묶음 B    b = none, 시설별 τ, Coverage 만 (nat_standard_coverage_*.csv)
  - 2SFCA     R_b(g,k) = S_gk / Σ_{o: t_og<=T, 같은 단위} p_o,  A_b(o,k) = Σ_{g: t_og<=T, 같은 단위} R_b(g,k)  (sfca_unit_*.csv, 인구 1만 명당)

사용 예:
  python a06_engine.py --year 2025 --grid 100                       # 본 분석(main)
  python a06_engine.py --year 2025 --grid 100 --T 600 --tag sens_T600
  python a06_engine.py --year 2025 --grid 100 --catset B --tag natstd_B
  python a06_engine.py --year 2025 --grid 100 --ku 11010 --tag test_ku11010   # 한 구 시험
  python a06_engine.py --year 2020 --grid 100 --net-year 2025 --tag sens_net2025   # 네트워크 고정(2020 시설·인구 + 2025 보행망)
  python a06_engine.py --year 2025 --grid 100 --ld-other --tag xb_main            # 경계 교차(ld_other = ld2020), 연구3 시계열 확장
  python a06_engine.py --year 2020 --grid 100 --net-year 2025 --ld-other --tag xb_net2025
    (먼저 python a05c_ttm_supplement.py --net 2025 --for-year 2020 --grid 100 — 2025 표에 없는 2019 인구 격자 보충)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as pads

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a00_config as C  # noqa: E402
import a11_provenance as P

ENGINE_VERSION = 'access-engine-v3.2'   # v2 (2026-09-25): 2SFCA 추가, facility-v1.2 / v3 (2026-09-25): 2SFCA 공급 중복 제거, 실행 환경·입력 해시 기록
BOUNDS = ['none', 'dong424', 'lz116', 'ld', 'ku']          # 경계 조건 b (ld = 해당 연도 Leiden)
UNIT_LEVELS = ['dong424', 'lz116', 'ld', 'ku', 'seoul']     # 집계 단위 u
# --ld-other (2026-09-27, 연구3 시계열 확장): 경계 연도와 데이터 연도를 분리. 'ld_other' = 다른 연도의 Leiden
# (2020 데이터 → ld2025, 2025 데이터 → ld2020). 켜면 BOUNDS·UNIT_LEVELS 에 'ld_other' 가 더해지고 2SFCA 는 계산하지 않는다.
LD_OTHER_YEAR = {2020: 2025, 2025: 2020}
CAT_B_ORDER = ['교육', '돌봄', '의료', '체육', '편의']
POPCOUNT8 = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)


def popcount(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.uint16)
    return (POPCOUNT8[a & 0xFF] + POPCOUNT8[(a >> 8) & 0xFF]).astype(np.uint8)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- 핵심 계산 (순수 함수, 단위시험 대상)
def origin_access(o: np.ndarray, d: np.ndarray, t: np.ndarray, Cmask: np.ndarray,
                  unit_codes: dict, K: int, T: float, union: bool = False):
    """출발 격자별 r, m, t_min, (U) 를 경계 조건 b 와 카테고리 c 마다 계산.

    o, d   : 출발·도착 격자 정수 번호 (같은 길이), t: 소요시간(초, 속도 환산 끝난 값)
    Cmask  : 격자 번호 → 카테고리 비트마스크 (bit c = 카테고리 c 가 그 격자에 있음)
    unit_codes : {b: 격자 번호 → 단위 번호 배열} (b='none' 은 None)
    반환: dict b -> dict(o=고유 출발 번호, r=(n,K) uint8, m=(n,K) float(NaN=정의 안 됨),
                         t=(n,K) float(NaN=30분 내 없음), U=(n,) float 또는 None)
    출발 격자 집합은 입력 o 의 고유값 전체(도달 시설이 하나도 없어도 r=0 행으로 남음).
    """
    o = np.asarray(o, dtype=np.int64); d = np.asarray(d, dtype=np.int64); t = np.asarray(t, dtype=np.float64)
    uo = np.unique(o)
    n = len(uo)
    cm = Cmask[d]
    keep = cm > 0                                   # 시설 없는 도착 격자는 지표에 영향 없음
    o, d, t, cm = o[keep], d[keep], t[keep], cm[keep]
    order = np.lexsort((t, o))                      # 출발 번호 순 정렬
    o, d, t, cm = o[order], d[order], t[order], cm[order]
    pc = popcount(cm).astype(np.float64)
    within = t <= T
    pos = np.searchsorted(uo, o)                    # 출발 번호 → 결과 행
    out = {}
    for b in unit_codes:
        uc = unit_codes[b]
        mb = np.ones(len(o), bool) if uc is None else (uc[o] == uc[d])
        r = np.zeros((n, K), np.uint8)
        m = np.full((n, K), np.nan)
        tm = np.full((n, K), np.nan)
        for c in range(K):
            sel = mb & ((cm >> c) & 1).astype(bool)
            if not sel.any():
                continue
            ps, ts, pcs, ws = pos[sel], t[sel], pc[sel], within[sel]
            starts = np.flatnonzero(np.r_[True, ps[1:] != ps[:-1]])
            rows = ps[starts]
            tm[rows, c] = np.minimum.reduceat(ts, starts)
            mm = np.maximum.reduceat(np.where(ws, pcs, 0.0), starts)
            ok = mm > 0
            r[rows[ok], c] = 1
            m[rows[ok], c] = mm[ok]
        U = None
        if union:
            U = np.zeros(n, np.float64)
            sel = mb & within
            if sel.any():
                ps = pos[sel]
                starts = np.flatnonzero(np.r_[True, ps[1:] != ps[:-1]])
                orv = np.bitwise_or.reduceat(cm[sel].astype(np.uint16), starts)
                U[ps[starts]] = popcount(orv)
        out[b] = dict(o=uo, r=r, m=m, t=tm, U=U)
    return out


def sfca_access(o: np.ndarray, d: np.ndarray, popv: np.ndarray, S: np.ndarray, unit_codes: dict):
    """2SFCA (지표정의_확정.md 3.4). o, d: T 안의 (출발, 도착) 격자 번호 쌍(인구>0 출발만, 속도 환산 뒤 t<=T).
    popv: 격자 번호 → 인구, S: (격자 수, 항목 수) 시설 개수, unit_codes: {b: 격자 번호 → 단위 번호 또는 None}.
    1단계 D_b(g) = Σ_{(o,g) 쌍, 같은 단위} p_o, R = S / D (D=0 이면 할당 안 됨)
    2단계 A_b(o,k) = Σ_{(o,g) 쌍, 같은 단위} R(g,k)  (쌍이 없으면 0)
    반환: {b: dict(A=(격자 수, 항목 수) 1인당 시설 수, D=(격자 수,), assigned=(격자 수,) bool)}"""
    o = np.asarray(o, np.int64); d = np.asarray(d, np.int64)
    n = len(popv); out = {}
    for b, uc in unit_codes.items():
        if uc is None:
            oo, dd = o, d
        else:
            same = uc[o] == uc[d]; oo, dd = o[same], d[same]
        D = np.bincount(dd, weights=popv[oo], minlength=n)
        ok = D > 0
        R = np.zeros(S.shape, np.float64); R[ok] = S[ok] / D[ok, None]
        A = np.zeros(S.shape, np.float64)
        for k in range(S.shape[1]):
            A[:, k] = np.bincount(oo, weights=R[dd, k], minlength=n)
        out[b] = dict(A=A, D=D, assigned=ok)
    return out


def natstd_access(o, d, t, groups, n_grid):
    """묶음 B: 경계 없음, 시설 하위유형별 τ. groups = [(cat_B, 시설, tau_sec, 격자번호 배열)].
    반환: 출발 번호 uo, 하위유형별 r (n, G), 카테고리별 r (n, 5)."""
    o = np.asarray(o, np.int64); d = np.asarray(d, np.int64); t = np.asarray(t, np.float64)
    uo = np.unique(o)
    pos = np.searchsorted(uo, o)
    rg = np.zeros((len(uo), len(groups)), np.uint8)
    for j, (_, _, tau, cells) in enumerate(groups):
        has = np.zeros(n_grid, bool); has[cells] = True
        sel = has[d] & (t <= tau)
        rg[np.unique(pos[sel]), j] = 1
    rc = np.zeros((len(uo), len(CAT_B_ORDER)), np.uint8)
    for j, (cb, _, _, _) in enumerate(groups):
        rc[:, CAT_B_ORDER.index(cb)] |= rg[:, j]
    return uo, rg, rc


def aggregate(df: pd.DataFrame, level_col: str, cats: list, T: float, union: bool) -> pd.DataFrame:
    """격자 결과(df: unit, b, cat, pop, r, m, t[, U]) → 단위 × b × c. 분자합/분모합."""
    x = df.copy()
    x['pr'] = x['pop'] * x['r']
    x['prm'] = np.where(x['r'] == 1, x['pop'] * x['m'], 0.0)
    x['prt'] = np.where(x['r'] == 1, x['pop'] * x['t'], 0.0)   # r=1 ⇔ t<=T (같은 b)
    agg = {'pop': 'sum', 'pr': 'sum', 'prm': 'sum', 'prt': 'sum'}
    if union:
        x['prU'] = np.where(x['r'] == 1, x['pop'] * x['U'], 0.0)
        x['pU'] = x['pop'] * x['U']
        agg.update(prU='sum', pU='sum')
    g = x.groupby([level_col, 'b', 'cat'], sort=False).agg(agg).reset_index()
    g = g.rename(columns={level_col: 'unit_id', 'pop': 'pop_total', 'pr': 'pop_reach'})
    with np.errstate(invalid='ignore', divide='ignore'):
        g['COV'] = g['pop_reach'] / g['pop_total']
        g['MAI'] = np.where(g['pop_reach'] > 0, g['prm'] / g['pop_reach'], np.nan)
        g['PWATT_sec'] = np.where(g['pop_reach'] > 0, g['prt'] / g['pop_reach'], np.nan)
        if union:
            g['UNI'] = np.where(g['pop_reach'] > 0, g['prU'] / g['pop_reach'], np.nan)
            g['UNI_allpop'] = g['pU'] / g['pop_total']
    g = g.drop(columns=[c for c in ['prm', 'prt', 'prU', 'pU'] if c in g])
    # 종합 (카테고리 단순평균; MAI·PWATT·UNI 는 값 있는 카테고리만)
    comp = g.groupby(['unit_id', 'b'], sort=False).agg(
        pop_total=('pop_total', 'first'), COV=('COV', 'mean'), MAI=('MAI', 'mean'),
        PWATT_sec=('PWATT_sec', 'mean'), n_cat_mai=('MAI', 'count')).reset_index()
    if union:
        u2 = g.groupby(['unit_id', 'b'], sort=False).agg(UNI=('UNI', 'mean'), UNI_allpop=('UNI_allpop', 'first')).reset_index()
        comp = comp.merge(u2, on=['unit_id', 'b'])
    comp['cat'] = '종합'
    comp['pop_reach'] = np.nan
    g['n_cat_mai'] = np.nan
    res = pd.concat([g, comp[g.columns]], ignore_index=True)
    res['cat'] = pd.Categorical(res['cat'], categories=cats + ['종합'], ordered=True)
    res['b'] = pd.Categorical(res['b'], categories=BOUNDS, ordered=True)
    return res.sort_values(['unit_id', 'b', 'cat']).reset_index(drop=True)


def build_cmask(cells: np.ndarray, bits: np.ndarray, n_grid: int) -> np.ndarray:
    """시설(격자 번호, 카테고리 비트) → 격자별 비트마스크 C_g. 같은 격자·같은 카테고리 시설이 여러 개여도 비트는 하나."""
    Cm = np.zeros(n_grid, np.uint16)
    np.bitwise_or.at(Cm, np.asarray(cells, np.int64), (np.uint16(1) << np.asarray(bits, np.uint16)).astype(np.uint16))
    return Cm


def read_ttm_ku(dset, k: int, code: pd.Series, popv: np.ndarray, factor: float, snap_sec: np.ndarray | None = None):
    """한 구(출발 구 k) 분할을 읽어 (o, d, t 환산초, 원래 행 수) 반환. 인구>0 출발만 남긴다.
    snap_sec 가 있으면(스냅 거리 민감도) o ≠ d 쌍에 양끝 격자 중심 → 노드 보행 시간을 더한다(같은 격자 쌍은 0 유지)."""
    tt = dset.to_table(filter=(pads.field('ku') == k), columns=['o_grid', 'd_grid', 't_sec']).to_pandas()
    o = tt['o_grid'].map(code).values; d = tt['d_grid'].map(code).values
    ok = ~(pd.isna(o) | pd.isna(d))
    o = o[ok].astype(np.int64); d = d[ok].astype(np.int64)
    t = tt['t_sec'].values[ok].astype(np.float64) * factor
    if snap_sec is not None:
        t = t + np.where(o != d, snap_sec[o] + snap_sec[d], 0.0)
    is_o = popv[o] > 0
    return o[is_o], d[is_o], t[is_o], len(tt)


def load_snap_sec(grid: int, net: int, gm: pd.DataFrame, speed: float):
    """격자 중심 → 가장 가까운 보행망 노드 거리(a05 스냅 파일, 보행망 시점 net)를 속도로 나눈 초. 격자 번호(gi) 순."""
    s = pd.read_parquet(C.DATA / 'ttm' / f'snap{grid}_{net}.parquet', columns=['grid_cd', 'snap_m'])
    m = gm['grid_cd'].map(s.set_index('grid_cd')['snap_m'])
    info = dict(snap_file=f'데이터/입력/ttm/snap{grid}_{net}.parquet', snap_missing_cells=int(m.isna().sum()),
                snap_m_popweighted=float((m.fillna(0) * gm['pop']).sum() / gm['pop'].sum()))
    return m.fillna(0.0).values.astype(np.float64) * 3.6 / speed, info


# ---------------------------------------------------------------- 입력
def load_inputs(year: int, grid: int, catset: str, retail: str):
    py = C.YEARS[year]['pop_year']
    gm = pd.read_parquet(C.DATA / 'grid' / f'grid{grid}_master.parquet')
    gm = gm.reset_index(drop=True)
    gm['gi'] = np.arange(len(gm))
    gm['pop'] = gm[f'pop_{py}'].astype(float)
    gm['ld'] = gm[f'ld{year}']
    gcol = 'grid100_cd' if grid == 100 else 'grid250_cd'
    f = pd.read_parquet(C.DATA / 'facility' / 'facility_2020_2025_units.parquet',
                        columns=['year', '시설', '시설_세부', '분석가능', 'cat_A', 'cat_A4', 'cat_B', 'tau_B_min', 'role', gcol])
    f = f[(f['year'] == year) & (f['분석가능'].astype(bool))].copy()
    info = dict(fac_rows_year_analyzable=int(len(f)))
    if retail == 'without':
        info['retail_removed'] = int((f['시설'] == '일상소매').sum())
        f = f[f['시설'] != '일상소매']
    idx = pd.Series(gm['gi'].values, index=gm['grid_cd'].values)
    f['gi'] = f[gcol].map(idx)
    if catset in ('A', 'A4'):
        f = f[f['role'].astype(str) != 'control']
        col = 'cat_A' if catset == 'A' else 'cat_A4'
        cats = list(C.CAT_A.keys()) if catset == 'A' else list(C.CAT_A4.keys())
        f = f[f[col].isin(cats)]
        info['fac_rows_used'] = int(len(f)); info['fac_rows_outside_grid'] = int(f['gi'].isna().sum())
        f = f.dropna(subset=['gi'])
        f['bit'] = f[col].map({c: i for i, c in enumerate(cats)}).astype(int)
        Cmask = build_cmask(f['gi'].astype(int).values, f['bit'].values, len(gm))
        info['fac_cells'] = int((Cmask > 0).sum())
        info['fac_cells_by_cat'] = {c: int(((Cmask >> i) & 1).sum()) for i, c in enumerate(cats)}
        info['Cg_dist'] = {int(k): int(v) for k, v in pd.Series(popcount(Cmask[Cmask > 0])).value_counts().sort_index().items()}
        return gm, cats, Cmask, None, info
    # 묶음 B
    f = f[f['cat_B'].notna() & f['role'].astype(str).str.contains('B')]
    info['fac_rows_used'] = int(len(f)); info['fac_rows_outside_grid'] = int(f['gi'].isna().sum())
    f = f.dropna(subset=['gi'])
    groups = []
    for (cb, fac, tau), s in f.groupby(['cat_B', '시설', 'tau_B_min'], sort=True):
        groups.append((cb, fac, float(tau) * 60.0, np.unique(s['gi'].astype(int).values)))
    info['groups'] = [(g[0], g[1], int(g[2] // 60), int(len(g[3]))) for g in groups]
    return gm, CAT_B_ORDER, None, groups, info


SUPPLY_KEY = ['name', 'x_5179', 'y_5179']      # 같은 시설 판정: 이름·좌표가 모두 같으면 한 곳(지표정의_확정.md 3.4)


def build_supply(year: int, grid: int, retail: str, gm: pd.DataFrame):
    """2SFCA 공급 행렬: 항목 = 기능 카테고리 8개 + 시설 28종, 값 = 격자별 분석가능 시설 개수.
    중복 제거(v3): 시설 항목은 (시설, 이름, 좌표)가 같은 행을 한 곳으로, 카테고리 항목은 문화기반시설 중 공공도서관 행
    (공공도서관 종과 같은 시설)을 빼고 (카테고리, 이름, 좌표)가 같은 행을 한 곳으로 센다. Coverage·MAI 는 격자 비트라 영향 없음."""
    gcol = 'grid100_cd' if grid == 100 else 'grid250_cd'
    f = pd.read_parquet(C.DATA / 'facility' / 'facility_2020_2025_units.parquet',
                        columns=['year', '시설', '시설_세부', '분석가능', 'cat_A', 'role', gcol] + SUPPLY_KEY)
    f = f[(f['year'] == year) & f['분석가능'].astype(bool) & (f['role'].astype(str) != 'control') & f['cat_A'].isin(list(C.CAT_A))]
    if retail == 'without':
        f = f[f['시설'] != '일상소매']
    idx = pd.Series(gm['gi'].values, index=gm['grid_cd'].values)
    gi = f[gcol].map(idx)
    f = f[gi.notna()].assign(gi=gi[gi.notna()].astype(np.int64))
    n0 = len(f)
    fac = f.drop_duplicates(['시설'] + SUPPLY_KEY)
    lib = (fac['시설'] == '문화기반시설') & fac['시설_세부'].isin(C.SUPPLY_CAT_EXCLUDE['문화기반시설'])
    cat = fac[~lib].drop_duplicates(['cat_A'] + SUPPLY_KEY)
    dedup = dict(rows_in=int(n0), facility_dup_removed=int(n0 - len(fac)), category_library_removed=int(lib.sum()),
                 category_cross_type_removed=int((~lib).sum() - len(cat)))
    items = [('category', c) for c in C.CAT_A] + [('facility', s) for fs in C.CAT_A.values() for s in fs]
    items = [(t, k) for t, k in items if (fac['cat_A' if t == 'category' else '시설'] == k).any()]
    S = np.zeros((len(gm), len(items)), np.float64)
    for j, (t, k) in enumerate(items):
        s = cat[cat['cat_A'] == k] if t == 'category' else fac[fac['시설'] == k]
        np.add.at(S[:, j], s['gi'].values, 1.0)
    return items, S, dedup


def ttm_partitions(year: int, grid: int, ku: int | None, net_year: int | None = None):
    """소요시간표 데이터셋. net_year 가 year 와 다르면(네트워크 고정 민감도) ttm{grid}_{net_year} 를 읽고,
    그 표에 출발로 없는 year 시점 인구 격자는 a05c_ttm_supplement.py 가 만든 ttm{grid}_{net_year}_for{year} 로 보충한다."""
    net = year if net_year is None else net_year
    base = C.DATA / 'ttm' / f'ttm{grid}_{net}'
    dset = pads.dataset(str(base), format='parquet', partitioning='hive')
    kus = sorted({int(p.split('ku=')[1].split('/')[0].split('\\')[0]) for p in dset.files})
    if net != year:
        extra = C.DATA / 'ttm' / f'ttm{grid}_{net}_for{year}'
        if extra.exists():
            dset = pads.dataset([dset, pads.dataset(str(extra), format='parquet', partitioning='hive')])
    if ku is not None:
        kus = [k for k in kus if k == ku]
    return dset, kus


SFCA_OWN_B = {'dong424': 'dong424', 'lz116': 'lz116', 'ld': 'ld', 'ku': 'ku'}   # 경계 개방비의 분모: 그 단위 자신의 경계 조건


def sfca_outputs(gm, items, S, sres, pos_cells, year, grid, T, speed, retail, outdir, suffix, save_grid):
    """2SFCA 단위 집계(분자합/분모합) → sfca_unit_*.csv, (선택) grid_sfca_*.parquet, 공급 보존 검사."""
    popv = gm['pop'].values
    keys = {lvl: (np.zeros(len(gm), np.int64) if lvl == 'seoul' else gm[lvl].astype(np.int64).values) for lvl in UNIT_LEVELS}
    it_type = np.array([t for t, _ in items], dtype=object); it_name = np.array([k for _, k in items], dtype=object)
    p = popv[pos_cells]
    rows = []; chk = {}; worst_g = 0.0; worst_u = 0.0; nonneg = True
    unassigned = {}
    for b, v in sres.items():
        A = v['A']; ok = v['assigned']
        nonneg &= bool((A >= -1e-15).all())
        tot_pa = (p[:, None] * A[pos_cells]).sum(0)
        tot_s = S[ok].sum(0)
        worst_g = max(worst_g, float(np.max(np.abs(tot_pa - tot_s) / np.maximum(tot_s, 1))))
        unassigned[b] = {it_name[j]: int(S[~ok, j].sum()) for j in range(len(items)) if it_type[j] == 'category'}
        for lvl in UNIT_LEVELS:
            key_o = keys[lvl][pos_cells]
            dfo = pd.DataFrame(p[:, None] * A[pos_cells], columns=range(len(items))); dfo['u'] = key_o
            num = dfo.groupby('u').sum()
            pz = pd.DataFrame(p[:, None] * (A[pos_cells] <= 0), columns=range(len(items))); pz['u'] = key_o
            zer = pz.groupby('u').sum()
            pt = pd.Series(p).groupby(key_o).sum()
            sup = pd.DataFrame(S, columns=range(len(items))).groupby(keys[lvl]).sum().reindex(num.index, fill_value=0)
            una = pd.DataFrame(S * (~ok)[:, None], columns=range(len(items))).groupby(keys[lvl]).sum().reindex(num.index, fill_value=0)
            if SFCA_OWN_B.get(lvl) == b:          # 단위 자신의 경계: 단위마다 공급 보존
                worst_u = max(worst_u, float(np.max(np.abs(num.values - (sup.values - una.values)))))
            n_u = len(num)
            rows.append(pd.DataFrame({'unit_level': lvl, 'unit_id': np.repeat(num.index.values, len(items)), 'b': b,
                                      'item_type': np.tile(it_type, n_u), 'item': np.tile(it_name, n_u),
                                      'pop_total': np.repeat(pt.reindex(num.index).values, len(items)),
                                      'supply_in_unit': sup.values.ravel(), 'supply_unassigned_in_unit': una.values.ravel(),
                                      'SFCA_per10k': (num.values / pt.reindex(num.index).values[:, None]).ravel() * 1e4,
                                      'pop_share_A0': (zer.values / pt.reindex(num.index).values[:, None]).ravel()}))
    su = pd.concat(rows, ignore_index=True)
    # 경계 개방비 OR = SFCA_none / SFCA_{그 단위 자신의 경계}  (b = none 행에만)
    own = su[su['unit_level'].map(SFCA_OWN_B) == su['b']][['unit_level', 'unit_id', 'item', 'SFCA_per10k']].rename(columns={'SFCA_per10k': '_own'})
    su = su.merge(own, on=['unit_level', 'unit_id', 'item'], how='left')
    with np.errstate(divide='ignore', invalid='ignore'):
        su['open_ratio'] = np.where((su.b == 'none') & (su._own > 0), su.SFCA_per10k / su._own, np.nan)
    su = su.drop(columns='_own')
    su['b'] = pd.Categorical(su['b'], categories=BOUNDS, ordered=True)
    su = su.sort_values(['unit_level', 'unit_id', 'b', 'item_type', 'item'], kind='stable').reset_index(drop=True)
    for c, v in [('year', year), ('grid_m', grid), ('T_sec', T), ('speed_kmh', speed), ('retail', retail)][::-1]:
        su.insert(0, c, v)
    files = []
    pth = outdir / f'sfca_unit_{suffix}.csv'
    su.to_csv(pth, index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n'); files.append(pth)
    if save_grid:
        g = []
        for b, v in sres.items():
            n = len(pos_cells)
            g.append(pd.DataFrame({'grid_cd': np.repeat(gm['grid_cd'].values[pos_cells], len(items)), 'b': b,
                                   'item': np.tile(it_name, n), 'A_per10k': (v['A'][pos_cells].ravel() * 1e4).astype(np.float32)}))
        gg = pd.concat(g, ignore_index=True)
        gg['b'] = pd.Categorical(gg['b'], categories=BOUNDS); gg['item'] = pd.Categorical(gg['item'], categories=list(dict.fromkeys(it_name)))
        pth = outdir / f'grid_sfca_{suffix}.parquet'; gg.to_parquet(pth, index=False); files.append(pth)
    chk['sfca_nonneg'] = nonneg
    chk['sfca_conservation_global'] = bool(worst_g < 1e-9)
    chk['sfca_conservation_unit'] = bool(worst_u < 1e-6)
    meta = dict(items=len(items), worst_rel_err_global=worst_g, worst_abs_err_unit=worst_u, supply_unassigned_category=unassigned)
    return files, chk, meta


# ---------------------------------------------------------------- 실행
def run(args):
    global BOUNDS, UNIT_LEVELS
    t0 = time.time()
    # Each run owns its boundary configuration, including repeated in-process runs.
    BOUNDS = ['none', 'dong424', 'lz116', 'ld', 'ku']
    UNIT_LEVELS = ['dong424', 'lz116', 'ld', 'ku', 'seoul']
    year, grid, T, speed = args.year, args.grid, float(args.T), float(args.speed)
    factor = C.WALK_KMH / speed                     # 소요시간 환산 (4.0 km/h 기준 표)
    gm, cats, Cmask, groups, info = load_inputs(year, grid, args.catset, args.retail)
    ld_other = bool(getattr(args, 'ld_other', False))
    if ld_other:
        gm['ld_other'] = gm[f'ld{LD_OTHER_YEAR[year]}']
        if 'ld_other' not in BOUNDS:
            BOUNDS = BOUNDS + ['ld_other']
            UNIT_LEVELS = UNIT_LEVELS[:-1] + ['ld_other', 'seoul']
    K = len(cats)
    code = pd.Series(gm['gi'].values, index=gm['grid_cd'].values)
    popv = gm['pop'].values
    unit_codes = {'none': None}
    for b in BOUNDS[1:]:
        unit_codes[b] = gm[b].astype(np.int64).values
    net = year if args.net_year is None else args.net_year
    dset, kus = ttm_partitions(year, grid, args.ku, net)
    provenance = P.capture_run(args, P.dataset_files(dset))
    snap_sec = None
    if args.snap:
        snap_sec, snap_info = load_snap_sec(grid, net, gm, speed)
        info = {**info, **snap_info}
    parts, parts_b = [], []
    n_rows = 0
    do_sfca = args.catset == 'A' and args.ku is None and not ld_other   # 2SFCA 는 집수역이 구를 넘으므로 서울 전체 실행에서만; 경계 교차 실행(xb)에서는 계산 안 함
    wo, wd = [], []
    for k in kus:
        o, d, t, nr = read_ttm_ku(dset, k, code, popv, factor, snap_sec)
        n_rows += nr
        if args.catset == 'B':
            uo, rg, rc = natstd_access(o, d, t, groups, len(gm))
            parts_b.append((uo, rg, rc))
            continue
        if do_sfca:
            w = t <= T; wo.append(o[w].astype(np.int32)); wd.append(d[w].astype(np.int32))
        res = origin_access(o, d, t, Cmask, unit_codes, K, T, union=args.union)
        for b, v in res.items():
            n = len(v['o'])
            dfp = pd.DataFrame({'gi': np.repeat(v['o'], K), 'b': b, 'cat': np.tile(np.array(cats, dtype=object), n),
                                'r': v['r'].ravel(), 'm': v['m'].ravel(), 't': v['t'].ravel()})
            if args.union:
                dfp['U'] = np.repeat(v['U'], K)
            parts.append(dfp)
    # 인구>0 인데 소요시간표 출발에 없는 격자 확인(있으면 r=0 으로 넣어야 함)
    pos_cells = gm.loc[gm['pop'] > 0, 'gi'].values
    if args.ku is not None:
        pos_cells = gm.loc[(gm['pop'] > 0) & (gm['ku'] == args.ku), 'gi'].values
    outdir = (Path(args.out_root) if args.out_root else C.OUT) / args.tag
    outdir.mkdir(parents=True, exist_ok=True)
    meta = dict(engine=ENGINE_VERSION, year=year, grid_m=grid, T_sec=T, speed_kmh=speed, catset=args.catset,
                retail=args.retail, union=bool(args.union), tag=args.tag, ku=args.ku, ttm_rows=int(n_rows), **info,
                env=C.runtime_env(), facility_units_source_sha256=C.units_source_sha256(),
                snap=bool(args.snap), ld_other=ld_other, provenance=provenance)
    if net != year:                                   # 네트워크 고정 민감도일 때만 기록(기본 실행의 run_meta 는 그대로)
        meta['net_year'] = net
        meta['ttm_dirs'] = [f'데이터/입력/ttm/ttm{grid}_{net}'] + ([f'데이터/입력/ttm/ttm{grid}_{net}_for{year}']
                                                               if (C.DATA / 'ttm' / f'ttm{grid}_{net}_for{year}').exists() else [])
        meta['boundary_ld'] = f'ld{year}'
    if ld_other:
        meta['boundary_year'] = {'lz116': 'fixed', 'ld': year, 'ld_other': LD_OTHER_YEAR[year]}
        meta['sfca_skipped'] = 'ld_other 실행에서는 2SFCA 계산 안 함'
    files = []
    suffix = f'{year}_{grid}' + (f'_ku{args.ku}' if args.ku else '')
    if args.catset == 'B':
        uo = np.concatenate([p[0] for p in parts_b]); rg = np.vstack([p[1] for p in parts_b]); rc = np.vstack([p[2] for p in parts_b])
        missing = np.setdiff1d(pos_cells, uo)
        if net != year and len(missing):
            raise SystemExit(f'출발 {len(missing)}셀이 ttm{grid}_{net} 에 없음 → a05c_ttm_supplement.py 먼저 실행')
        if len(missing):
            uo = np.r_[uo, missing]; rg = np.vstack([rg, np.zeros((len(missing), rg.shape[1]), np.uint8)]); rc = np.vstack([rc, np.zeros((len(missing), rc.shape[1]), np.uint8)])
        meta['origins'] = int(len(uo)); meta['origins_missing_in_ttm'] = int(len(missing))
        g = gm.iloc[uo]
        gdf = pd.DataFrame({'grid_cd': g['grid_cd'].values, 'pop': g['pop'].values})
        for j, c in enumerate(CAT_B_ORDER):
            gdf[f'r_{c}'] = rc[:, j]
        for j, (cb, fac, tau, _) in enumerate(groups):
            gdf[f'r_{cb}_{fac}_{int(tau // 60)}분'] = rg[:, j]
        gdf.to_parquet(outdir / f'grid_access_{suffix}.parquet', index=False)
        files.append(outdir / f'grid_access_{suffix}.parquet')
        rows = []
        cols_c = [f'r_{c}' for c in CAT_B_ORDER]; cols_g = [c for c in gdf.columns if c.startswith('r_') and c not in cols_c]
        for lvl in UNIT_LEVELS:
            key = np.zeros(len(g), np.int64) if lvl == 'seoul' else g[lvl].values
            tmp = gdf.assign(unit_id=key)
            for col in cols_c + cols_g:
                s = tmp.assign(pr=tmp['pop'] * tmp[col]).groupby('unit_id').agg(pop_total=('pop', 'sum'), pop_reach=('pr', 'sum')).reset_index()
                s['COV'] = s['pop_reach'] / s['pop_total']
                s['item'] = col[2:]; s['level'] = 'category' if col in cols_c else 'facility'; s['unit_level'] = lvl
                rows.append(s)
            pt = tmp.groupby('unit_id')['pop'].sum()
            covs = [(tmp['pop'] * tmp[c]).groupby(tmp['unit_id']).sum() / pt for c in cols_c]
            s = pd.DataFrame({'unit_id': pt.index, 'pop_total': pt.values, 'COV': np.mean(np.vstack([v.values for v in covs]), axis=0)})
            s['item'] = '종합(5개 단순평균)'; s['level'] = 'composite'; s['unit_level'] = lvl; s['pop_reach'] = np.nan
            rows.append(s)
        nat = pd.concat(rows, ignore_index=True)
        nat.insert(0, 'year', year); nat.insert(1, 'grid_m', grid); nat.insert(2, 'speed_kmh', speed)
        nat = nat[['year', 'grid_m', 'speed_kmh', 'unit_level', 'unit_id', 'level', 'item', 'pop_total', 'pop_reach', 'COV']]
        p = outdir / f'nat_standard_coverage_{suffix}.csv'
        nat.to_csv(p, index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n'); files.append(p)
        meta['checks'] = dict(origins_complete=len(uo)==len(pos_cells) and len(set(uo))==len(uo),
            COV_in_0_1=bool(nat.COV.between(0,1).all()),
            reach_in_0_1=bool(((rg==0)|(rg==1)).all() and ((rc==0)|(rc==1)).all()),
            pop_total_same_all_levels=bool(nat[nat.level=='composite'].groupby('unit_level').pop_total.sum().nunique()==1))
    else:
        df = pd.concat(parts, ignore_index=True)
        got = np.unique(df['gi'].values)
        missing = np.setdiff1d(pos_cells, got)
        if net != year and len(missing):                  # 다른 시점 네트워크: 표에 없는 출발은 미도달이 아니라 미계산
            raise SystemExit(f'출발 {len(missing)}셀이 ttm{grid}_{net} 에 없음 → a05c_ttm_supplement.py --net {net} --for-year {year} --grid {grid} 먼저 실행')
        if len(missing):                                  # 도달 불가 출발(표에 없음) → r=0
            add = []
            for b in BOUNDS:
                a = pd.DataFrame({'gi': np.repeat(missing, K), 'b': b, 'cat': np.tile(np.array(cats, dtype=object), len(missing)), 'r': 0, 'm': np.nan, 't': np.nan})
                if args.union:
                    a['U'] = 0.0
                add.append(a)
            df = pd.concat([df] + add, ignore_index=True)
        meta['origins'] = int(len(np.unique(df['gi']))); meta['origins_missing_in_ttm'] = int(len(missing))
        g = gm.set_index('gi')
        df['pop'] = popv[df['gi'].values]
        for lvl in [l for l in UNIT_LEVELS if l != 'seoul']:
            df[lvl] = g[lvl].values[df['gi'].values]
        df['seoul'] = 0
        # 격자 결과 저장
        gout = pd.DataFrame({'grid_cd': gm['grid_cd'].values[df['gi'].values], 'b': pd.Categorical(df['b'], categories=BOUNDS),
                             'cat': pd.Categorical(df['cat'], categories=cats), 'pop': df['pop'].astype(np.float32 if grid == 250 else np.int32),
                             'r': df['r'].astype(np.uint8), 'm': df['m'].astype('Float32'), 't_min_sec': df['t'].astype(np.float32)})
        if args.union:
            gout['U'] = df['U'].astype(np.uint8)
        gout = gout.sort_values(['grid_cd', 'b', 'cat']).reset_index(drop=True)
        p = outdir / f'grid_access_{suffix}.parquet'
        gout.to_parquet(p, index=False); files.append(p)
        # 단위 집계
        out = []
        for lvl in UNIT_LEVELS:
            a = aggregate(df, lvl, cats, T, args.union)
            a.insert(0, 'unit_level', lvl)
            out.append(a)
        ua = pd.concat(out, ignore_index=True)
        ua.insert(0, 'year', year); ua.insert(1, 'grid_m', grid); ua.insert(2, 'T_sec', T); ua.insert(3, 'speed_kmh', speed); ua.insert(4, 'catset', args.catset); ua.insert(5, 'retail', args.retail)
        cols = ['year', 'grid_m', 'T_sec', 'speed_kmh', 'catset', 'retail', 'unit_level', 'unit_id', 'b', 'cat', 'pop_total', 'pop_reach', 'COV', 'MAI', 'PWATT_sec', 'n_cat_mai'] + (['UNI', 'UNI_allpop'] if args.union else [])
        ua = ua[cols]
        p = outdir / f'unit_access_{suffix}.csv'
        ua.to_csv(p, index=False, encoding='utf-8-sig', float_format='%.6f', lineterminator='\n'); files.append(p)
        # 불변 조건 검사
        chk = {}
        s = ua[(ua.unit_level == 'seoul') & (ua.cat == '종합')].set_index('b')
        chk['pop_total_same_all_b'] = bool(s['pop_total'].nunique() == 1)
        chk['seoul_pop_total'] = float(s['pop_total'].iloc[0])
        cat_rows = ua[ua.cat != '종합']
        chk['COV_in_0_1'] = bool(cat_rows['COV'].between(0, 1).all())
        chk['MAI_in_1_K'] = bool(cat_rows['MAI'].dropna().between(1, K).all())
        chk['PWATT_le_T'] = bool((cat_rows['PWATT_sec'].dropna() <= T + 1e-9).all())
        # 경계 제한은 도달을 늘릴 수 없다: r_b <= r_none (격자 수준)
        piv = df.pivot_table(index=['gi', 'cat'], columns='b', values='r', aggfunc='first', observed=True)
        chk['r_b_le_r_none'] = bool(all((piv[b] <= piv['none']).all() for b in BOUNDS[1:]))
        chk['r_ku_ge_r_dong'] = bool((piv['dong424'] <= piv['ku']).all())   # 동 ⊂ 구
        if do_sfca:
            items, S, dedup = build_supply(year, grid, args.retail, gm)
            sres = sfca_access(np.concatenate(wo), np.concatenate(wd), popv, S, unit_codes)
            f_s, c_s, m_s = sfca_outputs(gm, items, S, sres, pos_cells, year, grid, T, speed, args.retail, outdir, suffix, args.save_sfca_grid)
            files += f_s; chk.update(c_s); meta['sfca'] = {**m_s, 'supply_dedup': dedup}
        meta['checks'] = chk
    drift = P.check_inventory(provenance['inputs'], C.DATA) + P.check_inventory(provenance['upstream_inputs'], C.BASE)
    if drift:
        raise RuntimeError('Inputs changed during calculation: ' + '; '.join(drift))
    meta['files_base'] = 'run_meta_directory'
    meta['files'] = [dict(file=p.name, sha256=sha256(p), bytes=p.stat().st_size) for p in files]
    meta['seconds'] = round(time.time() - t0, 1)
    mp = outdir / f'run_meta_{suffix}.json'
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in meta.items() if k not in ('files',)}, ensure_ascii=False))
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description='P5 공통 접근성 엔진')
    ap.add_argument('--year', type=int, choices=[2020, 2025], required=True)
    ap.add_argument('--grid', type=int, choices=[100, 250], default=100)
    ap.add_argument('--T', type=float, default=C.T_SEC)
    ap.add_argument('--speed', type=float, default=C.WALK_KMH)
    ap.add_argument('--catset', choices=['A', 'A4', 'B'], default='A')
    ap.add_argument('--retail', choices=['with', 'without'], default='with')
    ap.add_argument('--union', action='store_true')
    ap.add_argument('--tag', default='main')
    ap.add_argument('--ku', type=int, default=None, help='한 구만 시험 계산(출발 구 코드, 예 11010)')
    ap.add_argument('--net-year', type=int, choices=[2020, 2025], default=None,
                    help='소요시간표(보행망) 시점. 기본 = --year. 다르면 네트워크 고정 민감도(예: --year 2020 --net-year 2025)')
    ap.add_argument('--snap', action='store_true', help='스냅 거리 민감도: o≠d 쌍에 양끝 격자 중심→노드 보행 시간을 더함(sens_snap)')
    ap.add_argument('--ld-other', action='store_true', help='경계 조건 ld_other(다른 연도 Leiden) 추가: 2020 데이터→ld2025, 2025 데이터→ld2020. 2SFCA 는 계산 안 함(xb_*)')
    ap.add_argument('--out-root', default=None, help='출력 상위 폴더(기본 데이터/결과). 재현 점검용')
    ap.add_argument('--save-sfca-grid', action='store_true', help='2SFCA 격자 값(grid_sfca_*.parquet)도 저장(본 분석용, 약 5백만 행)')
    a = ap.parse_args(argv)
    if a.T > C.TTM_MAX_SEC * C.WALK_KMH / a.speed:
        ap.error('T 가 소요시간표 저장 상한(30분, 속도 환산)보다 큼')
    return run(a)


if __name__ == '__main__':
    main()
