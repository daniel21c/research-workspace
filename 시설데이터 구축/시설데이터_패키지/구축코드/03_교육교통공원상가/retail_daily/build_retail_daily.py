# -*- coding: utf-8 -*-
"""일상소매(상가업소 기준) 2020_01 / 2025_01 — 소상공인시장진흥공단 상가(상권)정보 서울
대상 소분류: G20404 슈퍼마켓, G20405 편의점, G20499 그 외 기타 종합 소매업, G20501 곡물/곡분, G20503 정육점,
            G20504 건어물/젓갈, G20505 수산물, G20506 채소/과일, G20509 반찬/식료품.
2020_01 주: 2019.12판(20191231) — 2025-11 재작성본(신분류·2022-08 이후 부여 상가업소번호) → grade B.
   플래그: flag_id_issued_after_ref = 번호 발급월(상가업소번호 7~12자리 YYYYMM) > 판 기준월,
          flag_nonbulk_id = 발급월이 일괄 재부여월(202208, 202410)이 아님(재작성 때 개별 추가된 번호 의심).
2020_01 민감도: 2020.03판(20200331, 같은 재작성본) → facilities_retail_daily_2020_01_sens202003.*
2025_01: 2024.12판(20241231, A).
원본 zip(전국)은 raw/에 보관, 서울 CSV에서 대상 업종(+비교용 의원·병원 Q101·Q102)만 raw/sbiz_seoul_extract_*.csv로 추출.
대조: 국세청 100대 생활업종 사업자 수(서울, 2020-01 = 202101판 전년동월, 2024-12 = 202412판 당월).
사용: python build_retail_daily.py extract 201912 202003 202412 → python build_retail_daily.py"""
import sys, zipfile, io, re, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_lib'))
import fac
import pandas as pd, numpy as np
import dl_sbiz

RAW = HERE / 'raw'; TYP = 'retail_daily'
REL = {'201912': '20191231', '202003': '20200331', '202412': '20241231'}
CODES = {'G20404': '슈퍼마켓', 'G20405': '편의점', 'G20499': '그 외 기타 종합 소매업', 'G20501': '곡물/곡분 소매업',
         'G20503': '정육점', 'G20504': '건어물/젓갈 소매업', 'G20505': '수산물 소매업', 'G20506': '채소/과일 소매업',
         'G20509': '반찬/식료품 소매업'}
USE = ['상가업소번호', '상호명', '지점명', '상권업종대분류코드', '상권업종중분류코드', '상권업종중분류명', '상권업종소분류코드',
       '상권업종소분류명', '표준산업분류코드', '시군구명', '행정동코드', '행정동명', '지번주소', '도로명주소', '건물명', '층정보', '경도', '위도']
BULK = {'202208', '202410'}

def zname(i):
    return i.filename if i.flag_bits & 0x800 else i.filename.encode('cp437').decode('cp949', 'replace')

def seoul_csv(zp):
    z = zipfile.ZipFile(zp)
    for i in z.infolist():
        n = zname(i)
        if n.endswith('.csv') and '서울' in n: return z.open(i), n
        if n.endswith('.zip'):
            zz = zipfile.ZipFile(io.BytesIO(z.read(i)))
            for j in zz.infolist():
                if zname(j).endswith('.csv') and '서울' in zname(j): return zz.open(j), n + '!' + zname(j)
    raise FileNotFoundError(zp)

def extract(rel):
    out = RAW / f'sbiz_seoul_extract_{rel}.csv'
    if out.exists(): return out
    zp = RAW / f'sbiz_상가상권정보_{REL[rel]}.zip'
    if not zp.exists(): dl_sbiz.get(REL[rel])
    f, n = seoul_csv(zp)
    rows = 0; parts = []
    for ch in pd.read_csv(f, dtype=str, usecols=USE, chunksize=100000, encoding='utf-8'):
        ch['source_row_id'] = np.arange(rows + 2, rows + 2 + len(ch)); rows += len(ch)
        parts.append(ch[ch['상권업종소분류코드'].isin(CODES) | ch['상권업종중분류코드'].isin(['Q101', 'Q102'])])
    d = pd.concat(parts)
    d.to_csv(out, index=False, encoding='utf-8-sig')
    fac.write_meta(out, derived_from=f'raw/{zp.name} :: {n}', seoul_rows_total=rows, extracted_rows=len(d),
                   rule='소분류 ' + ','.join(CODES) + ' 또는 중분류 Q101,Q102', created_utc=fac.utcnow())
    return out

