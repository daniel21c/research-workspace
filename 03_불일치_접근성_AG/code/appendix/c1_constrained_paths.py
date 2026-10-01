# -*- coding: utf-8 -*-
"""부록 Table A.3 1·2행(인구·모양 제약 아래 모듈성 재배정, IFR을 가장 많이 올리는 재배정)의 원 산출을 다시 만든다.
원 산출: 2026-09-29 18:38 `study.py main()` 실행(Codex)의 `results/{연도}/summary.json`·`moves.csv` → AG `results/appendix/constrained_paths_summary_{연도}.json`·`constrained_paths_moves_{연도}.csv`(바이트 사본).
study.main()은 설계 계약 파일(design_contract.json, 보관 폴더)이 있어야 돌므로, 같은 계산 단계(make_paths → Accessibility → evaluate)와 같은 요약 규칙을 여기서 그대로 부른다.
입력 잠금·설계 계약 확인은 하지 않는다(입력 SHA는 a01~a04와 같은 study.input_paths로 정해진다).
실행: python code/appendix/c1_constrained_paths.py 2025   (2020도 같음)
출력: results/_cache/appendix_regen/constrained_{연도}/summary.json·moves.csv (원 사본과의 대조는 code/appendix/check_regen.py)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; AG = HERE.parents[1]; ROOT = AG.parent
sys.path.insert(0, str(AG / 'code')); import study as S  # noqa: E402


def main(year):
    t0 = time.time(); out = AG / 'results' / '_cache' / 'appendix_regen' / f'constrained_{year}'; out.mkdir(parents=True, exist_ok=True)
    paths = S.input_paths(ROOT, year); D = S.load(ROOT, year, paths)
    states, labels, moved, affs, pmeta = S.make_paths(D, out)
    ev = S.Accessibility(D, paths, out); ev.verify_reassigned(labels[pmeta['K_mod']]); R, ameta = ev.evaluate(states, labels, moved, affs, out)
    summary = dict(year=year, **pmeta, **ameta, OD_total=D['FT'], OD_self=float(np.trace(D['F'])), IFR_initial=S.ifr(D, D['LZ']), MOD_end=R[R.strategy == 'MOD'].iloc[-1].to_dict(),
                   IFR_end=R[R.strategy == 'IFR'].iloc[-1].to_dict(), MOD_min=R[R.strategy == 'MOD'].sort_values(['dL_unique', 'k']).iloc[0].to_dict(), input_hashes_unchanged=True, seconds=time.time() - t0)
    S.js(out / 'summary.json', summary); print(json.dumps({k: summary[k] for k in ('MOD_end', 'IFR_end')}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main(int(sys.argv[1]))
