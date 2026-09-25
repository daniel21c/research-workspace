"""검증_<시설>.md 생성 (수치는 compare_summary / official_compare / sensitivity / qa_geocode 파일에서 읽음)."""
import json
from pathlib import Path
import pandas as pd
R = Path(__file__).resolve().parents[2]
SRC = {
 'FOOD': '서울특별시 「서울특별시기본통계」 **식품위생업 현황(구별)** — KOSIS orgId=201, tblId=DT_201004_O110008 (https://kosis.kr/statHtml/statHtml.do?orgId=201&tblId=DT_201004_O110008 ; 서울 열린데이터광장 DT201004O110008 ; data.go.kr 15085127). 기준: 매년 12월 말, 2019·2024 사용. KOSIS 자료갱신일 2026-04-17. 원자료: 자치구 보건소 인허가 대장 집계.',
 'PUB': '서울특별시 「서울특별시기본통계」 **공중위생업 현황** — KOSIS orgId=201, tblId=DT_201004_O110009_2015 (https://kosis.kr/statHtml/statHtml.do?orgId=201&tblId=DT_201004_O110009_2015). 기준: 매년 12월 말, 2019·2024 사용. KOSIS 자료갱신일 2026-04-08.',
 'RET': '서울특별시 「서울특별시기본통계」 **유통업체현황**(대규모점포 업태별 개소·판매면적) — KOSIS orgId=201, tblId=DT_201004_O080001 (https://kosis.kr/statHtml/statHtml.do?orgId=201&tblId=DT_201004_O080001). 기준: 매년 12월 말, 2019·2024 사용. KOSIS 자료갱신일 2026-03-31. 준대규모점포(SSM)는 표에 없음.',
}
COMMON_METHOD = ('- 구축본: `01_인허가/{f}/facilities_{f}_2020_01·2025_01` (행정안전부 지방행정 인허가, 역산 B등급; D=2019-12-31 / 2024-12-31).\n'
                 '- 자치구: 주소의 "서울특별시 ○○구"(없으면 인허가 개방자치단체코드). 좌표 행정동 코드 앞 5자리와 99.99% 일치.\n'
                 '- 공식 표는 KOSIS 통계표 화면에서 2019·2024 시점을 골라 표 값을 추출해 `raw/`에 CSV+metadata로 저장("-"=0).\n'
                 '- 비교 지표: 서울 합계 차이%, 25개 구 Pearson r, 구별 |차이%| 중앙값·최대, ±10% 이내 구 수. 좌표율 = 서울 경계 안 좌표 보유 행 / 전체 행.\n'
                 '- 민감도(방법4): A 기준 / B 현재 상태 휴업 행 제외 / C 기준일 이후 같은 날 20건 이상 일괄 폐업·말소된 행 제외 / D=B+C.')
def T(sc, f):
    s = json.load(open(R / f / f'compare_summary_{f}.json', encoding='utf-8'))
    out = ['| 범위 | 기준 | 구축 | 공식 | 차이% | 구 r | 구 \\|차이%\\| 중앙값 | 최대(구) | ±10% 이내 구 | 범위 좌표율(최저 구) |', '|---|---|---:|---:|---:|---:|---:|---|---:|---|']
    for name, v in s['scopes'].items():
        if sc and name not in sc: continue
        for y, a in v.items():
            out.append(f"| {name} | {y}-12-31 | {a['built']:,} | {a['official']:,} | {a['diff_pct']:+.2f} | {a['gu_pearson_r']} | {a['gu_median_abs_diff_pct']} | {a['gu_max_abs_diff_pct']} ({a['gu_max_abs_diff_gu']}) | {a['gu_n_within_10pct']}/25 | {100*a['scope_coord_rate']:.1f}% ({100*a['scope_min_gu_coord_rate']:.1f}%) |" if 'scope_coord_rate' in a else
                       f"| {name} | {y}-12-31 | {a['built']:,} | {a['official']:,} | {a['diff_pct']:+.2f} | {a['gu_pearson_r']} | {a['gu_median_abs_diff_pct']} | {a['gu_max_abs_diff_pct']} ({a['gu_max_abs_diff_gu']}) | {a['gu_n_within_10pct']}/25 | – |")
    return '\n'.join(out), s
