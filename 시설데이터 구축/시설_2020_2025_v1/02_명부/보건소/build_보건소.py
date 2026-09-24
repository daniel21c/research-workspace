# -*- coding: utf-8 -*-
"""보건소·보건지소·건강생활지원센터(보건복지부 전국 지역보건의료기관 현황, data.go.kr 3072692) 2020_01·2025_01. 연간 명부 → grade C.
2020_01: 20191231판(등록 2019-09-27, 표기 기준일 2019-12-31). 2025_01: 창 안 판이 없어 20251231판(+12개월)을 쓰고,
2024년말 시도별 수(data.go.kr 15127903)와 대조한다. 20221231판에도 있는지(in_2022_edition)를 함께 기록해 2025년 신설 가능성을 표시."""
import sys, re, io
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import mb
import pandas as pd
import requests

RAW = HERE / 'raw'
TYP = '보건소'
U = 'https://www.data.go.kr/cmm/cmm/fileDownload.do'
SRC = {
    '2020_01': dict(file='datagokr_3072692_지역보건의료기관_20191231.csv', atch='FILE_000000002879363', ref='2019-12-31',
                    ds='보건복지부_전국 지역보건의료기관 현황_20191231'),
    '2025_01': dict(file='datagokr_3072692_지역보건의료기관_20251231.csv', atch='FILE_000000003692397', ref='2025-12-31',
                    ds='보건복지부_전국 지역보건의료기관 현황_20251231'),
}
AUX = [('datagokr_3072692_지역보건의료기관_20221231.csv', 'FILE_000000003155391', '2022-12-31', '20221231판(신설 여부 보조)'),
       ('datagokr_15127903_보건소등수_시도별_20241231.csv', 'FILE_000000003639322', '2024-12-31', '보건소·보건지소·보건진료소·건강생활지원센터 수_시도별')]


def download():
    S = requests.Session(); S.headers['User-Agent'] = mb.UA
    for s in SRC.values():
        mb.fetch(U, RAW / s['file'], params=dict(atchFileId=s['atch'], fileDetailSn='1'), session=S, ref_date=s['ref'], note=s['ds'])
    for f, a, ref, note in AUX:
        mb.fetch(U, RAW / f, params=dict(atchFileId=a, fileDetailSn='1'), session=S, ref_date=ref, note=note)


def rd(f):
    b = (RAW / f).read_bytes()
    for e in ('utf-8-sig', 'cp949'):
        try:
            return pd.read_csv(io.StringIO(b.decode(e)), dtype=str)
        except UnicodeDecodeError:
            pass


def read(snap):
    d = rd(SRC[snap]['file'])
    d = d[d['시도'].str.contains('서울')].copy()
    d['_row'] = d.index + 2
    typ = '보건기관 유형' if '보건기관 유형' in d else '기관유형'
    out = pd.DataFrame(dict(name=d['보건기관명'].map(mb.clean), gu=d['시군구'].map(mb.clean), facility_subtype=d[typ].map(mb.clean),
                            raw_address=d['주소'].map(mb.clean), source_row_id='row' + d['_row'].astype(str),
                            sz_parent=d['상위기관명'].fillna('') if '상위기관명' in d else ''))
    out['address'] = [a if a.startswith('서울') else mb.seoulize(a, g) for a, g in zip(out.raw_address, out.gu)]
    return out


def official():
    d = rd(AUX[1][0])
    d = d[d['시도'].str.startswith('서울')]
    return {r['년도']: {k: int(r[k]) for k in ['보건소', '보건지소', '보건진료소', '건강생활지원센터']} for _, r in d.iterrows()}


def build():
    download()
    qa = dict(type=TYP, grade='C', note_grade='연간 공식 명부', snapshots={})
    fr = {}
    for snap in ['2020_01', '2025_01']:
        d = read(snap)
        d = mb.geocode_df(d, RAW / 'geocoding')
        fr[snap] = d
        qa['snapshots'][snap] = dict(source_file=SRC[snap]['file'], source_rows_seoul=len(d))
    d22 = rd(AUX[0][0]); d22 = d22[d22['시도'].str.contains('서울')]
    n22 = set(d22['보건기관명'].map(mb.norm_name))
    fr['2025_01']['in_2022_edition'] = fr['2025_01'].name.map(mb.norm_name).isin(n22)
    a, b, st = mb.assign_ids(fr['2020_01'], fr['2025_01'], 'PHC')
    qa['facility_id_rule'] = 'mb.assign_ids(0 명칭+주소키+subtype, 1 명칭+주소키, 2 명칭 유일, 3 주소키+subtype 유일, 4 좌표 50m+명칭 앞4자)'
    qa['id_matching'] = st
    off = official()
    for snap, d in [('2020_01', a), ('2025_01', b)]:
        s = SRC[snap]
        d = mb.spatial(d)
        d['category_group'] = '보건의료'; d['facility_type'] = TYP; d['grade'] = 'C'
        d['source_org'] = '보건복지부(data.go.kr)'; d['source_dataset'] = s['ds']
        d['source_url'] = f"{U}?atchFileId={s['atch']}&fileDetailSn=1"
        d['source_file'] = 'raw/' + s['file']; d['source_reference_date'] = s['ref']
        d['reference_month_delta'] = mb.month_delta(s['ref'], snap)
        d['temporal_reason'] = ('20191231판(data.go.kr 등록 2019-09-27; 표기 기준일 사용)' if snap == '2020_01' else
                                '창 안 판 없음 → 20251231판 사용(+12개월). 2024말 시도별 수와 대조, in_2022_edition=False는 2023~2025 신설 가능')
        d = mb.finalize(d.drop(columns=['raw_address']), snap, HERE, TYP)
        q = qa['snapshots'][snap]
        q['final_rows'] = len(d); q['subtype_counts'] = d.facility_subtype.value_counts().to_dict()
        q['geocoding'] = mb.geo_qa(d); q['duplicates'] = mb.dup_qa(d)
        yr = '2019' if snap == '2020_01' else '2024'
        q['official_check'] = dict(data_go_kr_15127903_seoul=off.get(yr), official_year=yr, parsed=q['subtype_counts'])
        if snap == '2025_01':
            q['rows_not_in_2022_edition'] = d.loc[~d.in_2022_edition.astype(bool), ['name', 'facility_subtype']].to_dict('records')
    mb.write_json(HERE / f'qa_{TYP}.json', qa)
    return qa


if __name__ == '__main__':
    q = build()
    for s, v in q['snapshots'].items():
        print(s, v['final_rows'], v['official_check'], v['geocoding']['coord_method'])
    print(q['snapshots']['2025_01']['rows_not_in_2022_edition'], q['id_matching'])
