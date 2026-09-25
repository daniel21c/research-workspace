# -*- coding: utf-8 -*-
"""가족센터(건강가정지원센터) 2020_01·2025_01. 기준일 배포본 → grade A.
2020_01: data.go.kr 3077162 「여성가족부_건강가정지원센터 현황_20190903」(창 안, -3개월).
2025_01: 여가부 「2025년 가족센터(건강가정지원센터) 현황」 주소록 HWP(2025.1.1 현재).
원천에 센터명이 없어 '자치구 + 센터 종류'로 이름을 만든다. 2025 주소록의 '1센터/2센터/분소/2관'은 지점 행으로 나누고
공동육아나눔터·교류소통공간 등 부속 공간은 제외한다(qa에 수 기록)."""
import sys, re, io
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import mb, hwptable
import pandas as pd
import requests

RAW = HERE / 'raw'
TYP = '가족센터'
SRC = {
    '2020_01': dict(file='datagokr_3077162_건강가정지원센터_20190903.csv', url='https://www.data.go.kr/cmm/cmm/fileDownload.do',
                    params=dict(atchFileId='FILE_000000002318385', fileDetailSn='1'), ref='2019-09-03',
                    ds='data.go.kr 3077162 여성가족부_건강가정지원센터 현황_20190903', org='여성가족부(data.go.kr)'),
    '2025_01': dict(file='mogef_가족센터_주소록_2025.hwp', url='https://www.mogef.go.kr/plc/down.do',
                    form=dict(bbid='plc503', bbtSn='705043', atfileSn='706255', atfileSeq='1'), ref='2025-01-01',
                    page='https://www.mogef.go.kr/mp/pcd/mp_pcd_s001d.do?mid=plc503&bbtSn=705043',
                    ds='여성가족부 2025년 가족센터(건강가정지원센터) 현황 주소록(2025.1.1 현재)', org='여성가족부'),
}
BRANCH_RE = re.compile(r'(?:(?<![^\s,])([가-힣\d]+(?:\([^)]*\))?)\s*:\s*|(?<![가-힣\d])(본센터|센터|[가-힣]*분소|공동육아나눔터|교류소통공간)\)\s*)')


def download():
    s = SRC['2020_01']
    S = requests.Session(); S.headers['User-Agent'] = mb.UA
    mb.fetch(s['url'], RAW / s['file'], params=s['params'], session=S, ref_date=s['ref'], note=s['ds'])
    s = SRC['2025_01']
    if not (RAW / s['file']).exists():
        S = requests.Session(); S.headers['User-Agent'] = mb.UA
        S.get(s['page'], timeout=60)
        mb.fetch(s['url'], RAW / s['file'], method='POST', data=s['form'], session=S, headers={'Referer': s['page']},
                 ref_date=s['ref'], note=s['ds'] + ' | 상세페이지 쿠키 후 POST')


def read_2019():
    b = (RAW / SRC['2020_01']['file']).read_bytes()
    d = pd.read_csv(io.StringIO(b.decode('cp949')), dtype=str)
    d = d[d['시도'] == '서울특별시'].copy()
    d['gu'] = d['시군구'].str.replace('서울특별시', '').str.strip()
    d['address'] = [mb.seoulize(a, g) for a, g in zip(d['주소'], d['gu'])]
    dup = d.gu.duplicated(keep=False)
    d['name'] = [f"{g} 건강가정지원센터" + (f" ({mb.parse_addr(a)[0]['road'] if mb.parse_addr(a) else ''})" if du else '')
                 for g, a, du in zip(d.gu, d.address, dup)]
    d['facility_subtype'] = ['건강·다문화가족지원센터(통합)' if x == 'Y' else '건강가정지원센터' for x in d['통합센터'].fillna('')]
    d['sz_open_date'] = d['개소일']; d['sz_state_funded'] = d['국비지원'].fillna(''); d['sz_integrated'] = d['통합센터'].fillna('')
    d['source_row_id'] = '번호' + d['번호']
    return d[['name', 'address', 'gu', 'facility_subtype', 'sz_open_date', 'sz_state_funded', 'sz_integrated', 'source_row_id']], dict(source_rows_seoul=len(d))


