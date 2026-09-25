# -*- coding: utf-8 -*-
"""공공체육시설 좌표 보완(2026-09-24 사용자 승인). 1→2→3 순서, 기존 행 삭제 없음.
1) 주소 표기 정리 후 재조회(Kakao→VWorld, 건물번호·번지 일치) → coord_method=geocode_*_exact, address_normalized 기록
2) 다른 공식 명부 차용: OA-1115(서울판 공공체육시설 현황) 주소 → 1단계 규칙 지오코딩(address_source='OA-1115');
   OA-21779(서울시 공공체육시설 정보, 현재판) 같은 자치구+정규화 명칭 일치+종목 호환 1건 → 그 주소를 정확 지오코딩,
   coord_method='borrowed_official_list_name_gu', borrow_source 기록. 후보 2건 이상이면 채택하지 않음.
   (OA-21779 파일에는 좌표 열이 없어 원천 주소를 1단계와 같은 정확 일치 규칙으로 좌표화)
3) Kakao 키워드 검색 '자치구 + 시설명': 주소 자치구 일치 + 종목 관련어 포함 후보만, 1건이거나 이름 유사도가 확실한 1위일 때만
   → coord_method='kakao_place_name_gu', place_match_score, place_name 기록."""
import re, difflib, os
from pathlib import Path
import pandas as pd
import openpyxl
import mb

HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'
OA21779 = dict(file='seoul_OA-21779_공공체육시설정보_현재.csv', url='https://datafile.seoul.go.kr/bigfile/iot/sheet/csv/download.do',
               form=dict(srvType='S', infId='OA-21779', serviceKind='1', pageNo='1', ssUserId='SAMPLE_VIEW', strWhere='', strOrderby='',
                         filterCol='', txtFilter=''))
OA1115 = {'2020_01': ('seoul_OA-1115_seq6_2019말.xlsx', '6', '2019-12-31'), '2025_01': ('seoul_OA-1115_seq12_2024말.xlsx', '12', '2024-12-31')}

KW = {'축구장': ['축구', '운동장', '구장', '풋살'], '야구장': ['야구'], '테니스장': ['테니스'], '수영장': ['수영'],
      '생활체육관': ['체육', '스포츠', '센터', '회관', '생활관'], '구기체육관': ['체육', '스포츠', '센터', '회관'], '투기체육관': ['체육', '스포츠', '센터', '회관'],
      '게이트볼장': ['게이트볼'], '골프연습장': ['골프'], '빙상장': ['빙상', '아이스', '스케이트'], '롤러스케이트장': ['롤러', '인라인', '스케이트'],
      '국궁장': ['국궁', '궁', '활터', '정'], '육상경기장': ['운동장', '경기장'], '하키장': ['하키'], '싸이클경기장': ['경륜', '사이클', '싸이클'],
      '파크골프장': ['파크골프', '골프'], '기타체육시설(풋살장)': ['풋살', '축구'],
      '기타체육시설(그외)': ['체육', '운동', '구장', '배드민턴', '족구', '탁구', '농구', '배구', '게이트볼', '테니스', '스포츠', '공원'],
      '기타체육시설': ['체육', '운동', '구장', '배드민턴', '족구', '탁구', '농구', '배구', '게이트볼', '테니스', '스포츠', '공원']}
TYPE_OK = {'축구장': {'축구장'}, '야구장': {'야구장'}, '테니스장': {'테니스장'}, '수영장': {'수영장', '생활체육관'},
           '생활체육관': {'생활체육관', '수영장', '구기체육관', '배드민턴장', '기타'}, '구기체육관': {'구기체육관', '생활체육관', '농구장', '배구장', '배드민턴장'},
           '투기체육관': {'생활체육관', '기타'}, '게이트볼장': {'게이트볼장'}, '골프연습장': {'골프연습장'}, '빙상장': {'빙상장'},
           '롤러스케이트장': {'기타'}, '국궁장': {'기타'}, '육상경기장': {'기타', '축구장'}, '하키장': {'기타'}, '싸이클경기장': {'기타'},
           '파크골프장': {'기타', '골프연습장'}, '기타체육시설(풋살장)': {'풋살장', '축구장'},
           '기타체육시설(그외)': {'기타', '배드민턴장', '농구장', '족구장', '배구장', '게이트볼장', '테니스장', '풋살장'},
           '기타체육시설': {'기타', '배드민턴장', '농구장', '족구장', '배구장', '게이트볼장', '테니스장', '풋살장'}}