def flags(d, rel):
    idn = d['상가업소번호'].astype(str)
    ok = idn.str.match(r'^MA01\d{2}\d{6}')
    ym = idn.str[6:12].where(ok)
    d['id_issue_ym'] = ym
    d['flag_id_issued_after_ref'] = (ym > rel).fillna(False)
    d['flag_nonbulk_id'] = (~ym.isin(BULK)) & ok
    return d

def build(rel, snap, codes, typ, tdir, ftype, cat, grade, fsuffix=''):
    d = fac.read_csv_any(RAW / f'sbiz_seoul_extract_{rel}.csv') if tdir == HERE else fac.read_csv_any(HERE / 'raw' / f'sbiz_seoul_extract_{rel}.csv')
    meta = json.load(open(RAW / f'sbiz_seoul_extract_{rel}.csv.metadata.json', encoding='utf-8'))
    d = d[codes(d)].copy(); d = flags(d, rel)
    o = pd.DataFrame(index=d.index)
    o['facility_id'] = 'SBIZ_' + d['상가업소번호']; o['category_group'] = cat; o['facility_type'] = ftype
    o['facility_subtype'] = d['상권업종소분류코드'] + ' ' + d['상권업종소분류명']; o['year_snapshot'] = snap
    o['name'] = d['상호명'].fillna('') + np.where(d['지점명'].notna(), ' ' + d['지점명'].fillna(''), '')
    o['address'] = d['도로명주소'].fillna(d['지번주소']); o['lon'] = d['경도']; o['lat'] = d['위도']
    o['coord_method'] = 'source'; o['grade'] = grade; o['source_org'] = '소상공인시장진흥공단'
    o['source_dataset'] = f'상가(상권)정보 {rel}판' + (' (2025-11 재작성본)' if rel < '2022' else '')
    o['source_url'] = 'https://www.data.go.kr/data/15083033/fileData.do'
    o['source_file'] = 'raw/' + meta['derived_from'].replace('raw/', '')
    o['source_row_id'] = d['source_row_id'].astype(str)
    ref = f'{REL[rel][:4]}-{REL[rel][4:6]}-{REL[rel][6:]}'
    o['source_reference_date'] = ref; o['reference_month_delta'] = fac.month_delta(ref, snap)
    o['temporal_reason'] = ('재작성본(원 배포본 아님): 번호 발급월 비일괄 행 플래그' if rel < '2022' else '기준일 배포본')
    for c in ['id_issue_ym', 'flag_id_issued_after_ref', 'flag_nonbulk_id']: o[c] = d[c]
    o['sbiz_mid_code'] = d['상권업종중분류코드']; o['ksic_code'] = d['표준산업분류코드']; o['floor'] = d['층정보']
    o['building_name'] = d['건물명']; o['gu_name'] = d['시군구명']; o['sbiz_adm_dong_cd'] = d['행정동코드']
    o = fac.attach_geo(o); o.loc[o['x_5179'].isna(), 'coord_method'] = 'unresolved'
    o = fac.finalize(o)
    base = Path(tdir) / f'facilities_{typ}_{snap}{fsuffix}'
    o.to_csv(str(base) + '.csv', index=False, encoding='utf-8-sig')
    o2 = o.copy()
    for c in o2.columns:
        if o2[c].dtype == object: o2[c] = o2[c].astype('string')
    o2.to_parquet(str(base) + '.parquet', index=False)
    q = fac.qa_block(o)
    q.update(seoul_rows_in_release=meta['seoul_rows_total'], extract_rows=meta['extracted_rows'],
             flag_id_issued_after_ref=int(o['flag_id_issued_after_ref'].sum()), flag_nonbulk_id=int(o['flag_nonbulk_id'].sum()),
             id_issue_ym_top=o['id_issue_ym'].value_counts().head(8).to_dict(), dup_name_addr=int(o.duplicated(['name', 'address']).sum()))
    return o, q

