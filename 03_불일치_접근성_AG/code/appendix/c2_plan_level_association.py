# -*- coding: utf-8 -*-
"""부록 Table A.3 3행(대안 지도 1000장 안에서 IFR과 L의 계획 단위 Spearman 상관, 모양 통제)의 원 산출을 다시 만든다.
원 코드: 보관 `explore/v3/7cat/appendix_e17_plan_level_association.py`(2026-09-29). 원 입력 e15_{연도}_plans_7cat.csv(대안 지도 7범주 재평가)와
e13 표본 라벨은 AG의 a03_ensemble_plans.csv(L·COV15·MAI15·IFR, 2002행 동일)와 a02 표본 라벨(2026-09-28 생성본과 동일, results/a02_reproduction_check.json)로 바꿨다.
계산·순서·시드(20260929, 사슬 안 연속 50개 블록 재표집 2000회)는 원 코드 그대로다.
실행: python code/appendix/c2_plan_level_association.py
출력: results/_cache/appendix_regen/plan_level_association.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent; AG = HERE.parents[1]; ROOT = AG.parent; RES = AG / 'results'
sys.path.insert(0, str(AG / 'code')); import study as S  # noqa: E402
OUT = RES / '_cache' / 'appendix_regen'; rng = np.random.default_rng(20260929)


def pres(v, C):
    X = np.column_stack([np.ones(len(v))] + [rankdata(c) for c in C]); r = rankdata(v); return r - X @ np.linalg.lstsq(X, r, rcond=None)[0]


def pc(x, y, C):
    return float(np.corrcoef(pres(x, C), pres(y, C))[0, 1]) if C else float(np.corrcoef(rankdata(x), rankdata(y))[0, 1])


def main():
    OUT.mkdir(parents=True, exist_ok=True); res = {}
    for y in (2025, 2020):
        paths = S.input_paths(ROOT, y); D = S.load(ROOT, y, paths)
        P = pd.read_csv(RES / str(y) / 'a03_ensemble_plans.csv').rename(columns={'L': 'L7', 'COV15': 'COV15_7', 'MAI15': 'MAI15_7'})
        P = P[P.plan.str.startswith('E')].sort_values(['seed', 'plan']).reset_index(drop=True)
        seeds = sorted(P.seed.unique()); pp_m, blen = [], []
        for s in seeds:
            L = np.load(RES / str(y) / f'a02_ensemble_{s}_labels.npz', allow_pickle=True)
            for i in range(500):
                lab = L[f'E{i:03d}'].astype(np.int64); zs = np.unique(lab); mem = [np.flatnonzero(lab == z) for z in zs]
                pp_m.append(np.mean([S.pp(D, m) for m in mem])); blen.append(sum(D['per'][m].sum() - D['S'][np.ix_(m, m)].sum() for m in mem) / 1e3)
        P['pp_mean'] = pp_m; P['boundary_km'] = blen
        out = {}
        for m, lab in (('L7', '누락 인구(낮을수록 좋음)'), ('COV15_7', 'COV'), ('MAI15_7', 'MAI')):
            for cn, C in (('raw', []), ('shape', ['pp_mean', 'boundary_km'])):
                est = pc(P.IFR.to_numpy(), P[m].to_numpy(), [P[c].to_numpy() for c in C])
                blocks = [np.arange(j, j + 50) for j in range(0, len(P), 50)]; bs = []
                for _ in range(2000):
                    idx = np.concatenate([blocks[b] for b in rng.integers(len(blocks), size=len(blocks))]); d = P.iloc[idx]
                    bs.append(pc(d.IFR.to_numpy(), d[m].to_numpy(), [d[c].to_numpy() for c in C]))
                out[f'{m}|{cn}'] = {'label': lab, 'rho': est, 'ci95': [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]}
        res[y] = out; print(y, json.dumps(out, ensure_ascii=False))
    (OUT / 'plan_level_association.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