DONG_ALIAS = {'포이동': '개포동'}


def download():
    if not (RAW / OA21779['file']).exists():
        mb.fetch(OA21779['url'], RAW / OA21779['file'], method='POST', data=OA21779['form'],
                 headers={'Referer': 'https://data.seoul.go.kr/dataList/OA-21779/S/1/datasetView.do'}, ref_date='현재판(다운로드 시점)',
                 note='서울 열린데이터 OA-21779 서울시 공공체육시설 정보 시트 CSV(좌표 열 없음)')
    for snap, (f, seq, ref) in OA1115.items():
        if not (RAW / f).exists():
            mb.fetch('https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false', RAW / f, method='POST',
                     data=dict(infId='OA-1115', seqNo='', seq=seq, infSeq='3'),
                     headers={'Referer': 'https://data.seoul.go.kr/dataList/OA-1115/F/1/datasetView.do'}, ref_date=ref,
                     note=f'서울 열린데이터 OA-1115 공공체육시설 현황 seq={seq}')


# ------------------------------------------------------------ 1단계
def normalize_variants(addr):
    a = mb.clean(addr)
    out = []
    b = re.sub(r'\([^)]*\)', ' ', a)
    b = re.sub(r'(\d)\s*(번지|호)(?![가-힣])', r'\1', b)
    b = re.sub(r'\s*일대.*$', '', b)
    b = re.sub(r'([가-힣](?:로|길))(\d)', r'\1 \2', b)                 # 안양천길336 → 안양천길 336
    b = re.sub(r'([가-힣]동)(산\s*\d)', r'\1 \2', b)                     # 망우동산73-2 → 망우동 산73-2
    b = re.sub(r'([가-힣]+?)(\d)가\s*\d동\s*(\d)', r'\1동\2가 \3', b)       # 성수1가 1동685-20 → 성수동1가 685-20
    b = re.sub(r'(?<![가-힣])(성수|문래|충무로|을지로|종로|남대문로|봉래동|회현동|명동|필동|인현동|예관동|장충동|황학동|홍익동|상왕십리동)(?=\d가)', lambda m: m.group(1), b)
    b = re.sub(r'\s+', ' ', b).strip()
    out.append(b)
    m = re.search(r'([가-힣]+?)(\d)가(?=\s+\d)', b)
    if m and not m.group(1).endswith(('로', '동')):
        out.append(b[:m.start()] + f'{m.group(1)}동{m.group(2)}가' + b[m.end():])   # 성수1가 → 성수동1가
    for k, v in DONG_ALIAS.items():
        if k in b:
            out.append(b.replace(k, v))
    # 도로명 뒤 장소명 제거(번호까지만)
    m = mb.ROAD_RE.search(b)
    if m:
        out.append(b[:m.end()])
    return [x for x in dict.fromkeys(out) if x and x != a]


def stage1(d):
    n = 0
    for i in d.index[(d.coord_method == 'unresolved') & (d.address != '')]:
        for v in normalize_variants(d.at[i, 'address']):
            lon, lat, meth, det = mb.geocode(v, RAW / 'geocoding')
            if lon is not None:
                d.at[i, 'lon'] = lon; d.at[i, 'lat'] = lat; d.at[i, 'coord_method'] = meth
                d.at[i, 'geocode_detail'] = det; d.at[i, 'address_normalized'] = v; d.at[i, 'coord_stage'] = '1_address_normalized'
                n += 1
                break
    return n


# ------------------------------------------------------------ 2단계
def nname(s, gu=''):
    s = mb.clean(s)
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'^(서울특별시|서울시|서울)\s*', '', s)
    if gu and gu.endswith('구'):
        s = re.sub('^' + re.escape(gu), '', s.replace(' ', ''))
        s = re.sub('^' + re.escape(gu[:-1]) + '(?=구립)', '', s)
    s = re.sub(r'(구립|시립|구민|국립)', '', s)
    return re.sub(r'[^0-9A-Za-z가-힣]', '', s)


def oa21779():
    d = pd.read_csv(RAW / OA21779['file'], encoding='cp949', dtype=str).fillna('')
    d = d[d['시설유형'] != '학교체육시설'].copy()
    d['gu'] = d['자치구'].map(lambda g: g if g.endswith('구') else g + '구')
    d['nn'] = [nname(n, g) for n, g in zip(d['시설명'], d['gu'])]
    return d


