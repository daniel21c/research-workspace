"""대규모점포(대규모점포/준대규모점포 × 업태) 2020_01·2025_01 역산."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

def subtype(df):
    return df['점포구분명'].fillna('').replace('', '점포구분미상')

CFG = {
    'type': '대규모점포', 'category_group': '상업생활편의', 'sources': [src('large_scale_retail_stores')], 'subtype_fn': subtype,
    'size_map': {'sz_area_m2': '소재지면적'},
    'attr_map': {'attr_business_type': '업태구분명', 'attr_store_class': '점포구분명'},
    'geocode': True,
    'notes': ['facility_subtype=점포구분명(대규모점포/준대규모점포/점포구분미상), 업태(대형마트·백화점·쇼핑센터·복합쇼핑몰·전문점·시장·그 밖의 대규모점포·구분없음)는 attr_business_type.',
              '준대규모점포는 대부분 SSM(기업형 슈퍼마켓).'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
