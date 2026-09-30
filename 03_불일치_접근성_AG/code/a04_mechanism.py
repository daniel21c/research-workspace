# -*- coding: utf-8 -*-
"""결과 4: 경계 동의 통행은 걸어서 닿는 시설이 더 많은 인접 생활권으로 향하는가(동 단위 공존 검정).
입력: study.py의 7범주 시설·424동·100 m 격자·15분 보행시간표. 2026-09-29 explore/v3/7cat/e18_mechanism_7cat.py를 경로만 바꿔 옮김.
단위: 경계 동 i × 같은 구 안에서 15분 안에 닿는 인접 공식 생활권 z(자기 생활권 제외 = e08 v2 주 결과).
 W = i의 동 밖 통행 중 z로 가는 비중, F = i에서 15분 안에 닿는 시설 격자(범주별, 출발 인구가중) 중 z 안의 비중(7범주 평균),
 A = 도달 격자 비중, P = 도달 인구 비중, 목적지 z의 log 인구·log 종사자.
검정: W–F 편상관 Spearman(A·P·log 인구·log 종사자 통제), 동 고정효과 표준화 계수, 동 단위 군집 부트스트랩 2,000회(시드 20261001+연도, e08과 같음).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402


def presid(v, C):
    X = np.column_stack([np.ones(len(v))] + [rankdata(c) for c in C]); r = rankdata(v); return r - X @ np.linalg.lstsq(X, r, rcond=None)[0]


def pcorr(x, y, C):
    return float(np.corrcoef(presid(x, C), presid(y, C))[0, 1])


def fe_beta(df, cols):
    d = df.copy()
    for c in ['W'] + cols:
        d[c] = (d[c] - d.groupby('i')[c].transform('mean')) / df[c].std()
    return np.linalg.lstsq(d[cols].to_numpy(), d.W.to_numpy(), rcond=None)[0]


def main(year):
    rng = np.random.default_rng(20261001 + year); OUT = AG / 'results' / str(year); OUT.mkdir(parents=True, exist_ok=True); SC = AG / 'results' / '_cache' / str(year); SC.mkdir(parents=True, exist_ok=True)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths); ev = S.Accessibility(D, paths, SC)
    gm = D['gm']; code = pd.Series(np.arange(len(gm)), index=gm.grid_cd); gd = D['gd']; LZ = D['LZ']; zcell = LZ[gd]; pop = D['pop']; mask = ev.mask; nD = 424; nZ = LZ.max() + 1; K = 7
    Az = np.zeros((nD, nZ)); Pz = np.zeros((nD, nZ)); Fz = np.zeros((nD, nZ, K))
    for pth in sorted(paths['ttm'].glob('ku=*/*.parquet')):
        x = pq.read_table(pth, columns=['o_grid', 'd_grid', 't_sec']).to_pandas()
        o = x.o_grid.map(code).to_numpy(int); d = x.d_grid.map(code).to_numpy(int); sel = (x.t_sec.to_numpy() <= 900) & (pop[o] > 0); o, d = o[sel], d[sel]
        io, zd, pw = gd[o], zcell[d], pop[o]
        np.add.at(Az, (io, zd), pw); np.add.at(Pz, (io, zd), pw * pop[d])
        for c in range(K):
            s = ((mask[d] >> c) & 1).astype(bool); np.add.at(Fz[:, :, c], (io[s], zd[s]), pw[s])
    with np.errstate(invalid='ignore', divide='ignore'):
        Fs = Fz / Fz.sum(1, keepdims=True); As = Az / Az.sum(1, keepdims=True); Ps = Pz / Pz.sum(1, keepdims=True)
    Fm = np.nanmean(Fs, 2)
    F = D['F'].copy(); np.fill_diagonal(F, 0); Wz = np.zeros((nD, nZ)); np.add.at(Wz.T, LZ, F.T); Wz = Wz / Wz.sum(1, keepdims=True)
    PY = 2019 if year == 2020 else 2024; zpop = pd.Series(D['popd']).groupby(LZ).sum(); zemp = pd.Series(np.bincount(gd, weights=gm[f'emp_{PY}'].fillna(0).to_numpy(), minlength=nD)).groupby(LZ).sum()
    boundary = np.array([any(LZ[u] != LZ[v] for u in D['G'][v]) for v in range(nD)])
    zku = pd.Series(D['ku']).groupby(LZ).first(); rows = []
    for i in np.flatnonzero(boundary):
        for z in np.flatnonzero(As[i] > 0):
            if z == LZ[i] or zku.get(z) != D['ku'][i]:
                continue
            rows.append({'i': i, 'dong': int(D['dongs'][i]), 'z': int(z), 'W': Wz[i, z], 'F': Fm[i, z], 'A': As[i, z], 'P': Ps[i, z], 'logZpop': float(np.log(zpop[z] + 1)), 'logZemp': float(np.log(zemp[z] + 1)),
                         **{f'F_{S.CATS[c]}': Fs[i, z, c] for c in range(K)}})
    O = pd.DataFrame(rows).dropna(subset=['W', 'F', 'A', 'P']).reset_index(drop=True); O.to_csv(OUT / 'a04_mechanism_pairs.csv', index=False, encoding='utf-8-sig')
    ids = O.i.unique(); groups = {i: np.flatnonzero(O.i.to_numpy() == i) for i in ids}
    def boot(fun, B):
        v = []
        for _ in range(B):
            idx = np.concatenate([groups[i] for i in rng.choice(ids, len(ids))]); v.append(fun(O.iloc[idx]))
        return np.quantile(np.array(v), [.025, .975], axis=0).tolist()
    out = {'year': year, 'n_pairs': int(len(O)), 'n_dongs': int(len(ids))}
    for nm, Cc in (('partial_W_F_given_AP', ['A', 'P']), ('partial_W_F_given_AP_Zpop_Zemp', ['A', 'P', 'logZpop', 'logZemp'])):
        f = lambda d, Cc=Cc: pcorr(d.W.to_numpy(), d.F.to_numpy(), [d[c].to_numpy() for c in Cc])
        out[nm] = {'est': f(O), 'ci95': boot(f, 2000)}
    cols = ['F', 'A', 'P', 'logZpop', 'logZemp']; b = fe_beta(O, cols); bc = boot(lambda d: fe_beta(d, cols), 1000)
    out['dongFE_std_beta'] = {n: {'est': float(b[j]), 'ci95': [bc[0][j], bc[1][j]]} for j, n in enumerate(cols)}
    out['partial_by_category'] = {}
    for c in S.CATS:
        dd = O.dropna(subset=[f'F_{c}']).reset_index(drop=True)
        out['partial_by_category'][c] = {'n': int(len(dd)), 'est': pcorr(dd.W.to_numpy(), dd[f'F_{c}'].to_numpy(), [dd[x].to_numpy() for x in ['A', 'P', 'logZpop', 'logZemp']])}
    (OUT / 'a04_mechanism_summary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8'); print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main(int(sys.argv[1]))