def GUTAB(f, sc):
    c = pd.read_csv(R / f / f'official_compare_{f}.csv'); c = c[c.scope == sc]
    p = c.pivot_table(index='gu', columns='year_official', values=['built', 'official', 'diff_pct'], aggfunc='first')
    lines = ['| 자치구 | 구축 2019 | 공식 2019 | 차이% | 구축 2024 | 공식 2024 | 차이% |', '|---|---:|---:|---:|---:|---:|---:|']
    order = ['서울합계'] + [g for g in p.index if g != '서울합계']
    for g in order:
        r = p.loc[g]
        lines.append(f"| {g} | {int(r[('built','2019')]) if ('built','2019') in r else int(r[('built',2019)])} | " if False else
                     f"| {g} | {int(r[('built',2019)]):,} | {int(r[('official',2019)]):,} | {r[('diff_pct',2019)]:+.1f} | {int(r[('built',2024)]):,} | {int(r[('official',2024)]):,} | {r[('diff_pct',2024)]:+.1f} |")
    return '\n'.join(lines)
def COORD(s, extra=''):
    c = s['coord']; b = s.get('coord_before', {})
    return '\n'.join(['| 시점 | 행 | 좌표율(서울 안) | 최저 구 | 85% 미만 구 | 좌표 단계 |', '|---|---:|---:|---|---:|---|'] +
                     [f"| {y}-12-31 | {v['n']:,} | {100*v['coord_rate_inside_seoul']:.1f}% | {v['min_gu']} {100*v['min_gu_coord_rate']:.1f}% | {v['n_gu_below_85']} | {v['coord_stage']} |" for y, v in c.items()]) + extra
def SENS(f):
    s = pd.read_csv(R / f / f'sensitivity_{f}.csv')
    lines = ['| 범위 | 시점 | 버전 | 구축 | 공식 | 차이% | 구 r | 제외 행 |', '|---|---|---|---:|---:|---:|---:|---:|']
    for _, r in s.iterrows():
        lines.append(f"| {r.scope} | {r.snapshot} | {r.version} | {r.built:,} | {r.official:,} | {r.diff_pct:+.2f} | {r.gu_r} | {r.rows_dropped:,} |")
    return '\n'.join(lines)

