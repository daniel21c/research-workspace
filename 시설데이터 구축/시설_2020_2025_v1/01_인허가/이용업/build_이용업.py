"""이용업 2020_01·2025_01 역산(subtype=업태구분명)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

def subtype(df):
    return df['업태구분명'].fillna('').replace('', '업태미상')

CFG = {
    'type': '이용업', 'category_group': '상업생활편의', 'sources': [src('barber_shops')], 'subtype_fn': subtype,
    'size_map': {'sz_area_m2': '소재지면적', 'sz_seats': '좌석수'}, 'attr_map': {'attr_hygiene_type': '위생업태명'},
    'geocode': True, 'geocode_max': 3000,
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
