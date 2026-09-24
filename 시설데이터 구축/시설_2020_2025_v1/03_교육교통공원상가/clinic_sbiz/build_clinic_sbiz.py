# -*- coding: utf-8 -*-
"""[비교용] 상가업소 기준 의원(Q102)·병원(Q101) 2020_01 / 2025_01 — 일상소매와 같은 방법(retail_daily 추출물 재사용).
주 원천은 보건의료 그룹의 인허가 역산(사용자 결정 2026-09-24). 이 파일은 비교용으로만 쓴다.
2020_01: 2019.12 재작성본(B, 플래그 동일), 민감도 2020.03판, 2025_01: 2024.12판(A).
대조: 국세청 100대 생활업종 의원 계열(내과ㆍ소아과·일반외과·신경정신과·피부ㆍ비뇨기과·안과·이비인후과·산부인과·성형외과·기타일반·치과·한방병원ㆍ한의원), 종합병원."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
RD = HERE.parent / 'retail_daily'
sys.path.insert(0, str(HERE.parent / '_lib')); sys.path.insert(0, str(RD))
import fac
import build_retail_daily as br
import pandas as pd

TYP = 'clinic_sbiz'
for r in br.REL: br.extract(r)
sel = lambda d: d['상권업종중분류코드'].isin(['Q101', 'Q102'])
qa = {'type': TYP, 'notes': [__doc__.strip(), '원본 zip·추출물은 ../retail_daily/raw/ 에 있음(중복 저장하지 않음).']}
o20, qa['2020_01'] = br.build('201912', '2020_01', sel, TYP, HERE, '의원·병원(상가업소, 비교용)', '보건의료', 'B')
o20s, qa['2020_01_sens202003'] = br.build('202003', '2020_01', sel, TYP, HERE, '의원·병원(상가업소, 비교용)', '보건의료', 'B', '_sens202003')
o25, qa['2025_01'] = br.build('202412', '2025_01', sel, TYP, HERE, '의원·병원(상가업소, 비교용)', '보건의료', 'A')
n20, n24 = br.nts()
CL = ['내과ㆍ소아과의원', '일반외과의원', '신경정신과의원', '피부ㆍ비뇨기과의원', '안과의원', '이비인후과의원', '산부인과의원', '성형외과의원',
      '기타일반의원', '치과의원', '한방병원ㆍ한의원']
qa['official_compare_nts100'] = {
    'Q102 의원 vs NTS 의원계열(한방병원 포함)': dict(sbiz_201912=int((o20['sbiz_mid_code'] == 'Q102').sum()), sbiz_202412=int((o25['sbiz_mid_code'] == 'Q102').sum()),
                                           nts_2020_01=sum(n20.get(x, (0, 0))[0] for x in CL), nts_2024_12=sum(n24.get(x, (0, 0))[0] for x in CL)),
    'Q10101 종합병원 vs NTS 종합병원': dict(sbiz_201912=int((o20['facility_subtype'].str[:6] == 'Q10101').sum()), sbiz_202412=int((o25['facility_subtype'].str[:6] == 'Q10101').sum()),
                                     nts_2020_01=n20.get('종합병원', (0, 0))[0], nts_2024_12=n24.get('종합병원', (0, 0))[0])}
fac.dump_qa(HERE, TYP, qa)
for k in ['2020_01', '2020_01_sens202003', '2025_01']:
    print(k, {kk: qa[k][kk] for kk in ['rows', 'coord_rate', 'flag_nonbulk_id']})
print(qa['official_compare_nts100'])
