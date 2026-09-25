# -*- coding: utf-8 -*-
"""노인복지시설(보건복지부 「노인복지시설 현황」 책자 시설 명부) 2020_01(2020년판=2019.12.31 기준)·2025_01(2025년판=2024.12.31 기준).
연간 명부 → grade C. 대상: 노인주거(양로·노인공동생활가정·노인복지주택), 노인의료(노인요양·노인요양공동생활가정), 노인복지관,
재가노인복지시설(방문요양·주야간보호·단기보호·방문목욕·방문간호·복지용구지원·재가노인지원). 경로당·노인교실(명부 없음, 구별 수만),
노인보호전문기관·노인일자리지원기관·치매전담실·부록(장기요양 재가기관)은 제외.
2020판은 HWP(바이너리), 2025판은 HWPX에서 표 구조(셀 주소)를 그대로 읽는다(_lib/hwptable.py)."""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import mb, hwptable
import pandas as pd
import openpyxl

RAW = HERE / 'raw'
TYP = '노인복지시설'
B = 'https://www.mohw.go.kr/boardDownload.es'
SRC = {
    '2020_01': dict(file='mohw_노인복지시설현황_2020_통계본문.hwp', bid='0020', list_no='355051', seq='3', ref='2019-12-31',
                    ds='2020 노인복지시설 현황(2019.12.31 기준) 통계본문'),
    '2025_01': dict(file='mohw_노인복지시설현황_2025.hwpx', bid='0019', list_no='1486600', seq='1', ref='2024-12-31',
                    ds='2025 노인복지시설 현황(2024.12.31 기준)'),
}
EXTRA = [('mohw_노인복지시설현황_2020_통계부록.hwp', '0020', '355051', '5', '2019-12-31', '2020 통계부록(재가장기요양기관, 미사용)'),
         ('mohw_노인복지시설현황_2020_총괄표_시도.xlsx', '0020', '355051', '7', '2019-12-31', '2020 총괄표(광역시.도) - 공식 집계 대조'),
         ('mohw_노인복지시설현황_2020_총괄표_시군구.xlsx', '0020', '355051', '8', '2019-12-31', '2020 총괄표(시.군.구)')]
TYPES = {'양로시설': ('노인주거복지시설', '양로시설'), '노인공동생활가정': ('노인주거복지시설', '노인공동생활가정'),
         '노인복지주택': ('노인주거복지시설', '노인복지주택'), '노인요양시설': ('노인의료복지시설', '노인요양시설'),
         '노인요양공동생활가정': ('노인의료복지시설', '노인요양공동생활가정'), '노인복지관': ('노인여가복지시설', '노인복지관'),
         '방문요양서비스': ('재가노인복지시설', '방문요양'), '주야간보호서비스': ('재가노인복지시설', '주야간보호'),
         '단기보호서비스': ('재가노인복지시설', '단기보호'), '방문목욕서비스': ('재가노인복지시설', '방문목욕'),
         '방문간호서비스': ('재가노인복지시설', '방문간호'), '복지용구지원서비스': ('재가노인복지시설', '복지용구지원'),
         '재가노인지원서비스': ('재가노인복지시설', '재가노인지원')}
HEAD_RE = re.compile(r'^(?:\d+|[IVX]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+)\s*\.\s*(.+?)\s*┃?\s*$')
SIDO_RE = re.compile(r'^(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원도|강원특별자치도|충청북도|충청남도|전라북도|전북특별자치도|전라남도|경상북도|경상남도|제주특별자치도|서울특별자치시)\b')


def download():
    for s in SRC.values():
        mb.fetch(B, RAW / s['file'], params=dict(bid=s['bid'], list_no=s['list_no'], seq=s['seq']), ref_date=s['ref'], note=s['ds'])
    for f, bid, ln, seq, ref, note in EXTRA:
        mb.fetch(B, RAW / f, params=dict(bid=bid, list_no=ln, seq=seq), ref_date=ref, note=note)


def nz(s):
    return re.sub(r'[\s･·ㆍ]', '', s or '')


def numv(v):
    m = re.search(r'-?\d[\d,]*', str(v or ''))
    return float(m.group(0).replace(',', '')) if m else None