def nts():
    a = fac.read_csv_any(RAW / 'nts_100대생활업종_202101.csv'); b = fac.read_csv_any(RAW / 'nts_100대생활업종_202412.csv')
    def tot(d, col):
        s = d[d['시도'].str.strip() == '서울특별시'].copy(); s['v'] = pd.to_numeric(s[col].str.strip(), errors='coerce')
        return s.groupby(s['업종'].str.replace(r'\s', '', regex=True).replace({'치과병원ㆍ의원': '치과의원'}))['v'].agg(lambda x: (int(x.sum()), int(x.isna().sum())))
    return tot(a, '전년동월'), tot(b, '당월')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'extract':
        for r in sys.argv[2:]: print(extract(r))
        sys.exit()
    for r in REL: extract(r)
    fac.fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do', RAW / 'nts_100대생활업종_202101.csv', params=dict(atchFileId='FILE_000000002490954', fileDetailSn=1), ref_date='202101', note='국세청_사업자현황_100대 생활업종(data.go.kr 15061118). 202101판의 전년동월 열=2020-01')
    fac.fetch('https://www.data.go.kr/cmm/cmm/fileDownload.do', RAW / 'nts_100대생활업종_202412.csv', params=dict(atchFileId='FILE_000000003104676', fileDetailSn=1), ref_date='202412', note='국세청_사업자현황_100대 생활업종(data.go.kr 15061118)')
    sel = lambda d: d['상권업종소분류코드'].isin(CODES)
    qa = {'type': TYP, 'notes': [__doc__.strip()]}
    o20, qa['2020_01'] = build('201912', '2020_01', sel, TYP, HERE, '일상소매(상가업소)', '상업생활편의', 'B')
    o20s, qa['2020_01_sens202003'] = build('202003', '2020_01', sel, TYP, HERE, '일상소매(상가업소)', '상업생활편의', 'B', '_sens202003')
    o25, qa['2025_01'] = build('202412', '2025_01', sel, TYP, HERE, '일상소매(상가업소)', '상업생활편의', 'A')
    n20, n24 = nts()
    MAP = {'G20404': ['슈퍼마켓'], 'G20405': ['편의점'], 'G20501': ['곡물가게'], 'G20503': ['정육점'], 'G20504': ['건어물가게'],
           'G20505': ['생선가게'], 'G20506': ['채소가게', '과일가게'], 'G20509': ['식료품가게']}
    cmp = {}
    for c, nm in MAP.items():
        cmp[c + ' ' + CODES[c]] = dict(nts_items=nm, sbiz_201912=int((o20['facility_subtype'].str[:6] == c).sum()),
                                      sbiz_202003=int((o20s['facility_subtype'].str[:6] == c).sum()),
                                      sbiz_202412=int((o25['facility_subtype'].str[:6] == c).sum()),
                                      nts_2020_01=sum(n20.get(x, (0, 0))[0] for x in nm), nts_2020_01_masked_gu=sum(n20.get(x, (0, 0))[1] for x in nm),
                                      nts_2024_12=sum(n24.get(x, (0, 0))[0] for x in nm), nts_2024_12_masked_gu=sum(n24.get(x, (0, 0))[1] for x in nm))
    qa['official_compare_nts100'] = cmp
    for k in ['2020_01', '2025_01']:
        pass
    ids20, ids25 = set(o20['facility_id']), set(o25['facility_id'])
    qa['panel'] = dict(common_ids=len(ids20 & ids25), only_2020=len(ids20 - ids25), only_2025=len(ids25 - ids20),
                       note='2019.12 재작성본 번호는 2022-08 이후 체계라 2024.12판과 같은 번호 체계')
    qa['sens_201912_vs_202003'] = dict(common=len(ids20 & set(o20s['facility_id'])), only_201912=len(ids20 - set(o20s['facility_id'])), only_202003=len(set(o20s['facility_id']) - ids20))
    fac.dump_qa(HERE, TYP, qa)
    for k in ['2020_01', '2020_01_sens202003', '2025_01']:
        print(k, {kk: qa[k][kk] for kk in ['rows', 'coord_rate', 'outside_seoul', 'flag_id_issued_after_ref', 'flag_nonbulk_id', 'dup_facility_id', 'subtype']})
    print(json.dumps(cmp, ensure_ascii=False)); print(qa['panel'], qa['sens_201912_vs_202003'])
