"""안전상비의약품 판매업소(편의점 등) 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '안전상비의약품판매업소', 'category_group': '보건의료', 'sources': [src('over_the_counter_medicine_stores', subtype='안전상비의약품판매업소')],
    'size_map': {'sz_area_m2': '판매점영업면적'}, 'geocode': True,
    'official_note': '보건복지부 안전상비의약품 판매업소 현황 대조 미실시(원자료 미확보)',
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
