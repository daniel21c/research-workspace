"""주유소(석유판매업 업태=주유소)를 원 빌드와 같은 규칙(lic_common.process_file + fix_transfers + 원천중복 제거)으로
여러 기준일(연말)에 역산해, 공식 발표값이 있는 연도(2021·2022·2023·2025 말)와 비교. 원본은 읽기만 함.
또한 '휴업 상태(현재) 제외' 민감도 버전도 계산."""
import sys, json
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists())
sys.path.insert(0, str(V1 / '01_인허가/_common')); sys.path.insert(0, str(V1 / '11_신뢰도_승격/_shared'))
import lic_common as L
from gu import ORG2GU, gu_from_address
DATES = {f'{y}': pd.Timestamp(f'{y}-12-31') for y in range(2018, 2026)}
L.SNAPS = DATES
raw = V1 / '01_인허가/주유소/raw/oil_retailers_seoul_OA-16110.csv'
keep = {'개방자치단체코드', '관리번호', '사업장명', '도로명주소', '지번주소', '영업상태명', '상세영업상태명', '업태구분명', '최종수정일자'}
df, st = L.process_file(raw, 'oil_retailers', keep)
df, tinfo = L.fix_transfers(df)
df = df[df['업태구분명'].fillna('') == '주유소'].copy()
df['address'] = df['도로명주소'].where(df['도로명주소'].fillna('').str.len() > 0, df['지번주소'])
df['_dupkey'] = df['사업장명'].fillna('').str.replace(r'\s+', '', regex=True) + '|' + df['address'].fillna('').str.replace(r'\s+', '', regex=True) + '|' + df['_lic'].dt.strftime('%Y-%m-%d').fillna('')
out = {}
for y in DATES:
    s = df[df['_active_' + y]].sort_values(['_dupkey', '관리번호'])
    s = s[~s.duplicated('_dupkey', keep='first')]
    out[y] = {'n': int(len(s)), 'n_excl_current_hyueop': int((~s['영업상태명'].fillna('').str.contains('휴업')).sum()),
              'current_status': s['영업상태명'].value_counts().to_dict()}
OFFICIAL = {'2018': (508, '에너지신문 2023-03(한국석유관리원): 2022년 444개 = 2018 대비 -12.6% → 역산 ≈508 (추정)'),
            '2021': (470, '에너지신문 2023-03 기사(한국석유관리원 영업 주유소 현황): 2021년 470개'),
            '2022': (444, '에너지신문 2023-03 기사(한국석유관리원): 2022년 말 444개'),
            '2023': (436, '데이터솜 2024-01 기사(한국석유관리원 2019~2023 영업 주유소 현황): 2023-12-31 436개'),
            '2025': (412, '한국석유공사_지역별 주유소 수_20251231 (data.go.kr 15038480, 파일 기준일 2025-12-31)')}
rows = []
for y, v in out.items():
    o = OFFICIAL.get(y)
    rows.append({'year_end': y, 'built': v['n'], 'built_excl_current_hyueop': v['n_excl_current_hyueop'],
                 'official': o[0] if o else None, 'official_source': o[1] if o else '',
                 'diff_pct': round(100 * (v['n'] - o[0]) / o[0], 2) if o else None,
                 'diff_pct_excl_hyueop': round(100 * (v['n_excl_current_hyueop'] - o[0]) / o[0], 2) if o else None})
r = pd.DataFrame(rows); r.to_csv(HERE.parent / 'official_compare_주유소.csv', index=False, encoding='utf-8-sig')
print(r.to_string()); print(json.dumps({k: v['current_status'] for k, v in out.items()}, ensure_ascii=False))

# ---- 참고: 서울시 주유소 현황(OA-22251, 기준일 불명, 포털 갱신 2023-12-22) 구별 분포 비교
ref = pd.read_csv(HERE.parent / 'raw/seoul_OA-22251_주유소현황.csv', encoding='cp949')
rg = ref['자치구명'].str.strip().value_counts()
import numpy as np
res = {}
for y in ('2021', '2022', '2023'):
    s = df[df['_active_' + y]].sort_values(['_dupkey', '관리번호']); s = s[~s.duplicated('_dupkey', keep='first')]
    s = s[~s['영업상태명'].fillna('').str.contains('휴업')]
    g = gu_from_address(s['address']).fillna(s['개방자치단체코드'].map(ORG2GU)).value_counts()
    idx = sorted(set(rg.index) | set(g.index)); a = g.reindex(idx, fill_value=0); b = rg.reindex(idx, fill_value=0)
    res[y] = {'built_excl_hyueop': int(a.sum()), 'ref_total': int(b.sum()), 'gu_r': round(float(np.corrcoef(a, b)[0, 1]), 4),
              'gu_max_abs_diff': int((a - b).abs().max()), 'gu_max_abs_diff_gu': (a - b).abs().idxmax()}
    if y == '2021':
        pd.DataFrame({'gu': idx, 'built_2021_excl_hyueop': a.values, 'seoul_OA22251_ref': b.values}).to_csv(HERE.parent / 'gu_compare_주유소_OA22251.csv', index=False, encoding='utf-8-sig')
print(json.dumps(res, ensure_ascii=False))
json.dump({'multi_date': rows, 'gu_ref_OA22251': res}, open(HERE.parent / 'compare_summary_주유소.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
