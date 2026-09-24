"""식료품 소매 인허가 4종 subtype: 축산판매업·식품판매업(기타)·즉석판매제조가공업·제과점영업."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '식료품소매', 'category_group': '상업생활편의',
    'sources': [src('livestock_retail', subtype='축산판매업'), src('other_food_retailers', subtype='식품판매업(기타)'),
                src('instant_food_processors', subtype='즉석판매제조가공업'), src('bakeries', subtype='제과점영업')],
    'size_map': {'sz_area_m2': '소재지면적', 'sz_facility_total_m2': '시설총규모', 'sz_workers': ['남성종사자수', '여성종사자수']},
    'attr_map': {'attr_business_type': '업태구분명', 'attr_hygiene_type': '위생업태명', 'attr_livestock_task': '축산업무구분명'},
    'geocode': True, 'geocode_max': 3000,
    'notes': ['식품위생 계열 원천(식품판매업(기타)·즉석판매·제과점)에는 인허가취소일·휴업일·전출 상태가 없고 영업/폐업만 있음.',
              '즉석판매제조가공업에는 반찬·떡·정육가공 등 제조판매가 섞임(attr_business_type 참고).'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