def oa1115(snap):
    import build_공공체육시설 as B
    f = RAW / OA1115[snap][0]
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    recs = []
    for sh in wb.sheetnames:
        if sh in B.SKIP or sh in ('서울시(총괄)',):
            continue
        try:
            cols, rows, start, sido_c = B.read_sheet(wb[sh])
        except Exception:
            continue
        nc = B.find(cols, '시설명'); ac = B.find(cols, '주소', exclude=('홈페이지',))
        gc = B.find(cols, '시군구') if B.find(cols, '시군구') is not None else B.find(cols, '시ㆍ군ㆍ구')
        if nc is None or ac is None:
            continue
        for k in range(start, len(rows)):
            r = list(rows[k]) + [None] * 80
            if r[nc] and r[ac]:
                g = re.sub(r'\s+', '', str(r[gc] or ''))
                recs.append(dict(sheet=sh, row=k + 1, name=mb.clean(r[nc]), gu=g, addr=mb.clean(r[ac]),
                                 subtype=B.subtype_of(sh)))
    o = pd.DataFrame(recs)
    if len(o):
        o['nn'] = [nname(n, g) for n, g in zip(o.name, o.gu)]
    return o


def compose(ad, gu):
    if ad.startswith('서울') or mb.OTHER_SIDO.match(ad):
        return ad
    if gu in mb.GU and not any(g in ad[:6] for g in mb.GU):
        return f'서울특별시 {gu} {ad}'
    return '서울특별시 ' + ad


def stage2(d, snap, rej):
    n1115 = n21779 = 0
    o15 = oa1115(snap); o21 = oa21779()
    for i in d.index[d.coord_method == 'unresolved']:
        gu = d.at[i, 'gu']; st = d.at[i, 'facility_subtype']; nn = nname(d.at[i, 'name'], gu)
        # (a) OA-1115 주소
        if len(o15):
            c = o15[(o15.gu == gu) & (o15.nn == nn) & (o15.subtype == st)]
            if len(c) == 1:
                ad = compose(c.iloc[0].addr, gu)
                for v in [ad] + normalize_variants(ad):
                    lon, lat, meth, det = mb.geocode(v, RAW / 'geocoding')
                    if lon is not None:
                        d.at[i, 'lon'] = lon; d.at[i, 'lat'] = lat; d.at[i, 'coord_method'] = meth; d.at[i, 'geocode_detail'] = det
                        d.at[i, 'address_source'] = 'OA-1115'; d.at[i, 'address_normalized'] = v
                        d.at[i, 'borrow_source'] = f"OA-1115 seq{OA1115[snap][1]} {c.iloc[0].sheet}!{c.iloc[0].row}"
                        d.at[i, 'coord_stage'] = '2a_OA-1115_address'; n1115 += 1
                        break
                if d.at[i, 'coord_method'] != 'unresolved':
                    continue
                rej['2a_OA-1115_address_geocode_fail'] = rej.get('2a_OA-1115_address_geocode_fail', 0) + 1
            elif len(c) > 1:
                rej['2a_OA-1115_multiple'] = rej.get('2a_OA-1115_multiple', 0) + 1
        # (b) OA-21779
        c = o21[(o21.gu == gu) & (o21.nn == nn)]
        if len(c) == 0:
            rej['2b_no_name_gu_match'] = rej.get('2b_no_name_gu_match', 0) + 1; continue
        ok = c[c['시설종류'].isin(TYPE_OK.get(st, set())) | c['시설명'].map(lambda x: any(k in x for k in KW.get(st, [])[:2]))]
        if len(ok) == 0:
            rej['2b_type_incompatible'] = rej.get('2b_type_incompatible', 0) + 1; continue
        if len(ok) > 1:
            rej['2b_multiple_candidates'] = rej.get('2b_multiple_candidates', 0) + 1
            d.at[i, 'borrow_source'] = 'REJECTED_multiple:' + ';'.join(ok['체육시설일련번호']); continue
        r = ok.iloc[0]
        ad = r['시설주소']
        got = False
        for v in [ad] + normalize_variants(ad):
            lon, lat, meth, det = mb.geocode(v, RAW / 'geocoding')
            if lon is not None:
                d.at[i, 'lon'] = lon; d.at[i, 'lat'] = lat; d.at[i, 'coord_method'] = 'borrowed_official_list_name_gu'
                d.at[i, 'geocode_detail'] = f'{meth}:{det}'; d.at[i, 'address_normalized'] = v
                d.at[i, 'borrow_source'] = f"OA-21779 체육시설일련번호={r['체육시설일련번호']} | {r['시설명']} | {r['시설종류']} | {ad}"
                d.at[i, 'coord_stage'] = '2b_OA-21779_name_gu'; n21779 += 1; got = True
                break
        if not got:
            rej['2b_borrowed_address_geocode_fail'] = rej.get('2b_borrowed_address_geocode_fail', 0) + 1
    return n1115, n21779