REP = {}
# ---------------------------------------------------------------- 일반음식점
qa = json.load(open(R / '일반음식점/qa_geocode_일반음식점.json', encoding='utf-8')); qp = json.load(open(R / '일반음식점/qa_geocode_position_일반음식점.json', encoding='utf-8'))
REP['일반음식점'] = dict(src='FOOD', scopes=None, gu='전체', judge='**상**', method='1 공식 통계 대조 · 3 좌표 보완(재지오코딩) · 4 민감도',
 coord_extra=(f"\n\n좌표 보완 전→후: 2020_01 {100*qa['2020_01']['coord_rate_before']:.1f}% → {100*qa['2020_01']['coord_rate_after']:.1f}%, 2025_01 {100*qa['2025_01']['coord_rate_before']:.1f}% → {100*qa['2025_01']['coord_rate_after']:.1f}%.\n"
   f"- 대상: 두 시점 좌표 없는 행의 고유 시설 {qa['candidates_unique_facilities']:,}개(주소 key 13,084개, 두 시점 공통 시설은 한 번만 조회). Kakao 주소검색(analyze_type=exact) → 불일치 시 VWorld, **도로명+건물번호 또는 법정동+번지 정확 일치**만 채택(원 빌드 `lic_common.geocode_one` 그대로). 채택 {qa['accepted_unique_facilities']:,}개 {qa['by_method']}, key 종류 {qa['by_key_type']}. 요청은 전역 초당 ≤9.5건, 응답은 `raw/geocoding/`(키 미저장) 캐시.\n"
   f"- 채운 행의 x_5179·y_5179·inside_seoul·adm_dong_cd·oa_cd·grid100_cd 는 `lic_common.spatial_attach`(원 빌드 동일, SGIS 2025 2Q 경계)로 부여, `coord_stage=geocode_11`, `coord_method=geocode_kakao_exact|geocode_vworld_exact`.\n"
   f"- 위치 검증: 같은 도로명+건물번호의 원천 좌표 행이 있는 {qp['n_with_same_address_source_rows']:,}건에서 거리 중앙값 {qp['median_m']} m, 50 m 이내 {100*qp['share_within_50m']:.1f}%, 100 m 이내 {100*qp['share_within_100m']:.1f}%, 90% {qp['p90_m']} m. 200 m 이상은 김포공항·세브란스·헬리오시티처럼 한 도로명주소가 넓은 부지를 덮는 경우(자치구 불일치 0). 100 m 격자 분석 시 `coord_stage` 로 민감도 가능.\n"
   f"- 채운 행 중 주소 자치구 ≠ 좌표 자치구: 2020 {qa['2020_01']['gu_coord_mismatch_among_filled']}건, 2025 {qa['2025_01']['gu_coord_mismatch_among_filled']}건(경계 인접). 남은 unresolved: 2020 {qa['2020_01']['unresolved_after']:,}, 2025 {qa['2025_01']['unresolved_after']:,}행(지하상가 '지하 N' 표기, 폐지 주소 등)."),
 why='T: 서울 합계 +0.13% / +1.97%(±5% 이내), 25개 구 r 0.999/0.998, 2024는 25개 구 모두 ±10% 이내. D: 두 시점 같은 원천·같은 규칙. S: 보완 후 99.0%/99.5%, 최저 구(종로) 95.6%/96.8% → 세 조건 충족.',
 gap='- 2019 은평구 +13.9%: 공식 은평구 일반음식점이 2019 3,164 → 2024 3,737(+18%)로 튀고 휴게음식점(+20.9%)·즉석판매(+15.7%)도 같은 해 같은 방향 → 공식 2019 은평구 집계 누락 가능성이 큼(구축은 3,603 → 3,889로 완만).\n- 2024 강남구 +8.2%, 송파 +5.1%: 폐업 신고 지연(기준일 뒤 폐업 처리) 추정. 민감도 C(사후 일괄폐업 제외)는 이 업종에서 하루 20건 이상 폐업이 흔해 과다 제외(−41%/−15%) → 채택하지 않음, 기준 A가 공식과 가장 가까움.\n- 원천에 휴업·취소 상태가 없음(영업/폐업만) → 휴업 포함 여부 차이는 확인 불가(공식도 인허가 대장 기준이라 정의 차이는 작다고 판단).',
 remain='좌표 unresolved 1,183 / 648행(1.0%/0.5%) — 대부분 지하상가 "지하 N" 표기로 주소 key가 안 만들어지거나 geocoder 불일치. 재지오코딩 좌표는 큰 단지에서 원천 좌표와 수백 m 다를 수 있음.')
REP['휴게음식점'] = dict(src='FOOD', scopes=None, gu='전체', judge='**상**', method='1 공식 통계 대조 · 3 구별 좌표율 점검(보완 불필요) · 4 민감도',
 coord_extra='\n\n좌표 보완은 하지 않음(이미 S 충족: 97.8%/97.9%, 최저 구 송파 93.2%/93.3%, 85% 미만 구 없음). 데이터 파일 변경 없음 → `01_인허가/휴게음식점/` 그대로 사용.',
 why='T: 서울 합계 −1.97% / +2.02%, 구 r 0.997/0.998. D 동일. S 원 빌드로 충족 → 상.',
 gap='- 2019 은평구 +20.9%: 일반음식점과 같은 공식 2019 은평구 이상값(공식 996 → 2024 1,139).\n- 2019 전반적으로 구축이 약간 적음(−2%): 휴게음식점 원천에서 과거 이력 일부 누락 가능. 2024 강남 +7.5%·양천 +6.3%.\n- 공식 휴게음식점과 구축 모두 편의점·커피숍·제과형 등 휴게음식점영업 전체(제과점영업은 별도 업종으로 양쪽 다 제외).',
 remain='좌표 unresolved 765/794행(2.2%) — 필요하면 일반음식점과 같은 방식으로 보완 가능.')
