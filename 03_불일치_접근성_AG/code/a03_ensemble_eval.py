# -*- coding: utf-8 -*-
"""결과 3 평가: 대안 생활권 지도 1,000장(연도별 두 사슬 × 500) 속에서 공식 생활권의 경계 내 시설 누락 순위.

각 표본을 study.Accessibility로 평가(7범주, 15분 보행). 순위 통계: r_greater = 표본 L > 공식 L + 0.5명 비율.
사슬 표본은 독립이 아니므로 자기상관·유효표본수(Geyer)와 10개 배치 평균을 함께 보고한다. 지시변수가 상수면 배치 구간은 계산하지 않는다.
실행: python code/a03_ensemble_eval.py 2025     출력: results/{연도}/a03_ensemble_plans.csv, a03_ensemble_summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402
from a02_ensemble import SEEDS  # noqa: E402
TOL = 0.5


def rank_stats(x, x0, tol=TOL):
    x = np.asarray(x, float); return float(np.mean(x < x0 - tol)), float(np.mean(np.abs(x - x0) <= tol)), float(np.mean(x > x0 + tol))


def batch_means(ind, n=10):
    ind = np.asarray(ind, float)
    if np.all(ind == ind[0]):
        return {'mean': float(ind.mean()), 'se': None, 'status': 'constant indicator; not estimable'}
    mu = np.array([b.mean() for b in np.array_split(ind, n)]); se = float(mu.std(ddof=1) / np.sqrt(n))
    return {'mean': float(ind.mean()), 'se': se, 'lo': float(ind.mean() - 1.96 * se), 'hi': float(ind.mean() + 1.96 * se), 'status': 'batch means'}


def acf(x, lag):
    x = np.asarray(x, float) - np.mean(x); d = (x * x).sum(); return float((x[:-lag] * x[lag:]).sum() / d) if d > 0 else np.nan


def ess(x):
    x = np.asarray(x, float); n = len(x)
    if np.all(x == x[0]):
        return np.nan
    rho = [1.0] + [acf(x, l) for l in range(1, n - 1)]; tau = -1.0
    for i in range(0, len(rho) - 1, 2):
        g = rho[i] + rho[i + 1]
        if g <= 0:
            break
        tau += 2 * g
    return float(n / tau) if tau > 0 else np.nan


def zone_sets(lab):
    g = {}
    for i, c in enumerate(lab):
        g.setdefault(c, set()).add(i)
    g = {c: frozenset(v) for c, v in g.items()}; return [g[c] for c in lab]


def main(year):
    out = AG / 'results' / str(year); cache = AG / 'results' / '_cache' / str(year); cache.mkdir(parents=True, exist_ok=True)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths); ev = S.Accessibility(D, paths, cache); cons = S.Constraints(D); rows = []; Z0 = zone_sets(D['LZ'])
    for s in SEEDS[year]:
        L = np.load(out / f'a02_ensemble_{s}_labels.npz'); assert np.array_equal(L['dongs'], D['dongs'])
        for key in ['LZ'] + [f'E{i:03d}' for i in range(500)]:
            lab = L[key].astype(np.int64); mat = ev.matrix(lab); r = mat > 0; assert np.all(~r | ev.rn)
            x = (ev.rn & ~r).any(1); m = ev.metrics(mat)
            rows.append({'seed': s, 'plan': key, 'L': float(ev.p[x].sum()), 'COV15': m['COV15'], 'MAI15': m['MAI15'], 'IFR': S.ifr(D, lab), 'hash': S.chash(lab),
                         'n_dongs_changed_zone': int(sum(a != b for a, b in zip(zone_sets(lab), Z0))),
                         'geometry_constraints_ok': all(cons.check(lab, k) for k in D['kus'])})
    P = pd.DataFrame(rows); P.to_csv(out / 'a03_ensemble_plans.csv', index=False, encoding='utf-8-sig', float_format='%.12g')
    L0 = float(ev.p[ev.x0].sum()); base = P[P.plan == 'LZ'].iloc[0]; assert abs(base.L - L0) < TOL
    E_all = P[P.plan.str.startswith('E')]
    summ = {'year': year, 'L_LZ': L0, 'IFR_LZ': float(base.IFR), 'n_samples': int(len(E_all)), 'n_unique_plans': int(E_all.hash.nunique()),
            'n_greater': int((E_all.L > L0 + TOL).sum()), 'share_greater': float((E_all.L > L0 + TOL).mean()), 'L_median_all': float(E_all.L.median()),
            'L_min_all': float(E_all.L.min()), 'median_minus_LZ': float(E_all.L.median() - L0), 'IFR_share_above_LZ': float((E_all.IFR > base.IFR + 1e-15).mean()),
            'IFR_median_all': float(E_all.IFR.median()), 'median_dongs_changed': float(E_all.n_dongs_changed_zone.median()),
            'all_samples_pass_geometry_constraints': bool(E_all.geometry_constraints_ok.all()), 'seeds': {}}
    for s in SEEDS[year]:
        E = P[(P.seed == s) & P.plan.str.startswith('E')].reset_index(drop=True); ind = (E.L > L0 + TOL).astype(float).to_numpy()
        less, eq, gr = rank_stats(E.L, L0)
        summ['seeds'][str(s)] = {'r_less': less, 'r_equal': eq, 'r_greater': gr, 'batch_means_r_greater': batch_means(ind), 'L_median': float(E.L.median()),
                                 'L_p2.5': float(E.L.quantile(.025)), 'L_p97.5': float(E.L.quantile(.975)), 'L_min': float(E.L.min()), 'L_acf1': acf(E.L, 1), 'L_ESS': ess(E.L),
                                 'COV15_share_above_LZ': float((E.COV15 > base.COV15 + 1e-12).mean()), 'MAI15_share_above_LZ': float((E.MAI15 > base.MAI15 + 1e-12).mean()),
                                 'IFR_share_above_LZ': float((E.IFR > base.IFR + 1e-15).mean())}
    (out / 'a03_ensemble_summary.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
    print(json.dumps(summ, ensure_ascii=False, default=float))


if __name__ == '__main__':
    main(int(sys.argv[1]))
