"""병원급(종합병원·병원·요양병원·치과병원·한방병원·정신병원) 2020_01·2025_01 역산. file.localdata 판(병상·의료인수 포함) 사용."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))
from lic_common import build
from sources import src
import hira_compare

def subtype(df):
    s = df['의료기관종별명'].fillna('').where(df['의료기관종별명'].fillna('') != '', df['업태구분명'].fillna(''))
    return s.str.replace(r'^요양병원.*$', '요양병원', regex=True).replace('', '미상')

S = src('hospitals', kind='localdata'); S['dataset'] = '지방행정 인허가 병원 (file.localdata.go.kr hospitals, 서울 6110000_ALL; data.go.kr 15045025)'
CFG = {
    'type': '병원급', 'category_group': '보건의료', 'sources': [S], 'subtype_fn': subtype,
    'extra_keep': ['의료기관종별명'],
    'size_map': {'sz_beds': '병상수', 'sz_medical_staff': '의료인수', 'sz_inpatient_rooms': '입원실수',
                 'sz_floor_area_m2': '총면적', 'sz_site_area_m2': '소재지면적'},
    'attr_map': {'attr_kind_detail': '의료기관종별명', 'dept_current_codes': '진료과목내용', 'dept_current_names': '진료과목내용명'},
    'geocode': True,
    'official_fn': lambda o: hira_compare.official(o, ['종합병원', '병원', '요양병원', '치과병원', '한방병원', '정신병원']),
    'notes': ['sz_*·dept_current_* 는 현재(원천 기준일) 기록값이며 과거 시점 값이 아님(2019 병상수 아님).',
              '요양병원(일반요양병원/노인병원/장애인의료재활시설)은 subtype=요양병원, 세부는 attr_kind_detail.',
              '상급종합병원은 인허가상 종합병원으로 등록됨(HIRA 대조 시 상급종합+종합 합산).'],
}
if __name__ == '__main__':
    out, qa = build(CFG, HERE)
    print({k: qa[k]['n_final'] for k in out}, {k: qa[k]['coord_rate'] for k in out}, qa['transfer_fix'])