REP['식료품소매'] = dict(src='FOOD', scopes=None, gu='즉석판매+제과점(범위제한)', judge='**상 (범위 제한: in_scope = 즉석판매제조가공업+제과점영업)** / 전체 식료품소매는 **중** 유지',
 method='1 공식 통계 대조 · 2 범위 제한(정의 맞춤) · 3 구별 좌표율 점검 · 4 민감도',
 coord_extra='\n\n범위(in_scope) 좌표율: 2020 99.4%(최저 종로 96.3%), 2025 99.8%(최저 97.8%). 전체 좌표율 98.1%/98.6%(원 빌드 지오코딩 포함) — 추가 보완 불필요.\n\n출력 `facilities_식료품소매_20XX_01.parquet/.csv` = 원 빌드 + `in_scope`, `scope_flag`, `coord_stage`, `gu*` 열(행은 그대로).',
 why='범위(즉석판매제조가공업+제과점영업): T 서울 합계 −2.47% / +3.30%, 구 r 0.985/0.995. D: 범위 규칙을 두 시점 동일 적용. S: 99.4%/99.8%, 85% 미만 구 없음 → 상. 전체(축산판매업·기타식품판매 포함)는 대응 공식 통계를 찾지 못해 T 미충족 → 중.',
 gap='- 축산판매업(식육판매·식육부산물·우유류·축산물유통전문·수입판매·식용란수집판매, 11,798~12,444행)은 축산물위생관리법 업종이라 서울시 식품위생업 현황에 없음. 서울시 기본통계(KOSIS 201) 보건 분야 목록에도 축산물 영업 현황 표가 없고, KOSIS 검색에서 시도·구별 식육판매업소 수 표를 찾지 못함 → 미대조.\n- 식품판매업(기타)(=기타식품판매업, 681~749행)은 공식 "식품소분·판매업"(13,431; 소분업·유통전문판매·자판기 등 포함)의 일부라 1:1 대조 불가.\n- 2019 동작구 −21.6%, 종로 −13.6%, 은평 +15.7%(공식 이상값 추정), 2024 강남 +12.6%. 제과점 2024 도봉구 +54%(작은 수 24 → 37).\n- 민감도 C(사후 일괄폐업 제외)는 2024를 −2.3%로 맞추지만 2019를 −9.7%로 벌림 → 기준 A 유지.',
 remain='축산판매업 공식 대조원(식약처 식품의약품통계연보 "축산물 영업장 현황" 시도별 등) 확보 시 전체 승격 재검토.')
for f, extra, why, gap in [
 ('미용업', '', 'T: +3.87% / +1.55%, 구 r 0.9995/0.9999, 2024 25개 구 모두 ±3% 이내. D 동일. S 99.3%/98.8%(최저 송파 96.2%/93.3%) → 상.',
  '- 2019는 모든 구에서 +2~7%로 고르게 많음: 공식이 일부 신규 세부업종(네일·메이크업 등록 초기)을 덜 반영했거나 원천의 늦은 폐업 처리 추정. 민감도 C(사후 일괄폐업 375행 제외) 시 +2.47% / +0.02%.\n- 원천 subtype "일반이용업" 1~2행 포함(무시 가능).'),
 ('이용업', '', 'T: +1.44% / +0.21%, 구 r 0.997/0.999, 25개 구 모두 ±10% 이내(최대 5.3%). S 99.4%/99.6% → 상.', '- 차이 거의 없음. 민감도 B·C 제외 행 0.'),
 ('세탁업', '', 'T: +1.25% / +0.17%, 구 r 0.9994/0.9998, 최대 구 편차 4.2%/2.2%. S 99.6%/99.7% → 상.', '- 공식 세탁업(일반+빨래방 등) = 원천 세부업종 전체와 같은 정의.'),
 ('목욕장업', '', 'T: −0.11% / −0.15%, 구 r 0.9997/0.9999. S 99.8%/100% → 상.', '- 공동탕·찜질시설·한증막 전체 = 공식 목욕장업과 같은 정의.')]:
    REP[f] = dict(src='PUB', scopes=None, gu='전체', judge='**상**', method='1 공식 통계 대조 · 3 구별 좌표율 점검 · 4 민감도',
                  coord_extra='\n\n좌표 보완 불필요(원 빌드로 S 충족). 데이터 파일 변경 없음 → `01_인허가/' + f + '/` 그대로 사용.', why=why, gap=gap, remain='없음(주의: 공식은 연말 등록 기준, 휴업 포함 여부는 명시 없음).')
