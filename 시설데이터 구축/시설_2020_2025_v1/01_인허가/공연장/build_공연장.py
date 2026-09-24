"""공연장 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '공연장', 'category_group': '문화체육녹지', 'sources': [src('performance_halls', subtype='공연장')],
    'size_map': {'sz_area_m2': '시설면적', 'sz_scale_raw': '시설규모', 'sz_floors_total': '총층수'},
    'attr_map': {'attr_building_use': '건물용도명', 'attr_culture_business': '문화사업자구분명'},
    'geocode': True,
    'official_note': '문화체육관광부 전국 문화기반시설 총람(공연장) 대조 미실시',
    'notes': ['sz_scale_raw(시설규모)는 대부분 0이고 단위 불명(원자료 그대로).'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
