"""의원(의원·치과의원·한의원 + 보건소·보건지소·조산원 subtype) 2020_01·2025_01 역산. 박사논문 주 원천."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src
import hira_compare

def subtype(df):
    s = df['의료기관종별명'].fillna('').where(df['의료기관종별명'].fillna('') != '', df['업태구분명'].fillna(''))
    return s.replace('', '미상')

CFG = {
    'type': '의원', 'category_group': '보건의료', 'sources': [src('clinics')], 'subtype_fn': subtype,
    'extra_keep': ['의료기관종별명'],
    'size_map': {'sz_medical_staff': '의료인수', 'sz_beds': '병상수', 'sz_inpatient_rooms': '입원실수', 'sz_floor_area_m2': '총면적'},
    'attr_map': {'attr_business_type': '업태구분명', 'dept_current_codes': '진료과목내용', 'dept_current_names': '진료과목내용명'},
    'geocode': True,
    'official_fn': lambda o: hira_compare.official(o, ['의원', '치과의원', '한의원', '보건소', '보건지소', '조산원']),
    'notes': ['sz_*·dept_current_* 는 현재(원천 기준일) 기록값이며 과거 시점 값이 아님.',
              '보건소·보건지소·조산원은 subtype 으로 분리(분석 시 의원 3종만 사용 권장).'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out})
