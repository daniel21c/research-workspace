"""범위 제한 규칙(scope_flag / in_scope)을 두 시점에 똑같이 적용해 11_신뢰도_승격/<시설>/facilities_*.parquet/.csv 작성.
 - 식료품소매: in_scope = facility_subtype ∈ {즉석판매제조가공업, 제과점영업} (서울시 식품위생업 현황과 같은 정의)
 - 대규모점포: in_scope = 점포구분=대규모점포 & 업태 ∈ {대형마트, 백화점, 쇼핑센터, 전문점} (서울시 유통업체현황 주요 4업태)
 - 주유소    : in_scope = 현재 영업상태가 '휴업'이 아닌 행 (휴업일자 없는 장기휴업 → 한국석유관리원·석유공사 '영업 주유소'와 같은 정의)
기존 파일(좌표 보완본)이 있으면 그 위에 열만 추가, 없으면 01_인허가 원 빌드 + gu 열."""
import sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; V1 = next(p for p in Path(__file__).resolve().parents if (p / '01_인허가').exists()); sys.path.insert(0, str(HERE))
from gu import add_gu
FAC = sys.argv[1]; OUT = V1 / '11_신뢰도_승격' / FAC
def rule(d):
    if FAC == '식료품소매':
        ins = d.facility_subtype.isin(['즉석판매제조가공업', '제과점영업'])
        flag = ins.map({True: '공식대조범위(즉석판매·제과점)', False: '범위밖(' }) + (~ins).map({True: '', False: ''})
        flag = flag.where(ins, '범위밖(' + d.facility_subtype + ')')
    elif FAC == '대규모점포':
        ins = (d.facility_subtype == '대규모점포') & d.attr_business_type.isin(['대형마트', '백화점', '쇼핑센터', '전문점'])
        flag = pd.Series('대규모점포_기타업태(' + d.attr_business_type.fillna('NA') + ')', index=d.index)
        flag[ins] = '주요4업태(' + d.attr_business_type[ins] + ')'
        flag[d.facility_subtype == '준대규모점포'] = '준대규모점포(SSM 등)'; flag[d.facility_subtype == '점포구분미상'] = '점포구분미상(옛 기록)'
    elif FAC == '주유소':
        ins = ~d.src_status.fillna('').str.contains('휴업')
        flag = ins.map({True: '영업(현재 휴업 아님)', False: '현재 휴업(휴업일자 없음) — 제외'})
    return ins, flag
for k in ('2020_01', '2025_01'):
    p = OUT / f'facilities_{FAC}_{k}.parquet'
    d = pd.read_parquet(p) if p.exists() else add_gu(pd.read_parquet(V1 / '01_인허가' / FAC / f'facilities_{FAC}_{k}.parquet'))
    if 'coord_stage' not in d:
        d['coord_stage'] = d.coord_method.map(lambda m: 'source' if m == 'source' else ('unresolved' if m == 'unresolved' else 'geocode_build'))
    d['in_scope'], d['scope_flag'] = rule(d)
    d.to_parquet(p, index=False); d.to_csv(OUT / f'facilities_{FAC}_{k}.csv', index=False, encoding='utf-8-sig')
    print(FAC, k, len(d), d.scope_flag.value_counts().to_dict())
