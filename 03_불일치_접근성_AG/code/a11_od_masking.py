# -*- coding: utf-8 -*-
"""OD 비공개(이동인구 3명 미만 '*') 규모 — 원고 5.4 한계 문장의 근거(2026-10-02 감사 S3-7 재확인 대응).
AG가 실제로 쓰는 필터 후 자료(코어 od_daily: 1월, 도착 09–20시, HW·WH 제외, 전 요일, 서울 내부)의 행 수·비공개 행 수로 계산한다.
 - 비공개 행 비율 = Σ n_masked / Σ n_rows
 - 통행량 상한 = c·Σ n_masked / (Σ flow + c·Σ n_masked), c = 2.99(3명 미만의 최댓값), 참고로 c = 1.5
실행: python code/a11_od_masking.py     출력: results/appendix/od_masking.json
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent; AG = HERE.parent; ROOT = AG.parent
sys.path.insert(0, str(HERE)); import study as S  # noqa: E402


def main():
    out = {}
    for y in (2020, 2025):
        od = S.input_paths(ROOT, y)['od']; d = pd.read_parquet(od, columns=['flow', 'n_rows', 'n_masked'])
        rows, masked, flow = int(d.n_rows.sum()), int(d.n_masked.sum()), float(d.flow.sum())
        out[str(y)] = {'source': str(od.relative_to(ROOT)).replace('\\', '/'), 'rows': rows, 'masked_rows': masked, 'flow': flow, 'masked_row_share': masked / rows,
                       'flow_upper_share_c2.99': 2.99 * masked / (flow + 2.99 * masked), 'flow_share_c1.5': 1.5 * masked / (flow + 1.5 * masked)}
    (AG / 'results' / 'appendix' / 'od_masking.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
