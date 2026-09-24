"""약국 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src
import hira_compare
CFG = {
    'type': '약국', 'category_group': '보건의료', 'sources': [src('pharmacies', subtype='약국')],
    'size_map': {'sz_area_m2': '약국영업면적'}, 'geocode': True,
    'official_fn': lambda o: hira_compare.official(o, ['약국']),
    'notes': ['sz_area_m2 는 현재 기록값.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