def parse(snap):
    s = SRC[snap]
    T = (hwptable.hwpx_tables if s['file'].endswith('x') else hwptable.hwp_tables)(RAW / s['file'])
    cur_type = None; cur_sido = None
    recs = []; official = {}
    for ti, t in enumerate(T):
        for x in t['ctx']:
            m = HEAD_RE.match(x.strip())
            if m:
                cur_type = TYPES.get(nz(m.group(1)).replace('주･야간', '주야간'), None) if True else None
                if cur_type is None and nz(m.group(1)) in ('주야간보호서비스',):
                    cur_type = TYPES['주야간보호서비스']
            m2 = re.match(r'^▣\s*(\S+)', x.strip())
            if m2:
                cur_sido = m2.group(1)
        g = t['grid']
        if not g:
            continue
        m3 = SIDO_RE.match(g[0][0].strip()) if g[0][0] else None
        if m3 and all(not c for c in g[0][1:]):
            cur_sido = m3.group(1)
            g = g[1:]
        if cur_type is None or cur_sido != '서울특별시':
            continue
        # 머리글 행: 첫 자료/합계 행 앞
        k = next((i for i, r in enumerate(g) if re.fullmatch(r'\d+', r[0].strip()) or nz(r[0]) == '합계'), None)
        if k is None:
            continue
        H = g[:k]

        def col(key, nth=0):
            hits = []
            for r in H:
                for j, c in enumerate(r):
                    if nz(c) == key and j not in hits:
                        hits.append(j)
            hits.sort()
            return hits[nth] if len(hits) > nth else None
        C = dict(gu=col('시군구'), name=col('시설명'), addr=col('소재지'), date=col('설치일'), op=col('운영주체'),
                 cap=col('정원'), cur=col('현원'), staff=col('종사자수'), annual=col('연간(실)인원'),
                 sale=col('분양현황'), oper=col('운영현황'))
        if C['name'] is None or C['addr'] is None:
            continue
        for ri, r in enumerate(g[k:]):
            c0 = r[0].strip()
            if nz(c0) == '합계':
                n = numv(r[C['name']]) if C['name'] is not None else None
                official[cur_type[1]] = official.get(cur_type[1], 0) + (n or 0)
                continue
            if not re.fullmatch(r'\d+', c0):
                continue
            g_ = lambda key: r[C[key]].strip() if C[key] is not None and C[key] < len(r) else ''
            rec = dict(facility_group=cur_type[0], facility_subtype=cur_type[1], serial=int(c0), gu=nz(g_('gu')),
                       name=mb.clean(g_('name')), raw_address=mb.clean(g_('addr')), sz_open_date=g_('date'), sz_operator=g_('op'),
                       source_row_id=f'table{ti}_row{k + ri}')
            if cur_type[1] == '노인복지주택':
                rec['sz_units_sale'] = numv(g_('sale')); rec['sz_units_operating'] = numv(g_('oper'))
                rec['sz_capacity'] = rec['sz_units_sale']
            else:
                rec['sz_capacity'] = numv(g_('cap'))
                rec['sz_current'] = numv(g_('cur'))
            rec['sz_staff'] = numv(g_('staff'))
            if C['annual'] is not None:
                rec['sz_annual_users'] = numv(g_('annual'))
            recs.append(rec)
    d = pd.DataFrame(recs)
    d['address'] = [a if a.startswith('서울') or mb.OTHER_SIDO.match(a) else mb.seoulize(a, gu if gu in mb.GU else '')
                    for a, gu in zip(d.raw_address, d.gu)]
    return d, official


def xlsx_official():
    wb = openpyxl.load_workbook(RAW / 'mohw_노인복지시설현황_2020_총괄표_시도.xlsx', read_only=True, data_only=True)
    spec = {'2. 가.노인주거복지시설 총괄표': {'양로시설': 6, '노인공동생활가정': 10, '노인복지주택': 14},
            '나. 노인의료복지시설 총괄표': {'노인요양시설': 6, '노인요양공동생활가정': 10},
            '다. 노인여가복지시설 총괄표': {'노인복지관': 3, '경로당(참고)': 5},
            '라. 재가노인복지시설 총괄표': {'재가노인복지시설_합계': 2, '방문요양': 6, '주야간보호': 10, '단기보호': 14, '방문목욕': 18,
                                    '방문간호': 22, '복지용구지원': 26}}
    out = {}
    for sh, m in spec.items():
        for r in wb[sh].iter_rows(values_only=True):
            if r[0] and str(r[0]).strip() == '서울':
                for k, j in m.items():
                    out[k] = r[j]
    return out


