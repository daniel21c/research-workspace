# -*- coding: utf-8 -*-
"""facility-v1.1 무결성 보정 2 — 인허가 역산 휴업 판정 (2026-09-25). 원인: 01_인허가/_common/lic_common.py todt()가 2027-01-01 이후 날짜를 결측으로 바꿔
휴업종료일자 ≥ 2027인 휴업이 SPEC 규칙(휴업 시작·종료가 모두 있고 시작 ≤ D ≤ 종료면 제외)에서 빠짐.
원천 행을 source_row_id로 다시 확인한 6행(모두 2025_01, 원천 영업상태 '휴업')을 채택본에서 뺀다.
근거 목록: 근거/defect1_suspension_2027.csv (원천 휴업시작·종료일자). 10_신뢰도_상/<시설>/ 채택본에서 해당 행을 뺀다.
이미 빠져 있으면 건너뛴다(다시 실행해도 결과 같음). 원인 코드는 01_인허가/_common/lic_common.py todt(cap=)로 고쳤다."""
import sys
from pathlib import Path
import pandas as pd
ST = Path(__file__).resolve().parent
V1 = ST.parent
ev = pd.read_csv(ST / '근거' / 'defect1_suspension_2027.csv', dtype=str)
log = []
for (fold, snap), g in ev.groupby(['10_folder', 'year_snapshot']):
    src = list((V1 / '10_신뢰도_상' / fold).glob(f'facilities_*_{snap}.parquet')); assert len(src) == 1, src
    d = pd.read_parquet(src[0]); n0 = len(d)
    m = d.facility_id.isin(g.facility_id)
    if m.sum() == 0:
        log.append(dict(folder=fold, snapshot=snap, before=n0, removed=0, after=n0, note='이미 반영됨')); continue
    assert m.sum() == len(g), (fold, snap, m.sum(), len(g))
    d = d[~m].copy()
    out = src[0].parent
    for c in d.columns:
        if d[c].dtype == object or str(d[c].dtype) == 'str': d[c] = d[c].astype('string')
    d.to_parquet(out / src[0].name, index=False)
    d.to_csv(out / src[0].name.replace('.parquet', '.csv'), index=False, encoding='utf-8-sig')
    log.append(dict(folder=fold, snapshot=snap, before=n0, removed=int(m.sum()), after=len(d)))
pd.DataFrame(log).to_csv(ST / 'fix_log_suspension.csv', index=False, encoding='utf-8-sig')
print(pd.DataFrame(log).to_string())
