"""체육시설업(신고·등록) 7종 subtype: 체력단련장·체육도장·수영장·골프연습장·당구장·종합체육시설·빙상장."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src

CFG = {
    'type': '체육시설업', 'category_group': '문화체육녹지',
    'sources': [src('fitness_centers', subtype='체력단련장'), src('martial_arts_dojo', subtype='체육도장'),
                src('swimming_pools', subtype='수영장'), src('golf_practice_ranges', subtype='골프연습장'),
                src('billiard_halls', subtype='당구장'), src('comprehensive_sports_facilities', subtype='종합체육시설'),
                src('ice_rinks', subtype='빙상장')],
    'size_map': {'sz_area_m2': '소재지면적', 'sz_building_floor_area_m2': '건축물연면적', 'sz_instructors': '지도자수', 'sz_members': '회원모집총인원'},
    'attr_map': {'attr_business_type': '업태구분명', 'attr_public_private': '공사립구분명', 'attr_culture_sports_type': '문화체육업종명'},
    'geocode': True,
    'notes': ['sz_area_m2(소재지면적)는 체력단련장 원천에만 있음. 규모는 현재 기록값.', '체육도장 업태(태권도·유도 등)는 attr_business_type.'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'].get('removed_from_active'), qa['geocoding'])
