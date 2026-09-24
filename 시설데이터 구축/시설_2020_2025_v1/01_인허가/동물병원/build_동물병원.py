"""동물병원 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '동물병원', 'category_group': '상업생활편의', 'sources': [src('animal_hospitals', subtype='동물병원')],
    'size_map': {'sz_area_m2': '소재지면적'}, 'geocode': True,
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