qd = json.load(open(R / '대규모점포/qa_geocode_대규모점포.json', encoding='utf-8'))
REP['대규모점포'] = dict(src='RET', scopes=None, gu='주요4업태(대형마트·백화점·쇼핑센터·전문점, 범위제한)',
 judge='**상 (범위 제한: in_scope = 점포구분 대규모점포 & 업태 대형마트·백화점·쇼핑센터·전문점)** / 전체 대규모점포 파일은 **중** 유지',
 method='1 공식 통계 대조(업태별) · 2 범위 제한 · 3 좌표 보완(옛 지번 표기 재파싱 후 재지오코딩)·구별 결측 점검 · 4 민감도',
 coord_extra=(f"\n\n좌표 보완 전→후(전체 파일): 2020 {100*qd['2020_01']['coord_rate_before']:.1f}% → {100*qd['2020_01']['coord_rate_after']:.1f}%, 2025 {100*qd['2025_01']['coord_rate_before']:.1f}% → {100*qd['2025_01']['coord_rate_after']:.1f}%.\n"
   "- 좌표 없는 55개 시설: 원 빌드 파서가 '구로동 736번지 1   호', '창신동 766호' 같은 옛 지번 표기를 번지 앞부분만 읽어 불일치 → 보완 파서(`parcel_fix.py`, key_parcel2)로 번지-호를 다시 만들어 Kakao→VWorld 재조회, 법정동+번지 정확 일치 13개 채택. 나머지 42/40행은 Kakao 결과 없음·VWorld 다른 번지(예: 736 → 736-1)·행정동명(수유3동, 망원2동)·'…일대' 주소라 규칙상 미채택.\n"
   "- 남은 결측은 점포구분미상(옛 시장·상가 기록)에 몰려 전체 파일은 은평·구로·영등포 등 3개 구가 85% 미만 → 전체는 S 미충족. 범위(주요 4업태) 좌표율 99.3%/99.3%(최저 중구 93.3%/93.8%).\n"
   "- 출력 `facilities_대규모점포_20XX_01` = 보완 좌표 + `in_scope`, `scope_flag`(주요4업태/기타업태/준대규모점포/점포구분미상), `coord_stage`, `gu*`."),
 why='범위(주요 4업태): T 서울 합계 −2.03% / −2.01%, 구 r 0.936/0.949. D: 같은 업태 규칙 두 시점 적용. S: 99.3%/99.3%, 85% 미만 구 없음 → 상. 단, 구별로는 작은 수(0~6개) 차이가 커서 구 |차이%| 최대 75% — 구 단위 분석보다는 점 단위 접근성용으로 적합.',
 gap='- 점포구분=대규모점포 전체: −11.35%(2019) / −1.41%(2024), 구 r 0.93/0.89 → 2019 T 미충족. 점포구분미상 포함 시 +19.7%/+32.5%(옛 휴업 기록 70건이 대부분; 현재휴업 제외해도 +4.7%/+16.0%).\n- 업태 분류 불일치: 복합쇼핑몰 구축 30/32 vs 공식 10/9, 그 밖의(시장 포함) −22.6%/−9.7% — 인허가 업태구분과 공식 분류 기준이 다름(공식은 그 밖의 대규모점포에 시장을 포함하는 것으로 보임).\n- 대형마트 −5.1%/−7.3%, 백화점 −6.9%/−9.7%, 쇼핑센터 +7.9%/+7.7% 로 개별 업태는 ±5% 밖이나 서로 상쇄 — 대형마트·백화점이 쇼핑센터로 등록된 사례 추정.\n- 준대규모점포(SSM 198/215)는 공식 대조원 없음(범위 밖).',
 remain='전체 대규모점포(그 밖의·시장·복합쇼핑몰·준대규모·점포구분미상)는 공식과 분류가 달라 중. 구별 업태 불일치 원인은 점포 개별 대조(서울시 대규모점포 등록 현황 명부)가 있어야 해소.')
REP['주유소'] = dict(src=None, judge='**상 (범위 제한: in_scope = 현재 영업상태가 휴업이 아닌 행)** — T는 인접 연도 공식값으로 간접 확인(2019·2024 당해 서울 공식값은 미확보)',
 method='1 공식 통계 대조(여러 연말 재역산) · 2 범위 제한(휴업 제외) · 3 구별 좌표율 점검 · 4 민감도(휴업 포함/제외)')

