"""석유판매업 중 업태구분명=주유소 만 추출(2020_01·2025_01 역산)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '주유소', 'category_group': '상업생활편의', 'sources': [src('oil_retailers')],
    'filter_fn': lambda df: df['업태구분명'].fillna('') == '주유소', 'filter_desc': '업태구분명 == 주유소 (일반판매소·용제판매소·항공유판매소 제외)',
    'subtype_fn': lambda df: df['업태구분명'].fillna(''),
    'size_map': {'sz_area_m2': '소재지면적'}, 'attr_map': {'attr_business_type': '업태구분명'},
    'geocode': True,
    'official_note': '한국석유공사 Opinet 주유소 현황 대조 미실시',
    'notes': ['LPG 충전소는 석유판매업이 아니라 포함되지 않음.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
