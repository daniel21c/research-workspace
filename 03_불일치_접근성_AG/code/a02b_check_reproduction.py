# -*- coding: utf-8 -*-
"""a02가 2026-09-28 생성 앙상블(explore/v3/e13_*_labels.npz, 현재 보관 폴더)과 같은 표본을 다시 만들었는지 대조한다.
실행: python code/a02b_check_reproduction.py <e13 labels가 있는 폴더>     출력: results/a02_reproduction_check.json
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

AG = Path(__file__).resolve().parents[1]; RES = AG / 'results'
SEEDS = {2025: (20261101, 20261102), 2020: (20261201, 20261202)}


def main(ref):
    ref = Path(ref); out = {'reference_dir': ref.as_posix(), 'chains': {}}
    for y, ss in SEEDS.items():
        for s in ss:
            a = np.load(RES / str(y) / f'a02_ensemble_{s}_labels.npz'); b = np.load(ref / f'e13_{y}_SIZE20_{s}_labels.npz', allow_pickle=True)
            same = all(np.array_equal(a[f'E{i:03d}'], b[f'E{i:03d}']) for i in range(500)) and np.array_equal(a['LZ'], b['LZ']) and np.array_equal(a['dongs'], b['dongs'])
            out['chains'][f'{y}_{s}'] = {'identical_500_samples': bool(same), 'reference_sha256': hashlib.sha256((ref / f'e13_{y}_SIZE20_{s}_labels.npz').read_bytes()).hexdigest()}
    out['all_identical'] = all(v['identical_500_samples'] for v in out['chains'].values())
    (RES / 'a02_reproduction_check.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out))


if __name__ == '__main__':
    main(sys.argv[1])
