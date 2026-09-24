"""산후조리업 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '산후조리업', 'category_group': '보건의료', 'sources': [src('postpartum_care', subtype='산후조리원')],
    'size_map': {'sz_capacity_mothers': '임산부정원수', 'sz_capacity_infants': '영유아정원수', 'sz_nurses': '간호사수',
                 'sz_nurse_aides': '간호조무사수', 'sz_room_area_mothers_m2': '임산부실면적'},
    'geocode': True,
    'official_note': '보건복지부 산후조리원 현황(시도별) 대조 미실시(원자료 미확보)',
    'notes': ['정원·인력은 현재 기록값.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
