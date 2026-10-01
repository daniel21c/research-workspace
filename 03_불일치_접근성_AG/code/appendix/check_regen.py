# -*- coding: utf-8 -*-
"""code/appendix/c1~c3이 다시 만든 산출(results/_cache/appendix_regen/)을 원고가 인용하는 원 사본(results/appendix/)과 대조한다.
바이트 SHA-256이 같으면 'identical'. 실행 시간(seconds)이 기록된 파일은 그 칸만 빼고 나머지 값을 전부 비교한다.
실행: python code/appendix/check_regen.py     출력: results/appendix/regeneration_check.json
"""
import hashlib
import json
from pathlib import Path

import pandas as pd

AG = Path(__file__).resolve().parents[1].parent; A = AG / 'results' / 'appendix'; R = AG / 'results' / '_cache' / 'appendix_regen'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmp_json(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k == 'seconds':
                continue
            out += cmp_json(a.get(k), b.get(k), f'{path}.{k}')
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += cmp_json(x, y, f'{path}[{i}]')
    elif a != b:
        out.append({'key': path, 'original': a, 'regenerated': b})
    return out


def main():
    rows = []
    for y in (2020, 2025):
        o, n = A / f'constrained_paths_moves_{y}.csv', R / f'constrained_{y}' / 'moves.csv'
        rows.append({'file': o.name, 'sha_original': sha(o), 'sha_regenerated': sha(n), 'identical': sha(o) == sha(n)})
        o, n = A / f'constrained_paths_summary_{y}.json', R / f'constrained_{y}' / 'summary.json'
        d = cmp_json(json.loads(o.read_text('utf-8')), json.loads(n.read_text('utf-8')))
        rows.append({'file': o.name, 'sha_original': sha(o), 'sha_regenerated': sha(n), 'identical': sha(o) == sha(n), 'differences_except_seconds': d, 'values_identical_except_seconds': not d})
    o, n = A / 'plan_level_association.json', R / 'plan_level_association.json'
    rows.append({'file': o.name, 'sha_original': sha(o), 'sha_regenerated': sha(n), 'identical': sha(o) == sha(n),
                 'differences': cmp_json(json.loads(o.read_text('utf-8')), json.loads(n.read_text('utf-8')))})
    for y, seeds in ((2025, (20261101, 20261102)), (2020, (20261201, 20261202))):
        for s in seeds:
            f = f'e13b_{y}_SIZE20_{s}_stagnant_search.csv'; o, n = A / f, R / f
            a, b = pd.read_csv(o).drop(columns='seconds'), pd.read_csv(n).drop(columns='seconds')
            rows.append({'file': f, 'sha_original': sha(o), 'sha_regenerated': sha(n), 'identical': sha(o) == sha(n), 'values_identical_except_seconds': bool(a.equals(b))})
    (A / 'regeneration_check.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    for r in rows:
        print(r['file'], 'identical' if r['identical'] else ('values identical except seconds' if r.get('values_identical_except_seconds') else 'DIFFERENT'))


if __name__ == '__main__':
    main()