def write(f, r):
    md = [f'# 검증 — {f} (11_신뢰도_승격, 2026-09-24)', '', f"최종 판정: {r['judge']}", '', f"적용 방법: {r['method']}", '', '## 공식 통계 출처·기준일']
    if f == '주유소':
        c = pd.read_csv(R / f / 'official_compare_주유소.csv'); s = json.load(open(R / f / 'compare_summary_주유소.json', encoding='utf-8'))
        md += ['- 한국석유공사_지역별 주유소 수_20251231 (data.go.kr 15038480; 파일 `raw/한국석유공사_지역별주유소수_20251231.csv`, 서울 412, 기준일 2025-12-31). 과거판(20191231·20241231)은 포털에서 새 파일로 대체돼 내려받을 수 없음.',
               '- 한국석유관리원 "영업 중인 주유소 현황"(보도자료 인용 기사): 2021년 470, 2022년 말 444 (에너지신문 2023-03, https://www.energy-news.co.kr/news/articleView.html?idxno=87386), 2023-12-31 436 (데이터솜 2024-01, https://www.datasom.co.kr/news/articleView.html?idxno=200280). 2018 ≈508 은 "2018 대비 −12.6%" 문구로 역산한 추정값.',
               '- 서울시 주유소 현황 (서울 열린데이터광장 OA-22251, 녹색에너지과, 포털 갱신 2023-12-22, **기준일 명시 없음**, 473개소, `raw/seoul_OA-22251_주유소현황.csv`) — 구별 분포 참고용.',
               '- 오피넷(opinet) 지역별 주유소 수 통계 페이지, 한국석유관리원(kpetro.or.kr, robots 확인 실패 → 접근 안 함)에서는 2019·2024 서울 값을 얻지 못함. KOSIS 에도 시도별 주유소 수 표 없음.',
               '', '## 방법', '- `scripts/multi_date_count.py`: 원 빌드와 같은 `lic_common.process_file`·`fix_transfers`·원천중복 제거를 2018~2025 각 12-31 에 적용(업태=주유소). 공식이 "영업 중" 기준이므로 현재 상태가 휴업인 행(휴업일자가 없어 원 빌드가 제외하지 못한 장기휴업, 20~22개)을 뺀 버전을 함께 계산.',
               '- `scripts/scope_flags.py`: 두 시점 파일에 `in_scope`/`scope_flag` 추가(행 유지).', '', '## 비교표 (서울 합계)',
               '| 연말 | 구축(원 빌드 규칙) | 구축(현재휴업 제외) | 공식 | 차이% | 차이%(휴업 제외) | 출처 |', '|---|---:|---:|---:|---:|---:|---|']
        for _, x in c.iterrows():
            md.append(f"| {x.year_end} | {x.built} | {x.built_excl_current_hyueop} | {'' if pd.isna(x.official) else int(x.official)} | {'' if pd.isna(x.diff_pct) else f'{x.diff_pct:+.2f}'} | {'' if pd.isna(x.diff_pct_excl_hyueop) else f'{x.diff_pct_excl_hyueop:+.2f}'} | {x.official_source if isinstance(x.official_source, str) else '(당해 공식값 미확보)'} |")
        g = s['gu_ref_OA22251']
        md += ['', f"구별(참고): 서울시 주유소 현황(OA-22251, 473개) vs 구축 2021-12-31 휴업 제외(473개) — 25개 구 r {g['2021']['gu_r']}, 최대 차이 {g['2021']['gu_max_abs_diff']}개({g['2021']['gu_max_abs_diff_gu']}); 2023 대비 r {g['2023']['gu_r']}. 합계가 2021 구축과 정확히 같아 이 목록은 2021년 말 무렵 기준으로 보임(`gu_compare_주유소_OA22251.csv`).",
               '', '## 좌표율', '| 시점 | in_scope 행 | 좌표율 | 최저 구 | 85% 미만 구 |', '|---|---:|---:|---|---:|',
               '| 2019-12-31 | 497 | 98.8% | 구로구 91.7% | 0 |', '| 2024-12-31 | 427 | 99.3% | 구로구 90.0% | 0 |', '(전체 519/449행 기준 99.0%/99.6%; 원 빌드 지오코딩 포함, 추가 보완 불필요)',
               '', '## 판정 근거', '- T: 휴업 제외 버전이 공식과 2021 +0.64%, 2022 +0.45%, 2023 +0.46%, 2025 0.00%(412=412), 2018(추정) −0.20%. 원 빌드 규칙(휴업 포함)은 +4.1~+5.2%로 경계선. 2019(497)·2024(427)는 인접 공식값 사이에 자연스럽게 놓임(2018 ≈508·2021 470 / 2023 436·2025 412).',
               '- D: 휴업 제외 규칙을 두 시점에 동일 적용. S: 98.8%/99.3%, 85% 미만 구 없음.',
               '- 정의 차이: 공식(석유관리원·석유공사)은 "영업 중" 주유소 → 휴업 제외. 구축 원 빌드는 휴업일자 있는 경우만 제외해서 약 5% 과다.',
               '', '## 남은 문제', '- 2019-12-31·2024-12-31 **당해** 서울 공식값을 확보하지 못함(석유공사 과거 파일·오피넷 통계 미확보). 확보 시 T 재확인 필요 — 현재 판정은 인접 5개 시점 대조에 근거.',
               '- "현재 휴업" 상태는 2026 원천 기준값이라, 2019년에 영업하다 이후 휴업한 곳은 2019에서 빠질 수 있음(휴업 행 수가 2018~2025 내내 20~22개로 고정 → 대부분 장기휴업으로 판단).', '- LPG 충전소는 석유판매업이 아니라 포함 안 됨(공식 주유소 수도 LPG 제외).',
               '', '## 파일', '- `facilities_주유소_2020_01/2025_01.parquet·.csv` (원 빌드 + in_scope, scope_flag, coord_stage, gu_org/gu_addr/gu/gu_coord)', '- `official_compare_주유소.csv`, `compare_summary_주유소.json`, `gu_compare_주유소_OA22251.csv`, `raw/`(공식 원본+metadata), `scripts/multi_date_count.py`, `scripts/scope_flags.py`, `scripts/gu.py`']
    else:
        tab, s = T(None, f)
        md += ['- ' + SRC[r['src']], '', '## 방법', COMMON_METHOD.format(f=f), '', '## 비교표 — 서울 합계·구별 요약', tab, '', f"## 구별 비교 ({r['gu']})", GUTAB(f, r['gu']),
               '', '## 좌표율 (전→후)', COORD(s, r.get('coord_extra', '')), '', '## 민감도', SENS(f), '', '## 판정 근거', r['why'], '', '## 정의 차이·편차 설명', r['gap'], '', '## 남은 문제', r['remain'], '', '## 파일',
               '- `official_compare_' + f + '.csv`(범위×시점×구), `compare_summary_' + f + '.json`, `coord_by_gu_' + f + '.csv`, `sensitivity_' + f + '.csv`, `raw/`(KOSIS 표 CSV+metadata' + (', 지오코딩 캐시·후보·색인' if f in ('일반음식점', '대규모점포') else '') + ')',
               '- 스크립트 `scripts/`: ' + ', '.join(sorted(p.name for p in (R / f / 'scripts').glob('*.py'))) + ((' — 실행 순서: geocode_missing.py(반복) → index_cache.py → apply_geocode.py → ' + ('parcel_fix.py → geocode_missing.py → index_cache.py → apply_geocode.py → scope_flags.py → ' if f == '대규모점포' else 'geocode_qa.py → ') + 'compare.py → sensitivity.py') if f in ('일반음식점', '대규모점포') else (' — scope_flags.py → compare.py → sensitivity.py' if f == '식료품소매' else ' — compare.py → sensitivity.py'))]
        if f in ('일반음식점', '대규모점포', '식료품소매'):
            md.append(f'- 데이터: `facilities_{f}_2020_01/2025_01.parquet·.csv` (원 빌드 공통 열 유지 + 추가 열 coord_stage' + (', in_scope, scope_flag' if f != '일반음식점' else '') + ', gu_org, gu_addr, gu, gu_coord)')
    (R / f / f'검증_{f}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
for f, r in REP.items():
    write(f, r); print('wrote', f)
