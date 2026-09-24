# -*- coding: utf-8 -*-
"""안전상비의약품판매업소: 독립 공식 통계 부재 → 좌표·구별 분포·민감도만 점검.
민감도: V0 기본 / V1 행정처리 종료(flag_admin_end: 취소·말소 등) 제외 / V2 현재 휴업 제외 / V3 이름+주소 중복 제거."""
import sys, json, warnings; warnings.filterwarnings('ignore')
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); import cmp_lib as C
sys.path.insert(0, str(C.LIC / '_common')); from lic_common import address_key
OUT = Path(__file__).resolve().parents[1]; summ = {}; rows = []
for y in ('2020', '2025'):
    d = C.load('안전상비의약품판매업소', y); d['ak'] = d.address.map(address_key)
    fae = d.flag_admin_end.astype(bool)
    end = pd.to_datetime(d.end_date, errors='coerce')
    summ[y] = dict(cov=C.coverage(d), V0=len(d), V1_excl_admin_end=int((~fae).sum()), V2_excl_current_suspended=int((d.src_status != '휴업').sum()),
                   V3_dedup_name_addr=len(d.drop_duplicates(['name', 'ak'])),
                   admin_end_year=end[fae].dt.year.value_counts().sort_index().to_dict(), status=d.src_status.value_counts().to_dict())
    for gu, n in d.gu.value_counts().items(): rows.append(dict(snapshot=f'{y}_01', gu=gu, ours=int(n)))
summ['note'] = ('서울 안전상비의약품 판매업소 수에 대한 독립 공식 통계(복지부·식약처·서울시 KOSIS/시정통계)는 2019-12·2024-12 기준으로 찾지 못함. '
                '서울시 「의약품 제조 및 판매업 현황」(KOSIS DT_201004_O110007_2015)에는 약국·약업사·매약상 등만 있고 안전상비의약품 판매업소 항목이 없음. '
                '서울시 누리집 게시 목록(2022-08-24, 2023-12-31 기준 엑셀)은 창 밖이며 자치구 등록대장(=인허가와 같은 원천)이라 독립 대조가 아님.')
(OUT / 'summary_안전상비의약품판매업소.json').write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
pd.DataFrame(rows).pivot(index='gu', columns='snapshot', values='ours').reset_index().assign(official='없음').to_csv(
    OUT / 'official_compare_안전상비의약품판매업소.csv', index=False, encoding='utf-8-sig')
print(json.dumps({k: v for k, v in summ.items()}, ensure_ascii=False, default=str))