def read_2025():
    T = hwptable.hwp_tables(RAW / SRC['2025_01']['file'])
    recs = []; skipped = []; official = None
    for ti, t in enumerate(T):
        g = t['grid']
        if not g or '주소' not in ' '.join(g[0]):
            continue
        kind = '가족센터' if '가족센터 주소' in ' '.join(g[0]) else '건강가정지원센터'
        off = 1 if g[0][0].strip() == '연번' else 0
        cur = None
        for ri, r in enumerate(g[1:], start=1):
            sd = r[off].strip()
            if sd:
                m = re.match(r'(\S+)\s*\((\d+)\)', sd)
                cur = m.group(1) if m else sd
                if m and cur == '서울' and kind == '가족센터':
                    official = int(m.group(2))
            if cur != '서울':
                continue
            gu = r[off + 1].strip(); ad = mb.clean(r[off + 2]); tel = r[off + 3] if len(r) > off + 3 else ''
            parts = [(m.group(1) or m.group(2), m.end()) for m in BRANCH_RE.finditer(ad)]
            if not parts:
                sites = [('', ad)]
            else:
                sites = []
                for k, (lab, st) in enumerate(parts):
                    en = [m.start() for m in BRANCH_RE.finditer(ad)][k + 1] if k + 1 < len(parts) else len(ad)
                    sites.append((lab, ad[st:en].strip(' ,')))
                pre = ad[:[m.start() for m in BRANCH_RE.finditer(ad)][0]].strip()
                if pre:
                    sites.insert(0, ('', pre))
            base = '서울특별시' if gu == '서울특별시' else gu
            kept = 0
            for k, (lab, a) in enumerate(sites):
                if re.search(r'나눔터|교류소통|1인가구|힐링|돌봄', lab):
                    skipped.append(dict(gu=gu, label=lab, address=a)); continue
                main = kept == 0
                kept += 1
                nm = (f"{base} 가족센터(광역)" if base == '서울특별시' else f"{base} 가족센터") if kind == '가족센터' else f"{base} 건강가정지원센터"
                if not main:
                    nm += f" {lab}"
                recs.append(dict(name=nm, gu=gu, address=a if a.startswith('서울') else mb.seoulize(a, gu),
                                 facility_subtype=kind + ('' if main else '(지점)'), sz_site_label=lab,
                                 sz_is_main_site=bool(main), source_row_id=f'table{ti}_row{ri}' + (f'_site{k}' if len(sites) > 1 else '')))
    d = pd.DataFrame(recs)
    d['address'] = d['address'].str.replace('서울시 ', '서울특별시 ', regex=False)
    return d, dict(source_rows_seoul=f'주소록 서울 {len(set(d.gu))}개 자치구·광역 행 → 지점 분리 {len(d)}행', official_seoul_family_centers=official, main_site_rows=int(d.sz_is_main_site.sum()), site_rows=len(d),
                   skipped_annex_spaces=skipped)


def build():
    download()
    qa = dict(type=TYP, grade='A', note_grade='기준일 배포본(2019-09-03 / 2025-01-01 현재)', snapshots={})
    fr = {}
    for snap, rd in [('2020_01', read_2019), ('2025_01', read_2025)]:
        s = SRC[snap]
        d, info = rd()
        d = mb.geocode_df(d, RAW / 'geocoding')
        fr[snap] = d
        qa['snapshots'][snap] = dict(source_file=s['file'], **info)
    a, b, st = mb.assign_ids(fr['2020_01'].assign(_k=fr['2020_01'].gu), fr['2025_01'].assign(_k=fr['2025_01'].gu), 'FAM', extra_key='_k')
    # 자치구 센터는 자치구가 같으면 같은 시설로 본다(명칭이 원천에 없고 2020~ '가족센터'로 개칭): 본점끼리 자치구로 재매칭
    a = a.drop(columns=['_k']); b = b.drop(columns=['_k'])
    main20 = a[~a.name.str.contains(r'\(')].drop_duplicates('gu').set_index('gu')['facility_id']
    fixed = 0
    for i in b.index:
        if b.at[i, 'sz_is_main_site'] and b.at[i, 'gu'] in main20.index and b.at[i, 'gu'] != '서울특별시' and b.at[i, 'id_match_rule'] == 'new':
            b.at[i, 'facility_id'] = main20[b.at[i, 'gu']]; b.at[i, 'id_match_rule'] = 'same_gu_main_center'; fixed += 1
    qa['facility_id_rule'] = 'mb.assign_ids(명칭+주소키 등, subtype 대신 자치구 사용) 후, 매칭 안 된 2025 자치구 본점은 같은 자치구 2020 센터 id를 부여(같은 자치구 센터 = 같은 시설로 간주, 이전 여부는 주소로 확인 가능)'
    qa['id_matching'] = dict(st, reassigned_same_gu_main=fixed)
    for snap, d in [('2020_01', a), ('2025_01', b)]:
        s = SRC[snap]
        d = mb.spatial(d)
        d['category_group'] = '복지행정안전'; d['facility_type'] = TYP; d['grade'] = 'A'
        d['source_org'] = s['org']; d['source_dataset'] = s['ds']
        d['source_url'] = s['url'] + ('?atchFileId=' + s['params']['atchFileId'] + '&fileDetailSn=1' if 'params' in s else '')
        d['source_file'] = 'raw/' + s['file']; d['source_reference_date'] = s['ref']
        d['reference_month_delta'] = mb.month_delta(s['ref'], snap)
        d['temporal_reason'] = '기준일 배포본' + (' (2019-09-03, 창 안 -3개월)' if snap == '2020_01' else ' (2025-01-01 현재)')
        d = mb.finalize(d, snap, HERE, TYP)
        q = qa['snapshots'][snap]
        q['final_rows'] = len(d); q['subtype_counts'] = d.facility_subtype.value_counts().to_dict()
        q['geocoding'] = mb.geo_qa(d); q['duplicates'] = mb.dup_qa(d)
    q = qa['snapshots']
    qa['official_check'] = {'2025_01': dict(official_seoul_가족센터=q['2025_01']['official_seoul_family_centers'],
                                            parsed_main_sites=q['2025_01']['main_site_rows']),
                            '2020_01': dict(parsed_rows=q['2020_01']['final_rows'],
                                            note='data.go.kr 파일 자체가 공식 명부(별도 시도 집계 없음). 서울 광역센터 포함 27행')}
    mb.write_json(HERE / f'qa_{TYP}.json', qa)
    return qa


if __name__ == '__main__':
    import json
    q = build()
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('skipped_annex_spaces',)} for k, v in q['snapshots'].items()}, ensure_ascii=False)[:2500])
    print(q['official_check'], q['id_matching'])