def build():
    download()
    qa = dict(type=TYP, grade='C', note_grade='연간 공식 명부(보건복지부 노인복지시설 현황, 12.31 기준)', snapshots={},
              excluded=['경로당·노인교실(개별 명부 없음)', '노인보호전문기관', '노인일자리지원기관', '치매전담실/치매전담형(하위 단위)', '부록 재가장기요양기관'])
    fr = {}
    for snap in ['2020_01', '2025_01']:
        s = SRC[snap]
        d, off = parse(snap)
        d = mb.geocode_df(d, RAW / 'geocoding')
        fr[snap] = d
        qa['snapshots'][snap] = dict(source_file=s['file'], source_rows_seoul=len(d),
                                     official_table_total_rows=off)
    a, b, st = mb.assign_ids(fr['2020_01'], fr['2025_01'], 'ELD')
    qa['facility_id_rule'] = 'mb.assign_ids(0 명칭+주소키+subtype, 1 명칭+주소키, 2 명칭 유일, 3 주소키+subtype 유일, 4 좌표 50m 이내+명칭 앞4자). 정규화=괄호·법인격·기호 제거, 주소키=도로명+건물번호(없으면 동+번지) subtype이 달라도(요양시설↔공동생활가정 전환 등) 1·2 규칙으로 같은 id'
    qa['id_matching'] = st
    for snap, d in [('2020_01', a), ('2025_01', b)]:
        s = SRC[snap]
        d = mb.spatial(d)
        d['category_group'] = '복지행정안전'; d['facility_type'] = TYP; d['grade'] = 'C'
        d['source_org'] = '보건복지부'; d['source_dataset'] = s['ds']
        d['source_url'] = f"{B}?bid={s['bid']}&list_no={s['list_no']}&seq={s['seq']}"
        d['source_file'] = 'raw/' + s['file']; d['source_reference_date'] = s['ref']
        d['reference_month_delta'] = mb.month_delta(s['ref'], snap)
        d['temporal_reason'] = '연간 책자(12.31 기준) 시설 명부'
        q = qa['snapshots'][snap]
        sc = {}
        for t, x in d.groupby('facility_subtype'):
            vc = x.serial.value_counts()
            sc[t] = dict(max_serial=int(x.serial.max()), duplicated_serials=sorted(int(i) for i in vc[vc > 1].index),
                         missing_serials=[i for i in range(1, int(x.serial.max()) + 1) if i not in set(x.serial)])
        q['book_serial_check'] = {k: v for k, v in sc.items() if v['duplicated_serials'] or v['missing_serials']}
        q['book_serial_note'] = '책자 일련번호 중복·누락은 원본 표기 그대로(행은 모두 유지). 합계 개소와 행수 차이의 원인.'
        d = mb.finalize(d.drop(columns=['raw_address', 'serial']), snap, HERE, TYP)
        q['final_rows'] = len(d); q['subtype_counts'] = d.facility_subtype.value_counts().to_dict()
        q['geocoding'] = mb.geo_qa(d); q['duplicates'] = mb.dup_qa(d)
        q['geocoding_by_subtype'] = d.groupby('facility_subtype')['lon'].apply(lambda x: round(x.notna().mean(), 4)).to_dict()
        q['official_check'] = {k: dict(book_table_total=v, parsed=q['subtype_counts'].get(k, 0), diff=q['subtype_counts'].get(k, 0) - v)
                               for k, v in q['official_table_total_rows'].items()}
        if snap == '2020_01':
            q['official_check_xlsx_시도총괄표'] = xlsx_official()
    qa['notes'] = ['방문요양·방문목욕 등 방문형 서비스는 정원이 0으로 기재됨(이용 현원·연간 실인원 사용).',
                   '2025판 방문요양(1,133)·방문목욕(741)은 2020판(206·163)보다 크게 늘었는데, 재가노인복지시설로 신고한 장기요양기관 범위 변화 영향이므로 두 시점 비교 시 주의.']
    mb.write_json(HERE / f'qa_{TYP}.json', qa)
    return qa


if __name__ == '__main__':
    q = build()
    for s, v in q['snapshots'].items():
        print(s, v['final_rows'], v['geocoding']['coord_method'])
        print('  ', v['official_check'])
    print(q['snapshots']['2020_01'].get('official_check_xlsx_시도총괄표'))
    print(q['id_matching'])
