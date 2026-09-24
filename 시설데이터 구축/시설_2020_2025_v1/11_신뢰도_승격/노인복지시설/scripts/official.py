# -*- coding: utf-8 -*-
"""보건복지부 노인복지시설 현황의 '시･군･구별 총괄표'에서 서울 25개 구 × 시설종류 시설수 추출.
2020판(2019.12.31): 02_명부/노인복지시설/raw/mohw_노인복지시설현황_2020_총괄표_시군구.xlsx (읽기만)
2025판(2024.12.31): 02_명부/노인복지시설/raw/mohw_노인복지시설현황_2025.hwpx 본문 section0/1 총괄표(시･군･구) (읽기만)
→ raw/official_노인복지시설_서울_구종류_2019_2024.csv"""
import sys, re, zipfile
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; FD = HERE.parent
sys.path.insert(0, str(FD / '_lib')); import u11
import pandas as pd, openpyxl
V1 = u11.V1; GU = u11.GU
SRC = V1 / '02_명부' / '노인복지시설' / 'raw'
sys.path.insert(0, str(V1 / '02_명부' / '_lib')); import hwptable

SPEC = {'주거': {'양로시설': 6, '노인공동생활가정': 10, '노인복지주택': 14},
        '의료': {'노인요양시설': 6, '노인요양공동생활가정': 10},
        '여가': {'노인복지관': 3},
        '재가': {'방문요양': 6, '주야간보호': 10, '단기보호': 14, '방문목욕': 18, '방문간호': 22, '복지용구지원': 26, '재가노인지원': 30}}


def num(v):
    s = re.sub(r'[,\s]', '', str(v if v is not None else ''))
    return int(s) if re.fullmatch(r'-?\d+', s) else (0 if s in ('', '-') else None)


def pick(rows, spec, shift=0):
    k = next(i for i, r in enumerate(rows) if re.sub(r'\s', '', str(r[0] or '')) == '서울합계')
    out = {}
    for r in rows[k:k + 26]:
        g = re.sub(r'\s', '', str(r[0] or ''))
        g = '서울합계' if g == '서울합계' else g
        out[g] = {t: num(r[c + shift]) for t, c in spec.items()}
    assert set(out) == set(GU) | {'서울합계'}, sorted(set(out) ^ (set(GU) | {'서울합계'}))
    return out


def y2019():
    wb = openpyxl.load_workbook(SRC / 'mohw_노인복지시설현황_2020_총괄표_시군구.xlsx', read_only=True, data_only=True)
    names = {'주거': '3. 가.노인주거복지시설 총괄표(시･군･구)', '의료': '나. 노인의료복지시설 총괄표(시･군･구)',
             '여가': '다. 노인여가복지시설 총괄표(시･군･구)', '재가': '라. 재가노인복지시설 총괄표(시･군･구)'}
    res = {}
    for grp, sh in names.items():
        rows = [list(r) for r in wb[sh].iter_rows(values_only=True)]
        for g, v in pick(rows, SPEC[grp]).items():
            res.setdefault(g, {}).update(v)
    return res


def y2024():
    z = zipfile.ZipFile(SRC / 'mohw_노인복지시설현황_2025.hwpx')
    T0 = hwptable._hwpx_parse(z.read('Contents/section0.xml').decode('utf-8', 'ignore'))
    T1 = hwptable._hwpx_parse(z.read('Contents/section1.xml').decode('utf-8', 'ignore'))
    res = {}
    found = {}
    for t in T0 + T1:
        ctx = ' '.join(t['ctx'][-2:]); g = t['grid']
        if not any(re.sub(r'\s', '', r[0]) == '서울합계' for r in g):
            continue
        head = ' '.join(' '.join(r) for r in g[:4])
        if '양로시설' in head and '노인복지주택' in head: grp, sh = '주거', 0
        elif '노인요양시설' in head and '공동생활' in head and '치매' not in head: grp, sh = '의료', 0
        elif '경 로 당' in head or '경로당' in head: grp, sh = '여가', 0
        elif '방문요양' in head and '주야간' in head: grp, sh = '재가', 1   # 이 표는 둘째 열이 빈 병합열
        else: continue
        if grp in found:
            continue
        found[grp] = ctx
        for gname, v in pick(g, SPEC[grp], shift=sh).items():
            res.setdefault(gname, {}).update(v)
    assert set(found) == set(SPEC), found
    return res


if __name__ == '__main__':
    out = []
    for y, ref, f in [(2019, '2019-12-31', y2019), (2024, '2024-12-31', y2024)]:
        r = f()
        for g, v in r.items():
            for t, n in v.items():
                out.append(dict(year=y, ref_date=ref, gu=g, facility_subtype=t, official=n))
    o = pd.DataFrame(out)
    chk = o[o.gu != '서울합계'].groupby(['year', 'facility_subtype']).official.sum().rename('sum_gu').reset_index().merge(
        o[o.gu == '서울합계'][['year', 'facility_subtype', 'official']], on=['year', 'facility_subtype'])
    print(chk.to_string()); assert (chk.sum_gu == chk.official).all()
    o['source'] = o.year.map({2019: '보건복지부 2020 노인복지시설 현황 총괄표(시･군･구) 2019.12.31 기준 (xlsx)',
                              2024: '보건복지부 2025 노인복지시설 현황 총괄표(시･군･구) 2024.12.31 기준 (hwpx 본문)'})
    o.to_csv(FD / 'raw' / 'official_노인복지시설_서울_구종류_2019_2024.csv', index=False, encoding='utf-8-sig')