# ------------------------------------------------------------ 3단계
def _kw(q):
    import requests
    r = mb._S.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={'query': q, 'size': 15},
                  headers={'Authorization': 'KakaoAK ' + mb.keys()['KAKAO_REST_API_KEY']}, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f'kakao kw http {r.status_code}')
    return r.json()


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def stage3(d, rej):
    n = 0
    for i in d.index[d.coord_method == 'unresolved']:
        gu = d.at[i, 'gu']; st = d.at[i, 'facility_subtype']; nm = d.at[i, 'name']
        if gu not in mb.GU:
            rej['3_gu_unknown'] = rej.get('3_gu_unknown', 0) + 1; continue
        q = f'{gu} {nm}'
        rec = mb._cached(RAW / 'geocoding', 'kakao_kw', q, _kw)
        docs = (rec.get('response') or {}).get('documents', []) if 'response' in rec else []
        if not docs:
            rej['3_no_result'] = rej.get('3_no_result', 0) + 1; continue
        kws = KW.get(st, ['체육'])
        cand = []
        for x in docs:
            addr = (x.get('road_address_name') or '') + ' ' + (x.get('address_name') or '')
            if f'서울 {gu}' not in addr:
                continue
            txt = (x.get('place_name') or '') + ' ' + (x.get('category_name') or '')
            if not any(k in txt for k in kws):
                continue
            cand.append((sim(nname(nm, gu), nname(x.get('place_name', ''), gu)), x))
        if not cand:
            rej['3_no_candidate_gu_or_keyword'] = rej.get('3_no_candidate_gu_or_keyword', 0) + 1; continue
        cand.sort(key=lambda t: -t[0])
        top = cand[0]
        if len(cand) == 1:
            ok = top[0] >= 0.5
            why = '3_single_low_similarity'
        else:
            ok = top[0] >= 0.6 and top[0] - cand[1][0] >= 0.15
            why = '3_ambiguous_multiple'
        if not ok:
            rej[why] = rej.get(why, 0) + 1
            d.at[i, 'place_name'] = 'REJECTED:' + ' | '.join(f"{x['place_name']}({s:.2f})" for s, x in cand[:3]); continue
        x = top[1]
        d.at[i, 'lon'] = float(x['x']); d.at[i, 'lat'] = float(x['y']); d.at[i, 'coord_method'] = 'kakao_place_name_gu'
        d.at[i, 'place_match_score'] = round(top[0], 3); d.at[i, 'place_name'] = x['place_name']
        d.at[i, 'geocode_detail'] = f"kakao_kw:{q} → {x['place_name']} | {x.get('road_address_name') or x.get('address_name')} | {x.get('category_name')} | n_cand={len(cand)}"
        d.at[i, 'coord_stage'] = '3_kakao_place'; n += 1
    return n


def fill(d, snap):
    for c in ['address_normalized', 'borrow_source', 'place_name', 'coord_stage']:
        if c not in d:
            d[c] = ''
    if 'place_match_score' not in d:
        d['place_match_score'] = None
    d.loc[(d.coord_method != 'unresolved') & (d.coord_stage == ''), 'coord_stage'] = '0_source_address'
    rej = {}
    before = int((d.coord_method != 'unresolved').sum())
    s1 = stage1(d)
    return d, rej, dict(before=before, stage1=s1)


def fill_rest(d, snap, rej, st):
    a, b = stage2(d, snap, rej)
    st['stage2a_OA1115'] = a; st['stage2b_OA21779'] = b
    st['stage3_kakao_place'] = stage3(d, rej)
    return st
