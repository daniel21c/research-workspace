"""휴게음식점 2020_01·2025_01 역산(대용량: 청크 처리, 지오코딩 안 함)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

def subtype(df):
    return df['업태구분명'].fillna('').replace('', '업태미상')

CFG = {
    'type': '휴게음식점', 'category_group': '상업생활편의', 'sources': [src('rest_cafes')], 'subtype_fn': subtype,
    'size_map': {'sz_area_m2': '소재지면적', 'sz_facility_total_m2': '시설총규모', 'sz_workers': ['남성종사자수', '여성종사자수']},
    'attr_map': {'attr_hygiene_type': '위생업태명', 'attr_multi_use': '다중이용업소여부'},
    'geocode': False,
    'notes': ['facility_subtype=업태구분명. 대용량 업종이라 좌표 없는 행은 지오코딩하지 않고 unresolved 로 둠.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
