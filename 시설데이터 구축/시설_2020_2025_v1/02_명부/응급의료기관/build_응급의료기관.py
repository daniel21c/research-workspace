# -*- coding: utf-8 -*-
"""응급의료기관(국립중앙의료원 E-GEN 월별 응급의료기관 현황) 2020_01(2020.01.31 추출)·2025_01(2025.01.31 추출). 기준일 배포본 → grade A.
subtype = 의료기관분류(권역응급의료센터·지역응급의료센터·지역응급의료기관 등). 첨부 2(응급의료기관 외 응급의료시설)도 subtype
'응급의료시설(응급의료기관 외)'로 함께 넣는다(facility_group 열로 구분)."""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import mb
import pandas as pd
import openpyxl, io
import requests

RAW = HERE / 'raw'
TYP = '응급의료기관'
B = 'https://media.nemc.or.kr/file/download_file_encrypt.do'
SRC = {
    '2020_01': dict(files=[('egen_응급의료기관현황_20200131.xlsx', '03ede879c3d254eb0545dbf0f4ce0392', '응급의료기관'),
                           ('egen_응급의료시설_20200131.xlsx', '00c33e5fdca055f3b2e58dcc1b3f09c0', '응급의료시설')],
                    ref='2020-01-31', notice='https://www.e-gen.or.kr/nemc/notice_detail.do?brdctsno=8421',
                    ds='E-GEN 2020년 1월 응급의료기관 및 응급의료기관 외 의료기관(응급의료시설) 현황(2020.01.31 추출)'),
    '2025_01': dict(files=[('egen_응급의료기관현황_20250131.xlsx', '868aaa0f14e3537767809b46c3774264', '응급의료기관'),
                           ('egen_응급의료시설_20250131.xlsx', '82d85b581b0d2d0b0955ffad60236dfb', '응급의료시설')],
                    ref='2025-01-31', notice='https://www.e-gen.or.kr/nemc/notice_detail.do?brdctsno=12881',
                    ds='E-GEN 2025년 1월 응급의료기관 및 응급의료기관 외 의료기관(응급의료시설) 현황(2025.01.31 추출)'),
}
OFF = ('datagokr_15044540_응급의료기관수_시도별_20241231.csv', 'FILE_000000003643851')


def download():
    for s in SRC.values():
        for f, fi, _ in s['files']:
            mb.fetch(B, RAW / f, params=dict(fileitemno=fi), headers={'Referer': 'https://www.e-gen.or.kr/'}, ref_date=s['ref'],
                     note=s['ds'] + ' | 공지 ' + s['notice'])
    S = requests.Session(); S.headers['User-Agent'] = mb.UA
    mb.fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do', RAW / OFF[0], params=dict(atchFileId=OFF[1], fileDetailSn='1'), session=S,
             ref_date='2024-12-31', note='보건복지부 응급의료기관 수_시도별(2018~2024)')


def read(snap):
    out = []
    for f, _, grp in SRC[snap]['files']:
        ws = openpyxl.load_workbook(RAW / f, read_only=True, data_only=True).worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        h = next(i for i, r in enumerate(rows) if r[0] == '번호')
        H = [re.sub(r'\s+', '', str(x or '')) for x in rows[h]]
        C = {k: H.index(k) for k in H if k}
        for i in range(h + 1, len(rows)):
            r = rows[i]
            if not r[C['기관명']] or not str(r[C['지역']] or '').startswith('서울'):
                continue
            out.append(dict(name=mb.clean(r[C['기관명']]), facility_group=grp,
                            facility_subtype=mb.clean(r[C['의료기관분류']]) if grp == '응급의료기관' else '응급의료시설(응급의료기관 외)',
                            sz_hospital_class=mb.clean(r[C['기관분류']]), gu=mb.clean(r[C['시군구']]),
                            address=mb.clean(r[C['기관주소(도로명)']]), sz_beds=r[C['허가병상수']] if '허가병상수' in C else None,
                            source_row_id=f"{f}!{i + 1}"))
    return pd.DataFrame(out)


def official():
    b = (RAW / OFF[0]).read_bytes()
    try:
        t = b.decode('utf-8-sig')
    except UnicodeDecodeError:
        t = b.decode('cp949')
    d = pd.read_csv(io.StringIO(t))
    d = d[d['시도'].str.startswith('서울')]
    return {str(r['연도']): {k: int(r[k]) for k in d.columns[2:]} | {'계': int(sum(r[k] for k in d.columns[2:]))} for _, r in d.iterrows()}


def build():
    download()
    qa = dict(type=TYP, grade='A', note_grade='월별 기준일 배포본(1월 31일 추출)', snapshots={})
    fr = {}
    for snap in ['2020_01', '2025_01']:
        d = read(snap)
        d = mb.geocode_df(d, RAW / 'geocoding')
        fr[snap] = d
        qa['snapshots'][snap] = dict(source_files=[f for f, _, _ in SRC[snap]['files']], source_rows_seoul=len(d))
    a, b, st = mb.assign_ids(fr['2020_01'], fr['2025_01'], 'EMR', extra_key='facility_group')
    qa['facility_id_rule'] = 'mb.assign_ids(명칭+주소키+group, 명칭+주소키, 명칭 유일, 주소키+group 유일, 좌표 50m+명칭 앞4자). 등급(권역/지역) 변경은 같은 id'
    qa['id_matching'] = st
    off = official()
    for snap, d in [('2020_01', a), ('2025_01', b)]:
        s = SRC[snap]
        d = mb.spatial(d)
        d['category_group'] = '보건의료'; d['facility_type'] = TYP; d['grade'] = 'A'
        d['source_org'] = '국립중앙의료원 중앙응급의료센터(E-GEN)'; d['source_dataset'] = s['ds']
        d['source_url'] = [f"{B}?fileitemno={next(fi for f, fi, g in s['files'] if g == grp)}" for grp in d.facility_group]
        d['source_file'] = ['raw/' + next(f for f, fi, g in s['files'] if g == grp) for grp in d.facility_group]
        d['source_reference_date'] = s['ref']
        d['reference_month_delta'] = mb.month_delta(s['ref'], snap)
        d['temporal_reason'] = '월별 현황 1월 말 추출본(창 안)'
        d['sz_beds'] = pd.to_numeric(d['sz_beds'], errors='coerce')
        d = mb.finalize(d, snap, HERE, TYP)
        q = qa['snapshots'][snap]
        q['final_rows'] = len(d); q['subtype_counts'] = d.facility_subtype.value_counts().to_dict()
        q['geocoding'] = mb.geo_qa(d); q['duplicates'] = mb.dup_qa(d)
        yr = '2019' if snap == '2020_01' else '2024'
        q['official_check'] = dict(data_go_kr_15044540_seoul=off.get(yr), year=yr,
                                   parsed_emergency_institutions=int((d.facility_group == '응급의료기관').sum()),
                                   note='공식 수는 연말 기준, 명부는 다음 해 1월 31일 추출이라 1월 중 지정 변동이 있으면 차이 날 수 있음')
    mb.write_json(HERE / f'qa_{TYP}.json', qa)
    return qa


if __name__ == '__main__':
    q = build()
    for s, v in q['snapshots'].items():
        print(s, v['final_rows'], v['subtype_counts'], v['official_check'], v['geocoding']['coord_method'])
    print(q['id_matching'])
