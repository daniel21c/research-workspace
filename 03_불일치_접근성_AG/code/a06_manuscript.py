# -*- coding: utf-8 -*-
"""Applied Geography 투고 원고 생성. 모든 수치는 results/의 원결과에서 읽어 채운다(손으로 적은 수치 없음).
출력(manuscript/): AG_manuscript_anonymised.docx(익명 본문·표·그림), AG_title_page.docx(저자·선언), AG_highlights.docx,
 AG_supplementary_appendix.docx(부록 A), AG_cover_letter.docx, AG_한국어_원고.docx(한국어 전문), values_used.json(채운 값), word_count.json
실행: python code/a06_manuscript.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = Path(__file__).resolve().parent; AG = HERE.parent; RES = AG / 'results'; MS = AG / 'manuscript'; FIG = MS / 'figures'
sys.path.insert(0, str(HERE))
import a06_text_en as EN  # noqa: E402
import a06_text_ko as KO  # noqa: E402
import a06_math as MATH  # noqa: E402

CAT = ['교육', '보육·복지', '의료', '문화', '행정·안전', '소매', '생활서비스']
CAT_EN = dict(zip(CAT, ['Education', 'Childcare and welfare', 'Health', 'Culture', 'Civic and safety', 'Retail', 'Personal services']))
TYPES_EN = {'교육': 'Kindergartens; schools; youth centres', '보육·복지': 'Childcare centres; senior day and welfare centres; disability community centres; family centres',
            '의료': 'Clinics; pharmacies; hospitals; public health centres; emergency medical facilities; postnatal care centres',
            '문화': 'Public libraries; cultural facilities; registered performance venues', '행정·안전': 'Community service centres; fire stations and 119 safety centres',
            '소매': 'Everyday retail; food retail (bakeries, prepared food); large stores', '생활서비스': 'Restaurants; cafés and snack bars; hair salons; barbers; laundries; public baths'}
TYPES_KO = {'교육': '유치원, 학교, 청소년수련시설', '보육·복지': '어린이집, 노인 이용시설, 장애인 이용시설, 가족센터(자치구 본소)', '의료': '의원, 약국, 병원급, 보건소·보건지소, 응급의료기관, 산후조리원',
            '문화': '공공도서관, 문화기반시설, 등록공연장', '행정·안전': '주민센터, 소방서·119안전센터', '소매': '일상소매, 식료품소매(즉석판매·제과), 대규모점포(주요 4업태)',
            '생활서비스': '일반음식점, 휴게음식점, 미용업, 이용업, 세탁업, 목욕장업'}


def _grp(v):
    """Elsevier 숫자 표기: 네 자리는 쉼표 없음(1000), 다섯 자리부터 쉼표(10,000). AG 게재 논문 10편 대조."""
    return f'{v:,}' if v >= 10000 else str(v)


def n0(x):
    v = int(round(float(x))); return ('−' if v < 0 else '') + _grp(abs(v))


def sgn(x):
    x = int(round(float(x))); return ('+' if x > 0 else '−' if x < 0 else '') + _grp(abs(x))


def f2(x):
    return (f'{x:.2f}').replace('-', '−')


def f3(x):
    return (f'{x:.3f}').replace('-', '−')


def ci(a, b, f=f3):
    return f'[{f(a)}, {f(b)}]'


def pct(x, d=1):
    return f'{100 * x:.{d}f}'


def load(y, name):
    return json.load(open(RES / str(y) / name, encoding='utf-8'))


def values():
    V = {}; T = {}
    for y in (2020, 2025):
        t = str(y)[2:]; a = load(y, 'a01_summary.json'); m = load(y, 'a04_mechanism_summary.json'); e = load(y, 'a03_ensemble_summary.json')
        C = pd.DataFrame(a['curve']); R = pd.read_csv(RES / str(y) / 'a01_states.csv'); fl = R[R.strategy == 'FLOW']; K = int(C.k.max()); rd = R[(R.strategy == 'RAND') & (R.k == K)]
        fi = a['facility_info']; od = json.load(open(RES / 'appendix' / f'constrained_paths_summary_{y}.json', encoding='utf-8'))
        P = pd.read_csv(RES / str(y) / 'a03_ensemble_plans.csv'); E = P[P.plan.str.startswith('E')]
        imin = fl.dL.idxmin(); end = C.iloc[-1]
        V.update({f'L{t}': n0(a['L_LZ']), f'L{t}s': pct(a['L_LZ_share']), f'ifr{t}': pct(a['IFR_LZ']), f'cul{t}': n0(a['category_omission_LZ']['문화']), f'civ{t}': n0(a['category_omission_LZ']['행정·안전']),
                  f'nm{t}': str(K), f'ngu{t}': str(a['n_gu_with_moves']), f'rm{t}': sgn(end.rand_median), f'rlo{t}': sgn(end['rand_p2.5']), f'rhi{t}': sgn(end['rand_p97.5']),
                  f'fmin{t}': n0(-fl.loc[imin, 'dL']), f'fk{t}': str(int(fl.loc[imin, 'k'])), f'fe{t}': sgn(end.flow_dL), f'k{t}': str(a['first_k_from_which_flow_below_all_random']),
                  f's10_{t}': f"{100 * C[C.k == 10].share_rand_below_flow.iloc[0]:.0f}", f'fp{t}': n0(fl[fl.k == K].moved_pop.iloc[0]), f'rp{t}': n0(rd.moved_pop.median()),
                  f'fn{t}': n0(end.flow_new), f'fr{t}': n0(end.flow_resolved), f'rn{t}': n0(rd.new.median()), f'rr{t}': n0(rd.resolved.median()),
                  f'fifr{t}': pct(end.flow_IFR), f'rifr{t}': pct(rd.IFR.median()),
                  f'g{t}': n0(e['n_greater']), f'med{t}': n0(e['L_median_all']), f'dmed{t}': n0(e['median_minus_LZ']), f'dmin{t}': n0(e['L_min_all'] - e['L_LZ']),
                  f'np{t}': n0(m['n_pairs']), f'nd{t}': n0(m['n_dongs']), f'pc{t}': f3(m['partial_W_F_given_AP']['est']), f'pc{t}ci': ci(*m['partial_W_F_given_AP']['ci95']),
                  f'pz{t}': f3(m['partial_W_F_given_AP_Zpop_Zemp']['est']), f'pz{t}ci': ci(*m['partial_W_F_given_AP_Zpop_Zemp']['ci95']), f'fe{t}b': f2(m['dongFE_std_beta']['F']['est']),
                  f'h{t}': f2(m['partial_by_category']['의료']['est']), f'r{t}': f2(m['partial_by_category']['소매']['est']), f's{t}': f2(m['partial_by_category']['생활서비스']['est']),
                  f'od{t}m': f"{fi_od(y):.1f}", f'fac{t}': n0(fi['facility_selected_rows']), f'cell{t}': n0(fi['facility_cells']), f'pop{t}m': f"{a['population'] / 1e6:.2f}"})
        n_ab = int((E.IFR > float(P[P.plan == 'LZ'].IFR.iloc[0]) + 1e-15).sum()); V[f'ifrab{t}_n'] = n_ab
        T[y] = dict(a=a, m=m, e=e, C=C, R=R, rd=rd, fl=fl, K=K, od=od, P=P, E=E)
    ess = [s['L_ESS'] for y in (2020, 2025) for s in T[y]['e']['seeds'].values()]
    V['essmin'], V['essmax'] = f'{min(ess):.0f}', f'{max(ess):.0f}'
    l20 = 1000 - int(V['g20'].replace(',', '')); l25 = 1000 - int(V['g25'].replace(',', ''))
    V['depend_en'] = 'The reported shares describe the sampled ensemble and should not be read as probabilities over all feasible partitions.'
    V['depend_ko'] = '이 비율은 표본으로 얻은 앙상블 안의 비율이며, 가능한 모든 분할에 대한 확률로 읽어서는 안 된다.'
    a25, a20 = V['ifrab25_n'], V['ifrab20_n']
    V['ifr_en'] = f'{"no" if a25 == 0 else a25} alternative map{"s" if a25 > 1 else ""} had a higher IFR in 2025, and {a20} did in 2020.'
    V['ifr_ko'] = f'IFR이 공식보다 높은 대안은 2025년 {"한 장도 없었고" if a25 == 0 else f"{a25}장이었고"}, 2020년 {a20}장이었다.'
    V['pop25m'] = V.pop('pop25m'); V.pop('pop20m')
    for y in (2020, 2025):  # 범주 의존·시설 시점 민감도(a10, 2026-10-02 감사 S2-1 대응)
        t = str(y)[2:]; a = json.load(open(RES / str(y) / 'a10_sensitivity.json', encoding='utf-8')); fc = a['flow_end_minus_official_by_category']; pa = a['paths']
        V.update({f'cul_d{t}': sgn(fc['문화']), f'civ_d{t}': sgn(fc['행정·안전']), f'edu_d{t}': sgn(fc['교육']),
                  f'f5_{t}': sgn(pa['five']['flow_end']), f'r5_{t}': n0(pa['five']['rand_end_median']), f'b5_{t}': f"{100 * (1 - pa['five']['rand_end_share_below_flow']):.0f}",
                  f'fC_{t}': sgn(pa['noC']['flow_end']), f'rC_{t}': sgn(pa['noC']['rand_end_median']), f'kC_{t}': str(pa['noC']['first_k_flow_below_all_random']),
                  f'g5_{t}': n0(a['ensemble']['five']['n_greater']), f'gC_{t}': n0(a['ensemble']['noC']['n_greater'])})
        T[y]['a10'] = a
    V['minstates'] = str(min(int(pd.read_csv(f).query('ku not in [11010, 11020, 11130, 11180]').saved_unique_states.min()) for f in sorted(RES.glob('20*/a02_ensemble_*_chain_diag.csv'))))
    return V, T


def fi_od(y):
    return float(json.load(open(RES / 'appendix' / f'constrained_paths_summary_{y}.json', encoding='utf-8'))['OD_total']) / 1e6


# ---------------------------------------------------------------- tables
def tables(V, T, lang='en'):
    k = lambda en, ko: en if lang == 'en' else ko  # noqa: E731
    Y = (2020, 2025); out = {}
    rows = [[k('Item', '항목'), '2020', '2025'],
            [k('Spatial units', '공간 단위'), k('25 gu, 424 dongs, 116 official living zones (dong boundaries of July 2023)', '25개 자치구, 424개 동, 116개 공식 생활권(2023년 7월 동 경계)'), k('same', '같음')],
            [k('Residents (100 m grid; population year)', '주민(100 m 격자, 인구 연도)'), f"{n0(T[2020]['a']['population'])} (2019)", f"{n0(T[2025]['a']['population'])} (2024)"],
            [k('Populated 100 m cells', '인구가 있는 100 m 격자'), n0(T[2020]['a']['facility_info']['positive_origins']), n0(T[2025]['a']['facility_info']['positive_origins'])],
            [k('Trips between Seoul dongs (January; arrivals 09:00–20:59; home–work trips removed)', '서울 동 간 통행(1월, 09:00~20:59 도착, 집–직장 통행 제외)'), n0(T[2020]['od']['OD_total']), n0(T[2025]['od']['OD_total'])],
            [k('Facility records (27 types, 7 categories)', '시설 기록(27개 유형, 7개 범주)'), n0(T[2020]['a']['facility_info']['facility_selected_rows']), n0(T[2025]['a']['facility_info']['facility_selected_rows'])],
            [k('100 m cells containing a facility', '시설이 있는 100 m 격자'), n0(T[2020]['a']['facility_info']['facility_cells']), n0(T[2025]['a']['facility_info']['facility_cells'])],
            [k('Walking network (OpenStreetMap extract)', '보행망(OpenStreetMap 추출본)'), '1 Jan 2020', '1 Jan 2025'],
            [k('Cell pairs within 15 min (populated origin, facility destination)', '15분 안 격자 쌍(인구 출발, 시설 도착)'), n0(T[2020]['a']['facility_info']['usable_pairs']), n0(T[2025]['a']['facility_info']['usable_pairs'])]]
    out['T1'] = (k('Table 1. Data and study settings.', '표 1. 자료와 분석 설정.'), rows, k('Walking speed 4 km/h; threshold 15 minutes. Sports businesses are excluded from the facility inventory.', '보행 속도 4 km/h, 기준 15분. 체육시설업은 시설 목록에서 제외.'))
    r = [[k('', ''), '2020', '2025']]
    r.append([k('Official plan: excluded residents (share)', '공식 생활권: 누락 인구(비율)')] + [f"{V['L' + str(y)[2:]]} ({V['L' + str(y)[2:] + 's']}%)" for y in Y])
    r.append([k('Official plan: IFR (%)', '공식 생활권: IFR(%)')] + [V['ifr' + str(y)[2:]] for y in Y])
    r.append([k('Moves (dongs moved)', '이동 수(옮긴 동 수)')] + [f"{T[y]['K']} ({T[y]['a']['n_flow_moved_dongs']})" for y in Y])
    r.append([k('Flow-guided: residents in moved dongs', '통행 기준: 옮긴 동의 인구')] + [V['fp' + str(y)[2:]] for y in Y])
    r.append([k('Flow-guided: ΔL (new / resolved)', '통행 기준: ΔL(신규 / 해소)')] + [f"{V['fe' + str(y)[2:]]} ({V['fn' + str(y)[2:]]} / {V['fr' + str(y)[2:]]})" for y in Y])
    r.append([k('Flow-guided: IFR (%)', '통행 기준: IFR(%)')] + [V['fifr' + str(y)[2:]] for y in Y])
    r.append([k('Random, median of 100: residents in moved dongs', '무작위 100경로 중앙값: 옮긴 동의 인구')] + [V['rp' + str(y)[2:]] for y in Y])
    r.append([k('Random: ΔL [middle 95%]', '무작위: ΔL [가운데 95%]')] + [f"{V['rm' + str(y)[2:]]} [{V['rlo' + str(y)[2:]]}, {V['rhi' + str(y)[2:]]}]" for y in Y])
    r.append([k('Random: new / resolved (medians)', '무작위: 신규 / 해소(중앙값)')] + [f"{V['rn' + str(y)[2:]]} / {V['rr' + str(y)[2:]]}" for y in Y])
    r.append([k('Random: IFR (%, median)', '무작위: IFR(%, 중앙값)')] + [V['rifr' + str(y)[2:]] for y in Y])
    r.append([k('Flow-guided below all random paths from k =', '통행 기준이 모든 무작위 경로보다 낮아지는 k')] + [V['k' + str(y)[2:]] for y in Y])
    out['T2'] = (k('Table 2. Official plan and the end of the reassignment paths.', '표 2. 공식 생활권과 재배정 경로의 끝.'), r,
                 k('ΔL is the change in excluded residents relative to the official plan; ΔL = new − resolved. Random figures are medians over 100 paths.', 'ΔL은 공식 생활권 대비 누락 인구 변화이며 ΔL = 신규 − 해소. 무작위 값은 100개 경로의 중앙값.'))
    r = [[k('Year / chain', '연도 / 연쇄'), k('Maps (unique)', '지도(고유)'), k('Share with L above official', 'L이 공식보다 큰 비율'), k('Median L [2.5%, 97.5%]', 'L 중앙값 [2.5%, 97.5%]'), k('Minimum L', 'L 최솟값'), k('Effective sample size', '유효표본수')]]
    for y in Y:
        e = T[y]['e']; P = T[y]['P']
        for j, (s, v) in enumerate(e['seeds'].items(), 1):
            Es = P[(P.seed == int(s)) & P.plan.str.startswith('E')]
            r.append([f'{y} / {j}', f"{len(Es)} ({Es.hash.nunique()})", f"{v['r_greater']:.3f}", f"{n0(v['L_median'])} [{n0(v['L_p2.5'])}, {n0(v['L_p97.5'])}]", n0(v['L_min']), f"{v['L_ESS']:.0f}"])
    out['T3'] = (k('Table 3. The official plan among alternative maps.', '표 3. 대안 지도 속의 공식 생활권.'), r,
                 k(f"Official L: {V['L20']} (2020), {V['L25']} (2025). Maps are ReCom samples under the ±20% population and compactness rules; they are not a uniform sample. Effective sample size of L adjusts for the similarity of successive maps (Geyer, 1992).",
                   f"공식 L: 2020년 {V['L20']}, 2025년 {V['L25']}. ReCom 표본(인구 ±20%·모양 규칙)이며 균등 표본이 아님. 유효표본수는 앞뒤 지도가 비슷한 정도를 감안한 실질 표본 수(Geyer, 1992)."))
    mm = {y: T[y]['m'] for y in Y}
    r = [[k('Estimate', '추정'), '2020', '2025'],
         [k('Pairs (boundary dongs)', '쌍(경계 동)')] + [f"{mm[y]['n_pairs']} ({mm[y]['n_dongs']})" for y in Y],
         [k('Partial ρ(W, F | A, P)', '편 ρ(W, F | A, P)')] + [f"{f3(mm[y]['partial_W_F_given_AP']['est'])} {ci(*mm[y]['partial_W_F_given_AP']['ci95'])}" for y in Y],
         [k('Partial ρ(W, F | A, P, zone population, zone jobs)', '편 ρ(W, F | A, P, 생활권 인구·종사자)')] + [f"{f3(mm[y]['partial_W_F_given_AP_Zpop_Zemp']['est'])} {ci(*mm[y]['partial_W_F_given_AP_Zpop_Zemp']['ci95'])}" for y in Y],
         [k('Dong fixed effects: standardised coefficient on F', '동 고정효과: F의 표준화 계수')] + [f"{f3(mm[y]['dongFE_std_beta']['F']['est'])} {ci(*mm[y]['dongFE_std_beta']['F']['ci95'])}" for y in Y]]
    out['T4'] = (k('Table 4. Trip shares and walkable facility shares of adjacent zones.', '표 4. 인접 생활권의 통행 비율과 보행 시설 비율.'), r,
                 k('W: share of a boundary dong’s out-of-dong trips ending in the adjacent zone; F: share of its walkable facility cells located there (mean of seven categories); A, P: shares of reachable cells and of the population of reachable cells; F, A and P are all weighted by origin-cell population. Brackets: 95% dong-cluster bootstrap intervals.',
                   'W: 경계 동의 동 밖 통행 중 인접 생활권에서 끝나는 비율, F: 보행 시설 격자 중 그 생활권에 있는 비율(7범주 평균), A·P: 닿는 격자 비율·닿는 격자의 인구 비율. F·A·P 모두 출발 격자 인구로 가중. 괄호는 동 군집 부트스트랩 95% 구간.'))
    return out


AI_DECLARATION = ('During the preparation of this work the authors used Claude (Anthropic) to help write and check the analysis code and to '
                  'draft and edit the text. After using this tool, the authors reviewed and edited the content as needed and take full '
                  'responsibility for the content of the published article.')

SOURCES = {  # (source, 2020 reference / 2025 reference, reconstruction method)
    '유치원': ('Ministry of Education kindergarten disclosure (Yuchiwon Alrimi), basic status', '2nd half 2019 / 2nd half 2024 (1 Oct)', 'A'),
    '학교': ('Seoul Metropolitan Office of Education school list and school-district map', '1 Oct 2019 / 1 Oct 2024; closed and suspended schools excluded', 'A'),
    '청소년수련시설': ('Ministry of Gender Equality and Family, youth facility status', '31 Dec 2019 / 31 Dec 2024; geocoded from addresses', 'C'),
    '어린이집': ('Seoul Open Data OA-20300 (childcare information portal), incl. closed centres', 'licence and closure dates reconstructed; suspended centres excluded', 'B'),
    '노인 이용시설': ('Ministry of Health and Welfare, welfare facilities for older persons', '31 Dec 2019 / 31 Dec 2024; welfare, day and short-stay centres; home-visit services excluded', 'C'),
    '장애인 이용시설': ('Ministry of Health and Welfare, directory of facilities for persons with disabilities', '2020 / 2025 editions (end 2024); community rehabilitation facilities', 'C'),
    '가족센터(자치구 본소)': ('Ministry of Gender Equality and Family, family centre address list', '3 Sep 2019 / 1 Jan 2025; 25 district head offices', 'A'),
    '의원': ('Local licensing data (LocalData) / Seoul Open Data OA-16480', 'open and close dates reconstructed; public health centres and midwifery separated', 'B'),
    '약국': ('LocalData / Seoul Open Data OA-16484', 'open and close dates reconstructed', 'B'),
    '병원급': ('LocalData Seoul (6110000_ALL), hospital-level institutions', 'open and close dates reconstructed; type mapping', 'B'),
    '보건소·보건지소': ('Ministry of Health and Welfare, list of public health institutions', '31 Dec 2019 / 2025 edition (file dated 31 Dec 2025, 12 months after nominal date)', 'C'),
    '응급의료기관': ('National Emergency Medical Center (E-GEN) status', '31 Jan 2020 / 31 Jan 2025; geocoded from addresses', 'A'),
    '산후조리원': ('LocalData / Seoul Open Data OA-16482', 'open and close dates reconstructed', 'B'),
    '공공도서관': ('National Library of Korea, national library statistics', 'year-end 2019 / 2024', 'C'),
    '문화기반시설': ('Ministry of Culture, Sports and Tourism, directory of cultural facilities', '1 Jan 2020 / 1 Jan 2025; may overlap with public libraries', 'A'),
    '등록공연장': ('Ministry of Culture, Sports and Tourism, registered performance venues', '31 Dec 2019 / 31 Dec 2024', 'A'),
    '주민센터': ('Ministry of the Interior and Safety, sub-municipal offices (data.go.kr 15059715)', '30 Jun 2019 / 31 Jul 2024 (outside the nominal window); former and temporary offices partly restored', 'C'),
    '소방서·119안전센터': ('Seoul Fire and Disaster Headquarters, Seoul Open Data OA-21072', '2020 / 2024 annual editions', 'C'),
    '일상소매': ('Small Enterprise and Market Service, commercial district data (15083033), nine everyday-retail subclasses', 'Dec 2019 (regenerated Nov 2025) / Dec 2024; not a complete historical inventory', 'B / A'),
    '식료품소매(즉석판매·제과)': ('LocalData / Seoul Open Data OA-16085, OA-16084', 'open and close dates reconstructed', 'B'),
    '대규모점포(주요4업태)': ('LocalData / Seoul Open Data OA-16096; hypermarkets, department stores, shopping centres, specialty stores', 'open and close dates reconstructed', 'B'),
    '일반음식점': ('LocalData / Seoul Open Data OA-16094', 'open and close dates reconstructed; missing coordinates geocoded', 'B'),
    '휴게음식점': ('LocalData / Seoul Open Data OA-16095', 'open and close dates reconstructed; missing coordinates geocoded', 'B'),
    '미용업': ('LocalData / Seoul Open Data OA-16063', 'open and close dates reconstructed; missing coordinates geocoded', 'B'),
    '이용업': ('LocalData / Seoul Open Data OA-16064', 'open and close dates reconstructed', 'B'),
    '세탁업': ('LocalData / Seoul Open Data OA-16065', 'open and close dates reconstructed', 'B'),
    '목욕장업': ('LocalData / Seoul Open Data OA-16146', 'open and close dates reconstructed', 'B'),
}
TYPE_EN = {'유치원': 'Kindergartens', '학교': 'Schools', '청소년수련시설': 'Youth centres', '어린이집': 'Childcare centres', '노인 이용시설': 'Senior welfare and day centres', '장애인 이용시설': 'Disability community centres',
           '가족센터(자치구 본소)': 'Family centres', '의원': 'Clinics', '약국': 'Pharmacies', '병원급': 'Hospitals', '보건소·보건지소': 'Public health centres', '응급의료기관': 'Emergency medical facilities', '산후조리원': 'Postnatal care centres',
           '공공도서관': 'Public libraries', '문화기반시설': 'Cultural facilities', '등록공연장': 'Registered performance venues', '주민센터': 'Community service centres', '소방서·119안전센터': 'Fire stations and 119 safety centres',
           '일상소매': 'Everyday retail', '식료품소매(즉석판매·제과)': 'Food retail (prepared food, bakeries)', '대규모점포(주요4업태)': 'Large stores', '일반음식점': 'Restaurants', '휴게음식점': 'Cafés and snack bars', '미용업': 'Hair salons', '이용업': 'Barbers', '세탁업': 'Laundries', '목욕장업': 'Public baths'}


def appendix_tables(V, T, lang='en'):
    k = lambda en, ko: en if lang == 'en' else ko  # noqa: E731
    Y = (2020, 2025); out = {}
    r = [[k('Category', '범주'), k('Facility types', '시설 유형'), k('Cells 2020', '격자 2020'), k('Cells 2025', '격자 2025')]]
    for c in CAT:
        r.append([k(CAT_EN[c], c), k(TYPES_EN[c], TYPES_KO[c])] + [n0(T[y]['a']['facility_info']['facility_cells_by_category'][c]) for y in Y])
    out['A1'] = (k('Table A.1. Facility categories and types.', '표 A.1. 시설 범주와 유형.'), r, k('Cells: 100 m cells containing at least one facility of the category.', '격자: 해당 범주 시설이 하나 이상 있는 100 m 격자 수.'))
    r = [[k('Category', '범주'), k('Walkable at all, share of residents 2020', '보행 도달 주민 비율 2020'), k('2025', '2025'), k('Excluded under official plan 2020', '공식 생활권 누락 2020'), k('2025', '2025')]]
    for c in CAT:
        r.append([k(CAT_EN[c], c)] + [pct(T[y]['a']['no_boundary_reach_share'][c]) + '%' for y in Y] + [n0(T[y]['a']['category_omission_LZ'][c]) for y in Y])
    r.append([k('Any category (unique residents)', '어느 범주든(고유 주민)'), '', ''] + [V['L20'], V['L25']])
    out['A2'] = (k('Table A.2. Walkable reach and exclusion by category under the official plan.', '표 A.2. 공식 생활권의 범주별 보행 도달과 누락.'), r, k('A resident is excluded for a category if it is reachable within 15 minutes but not within the resident’s own zone.', '범주가 15분 안에 닿지만 자기 생활권 안에서는 닿지 않으면 그 범주에서 누락.'))
    od = {y: T[y]['od'] for y in Y}; pla = json.load(open(RES / 'appendix' / 'plan_level_association.json', encoding='utf-8'))
    r = [[k('Analysis', '분석'), '2020', '2025', k('Condition tested and reading', '시험 조건과 해석')],
         [k('Modularity reassignment under the ±20% population and compactness rules (end of path)', '인구 ±20%·모양 규칙 아래 모듈성 재배정(경로 끝)')] +
         [f"k = {od[y]['MOD_end']['k']}; ΔL {sgn(od[y]['MOD_end']['dL_unique'])} ({n0(od[y]['MOD_end']['new_excl'])} / {n0(od[y]['MOD_end']['resolved'])})" for y in Y] +
         [k('Population and compactness rules of Section 3.3 applied to each move; summarised in Section 4.2. The rules block most flow-guided moves after the first, so the path is short and its sign differs between years.', '3.3절의 인구·모양 규칙을 매 이동에 적용. 4.2절에 요약. 규칙이 첫 이동 이후 대부분의 통행 기준 이동을 막아 경로가 짧고 부호가 해마다 다름.')],
         [k('Reassignment choosing the move that raises the IFR most (each dong moved at most once)', 'IFR을 가장 많이 올리는 이동부터 고르는 재배정(동당 1회)')] +
         [f"k = {od[y]['IFR_end']['k']}; ΔL {sgn(od[y]['IFR_end']['dL_unique'])}" for y in Y] + [k('Same rules as above, objective IFR instead of modularity, each dong moved at most once. Raising IFR directly raised exclusion in both years.', '위와 같은 규칙, 목적함수는 모듈성 대신 IFR, 동당 최대 1회 이동. IFR을 직접 올리면 두 해 모두 누락 증가.')],
         [k('Plan-level Spearman ρ(IFR, L) across alternative maps, controlling for shape', '대안 지도 전체의 계획 단위 Spearman ρ(IFR, L), 모양 통제')] +
         [f"{f2(pla[str(y)]['L7|shape']['rho'])} {ci(*pla[str(y)]['L7|shape']['ci95'], f=f2)}" for y in Y] + [k('Rank correlation over the 1000 alternative maps of Section 3.3, controlling for shape. Small; reported for completeness.', '3.3절 대안 지도 1000장에 대한 순위상관, 모양 통제. 작음. 기록용.')],
         [k('Paired differences ΔIFR ~ Δaccess between official and flow-based boundaries', '공식–통행 기반 경계의 쌍 차분 ΔIFR ~ Δ접근성')] + ['—', '—'] +
         [k('Earlier design, not pursued: almost all random plans produced the same sign, so the test could not discriminate between plans.', '초기 설계, 미채택: 무작위 계획 거의 전부가 같은 부호를 내어 계획 간 판별력이 없음.')]]
    from study import TYPES
    r4 = [[k('Category', '범주'), k('Type', '유형'), k('Source', '원천 자료'), k('Reference dates and treatment', '기준 시점과 처리'), k('Method', '방법')]]
    for c in CAT:
        for tname in TYPES[c]:
            src, dates, meth = SOURCES[tname]; r4.append([k(CAT_EN[c], c), k(TYPE_EN[tname], tname), src, dates, meth])
    out['A4'] = (k('Table A.6. Facility sources and reconstruction of the 2020 and 2025 inventories.', '표 A.6. 시설 원천 자료와 2020·2025 목록 재구축.'), r4,
                 k('Method: A, snapshot or edition dated at or near the reference date (end of 2019 / end of 2024); B, current licensing history with open and close dates used to reconstruct the stock at the reference date; C, nearest annual or nominal edition. All facilities were assigned to 100 m cells by coordinates; records outside the grid (39 per year) were dropped. Sports businesses were excluded. Source files and retrieval dates are listed in the data package.',
                   '방법: A 기준 시점(2019년 말 / 2024년 말) 근처의 스냅숏·판본, B 현재 인허가 이력의 개폐업일로 기준 시점 재고를 역산, C 가장 가까운 연간·명목 판본. 좌표로 100 m 격자에 배정, 격자 밖 기록(연 39건) 제외, 체육시설업 제외. 원파일·취득일은 자료 패키지에 기록.'))
    out['A3'] = (k('Table A.3. Sensitivity and earlier analyses not reported in full in the main text.', '표 A.3. 본문에 전부 싣지 않은 민감도·초기 분석.'), r,
                 k('All analyses are post hoc. ΔL values give new / resolved in parentheses.', '모든 분석은 사후 분석. 괄호는 신규 / 해소.'))
    a10 = {y: T[y]['a10'] for y in Y}; CK = ['교육', '보육·복지', '의료', '문화', '행정·안전', '소매', '생활서비스']
    r5 = [[k('Category', '범주'), k('Flow-guided 2020', '통행 기준 2020'), k('Random median 2020', '무작위 중앙값 2020'), k('Flow-guided 2025', '통행 기준 2025'), k('Random median 2025', '무작위 중앙값 2025')]]
    for c in CK:
        r5.append([k(CAT_EN[c], c)] + [x for y in Y for x in (sgn(a10[y]['flow_end_minus_official_by_category'][c]), sgn(a10[y]['random_end_minus_official_median_by_category'][c]))])
    r5.append([k('Five categories without culture and civic (unique residents)', '문화·행정·안전을 뺀 5범주(고유 주민)')] + [x for y in Y for x in (sgn(a10[y]['paths']['five']['flow_end']), sgn(a10[y]['paths']['five']['rand_end_median']))])
    r5.append([k('All seven categories (unique residents; Table 2)', '7범주 전체(고유 주민, 표 2)')] + [x for y in Y for x in (sgn(a10[y]['paths']['all7']['flow_end']), sgn(a10[y]['paths']['all7']['rand_end_median']))])
    out['A5'] = (k('Table A.4. Change in excluded residents by category at the end of the reassignment paths.', '표 A.4. 재배정 경로 끝의 범주별 누락 인구 변화.'), r5,
                 k('Change relative to the official plan after all moves (66 in 2020, 65 in 2025). Category rows count residents excluded for that category, so they overlap and do not add up to the unique-resident rows. Random figures are medians over the 100 paths.',
                   '모든 이동 뒤(2020년 66회, 2025년 65회) 공식 생활권 대비 변화. 범주 행은 그 범주에서 누락된 주민 수라 서로 겹치며 고유 주민 행의 합이 아니다. 무작위 값은 100개 경로의 중앙값.'))
    S6 = (('all7', k('All seven categories (main analysis)', '7범주(주분석)')), ('five', k('Five categories (without culture and civic)', '5범주(문화·행정·안전 제외)')),
          ('noC', k('Without the three least precisely dated types', '시점 등급 C 세 유형 제외')))
    r6 = [[k('Measure', '항목')] + [lab for _, lab in S6]]
    for y in Y:
        pa = a10[y]['paths']; en = a10[y]['ensemble']; g_all = T[y]['e']['n_greater']
        r6 += [[k(f'{y}: official plan, excluded residents', f'{y}: 공식 생활권 누락 인구')] + [n0(a10[y]['official_L'][nm]) for nm, _ in S6],
               [k(f'{y}: flow-guided ΔL at end of path', f'{y}: 통행 기준 경로 끝 ΔL')] + [sgn(pa[nm]['flow_end']) for nm, _ in S6],
               [k(f'{y}: random ΔL, median of 100 paths', f'{y}: 무작위 ΔL, 100경로 중앙값')] + [sgn(pa[nm]['rand_end_median']) for nm, _ in S6],
               [k(f'{y}: random paths ending above flow-guided (%)', f'{y}: 통행 기준보다 높게 끝난 무작위 경로(%)')] + [f"{100 * (1 - pa[nm]['rand_end_share_below_flow']):.0f}" for nm, _ in S6],
               [k(f'{y}: flow-guided below all random paths from k =', f'{y}: 통행 기준이 모든 무작위 경로보다 낮아지는 k')] + [str(pa[nm]['first_k_flow_below_all_random'] or '—') for nm, _ in S6],
               [k(f'{y}: alternative maps (of 1000) excluding more than official', f'{y}: 공식보다 누락이 많은 대안 지도(1000장 중)')] + [n0(g_all), n0(en['five']['n_greater']), n0(en['noC']['n_greater'])]]
    out['A6'] = (k('Table A.5. Results under alternative counts of excluded residents.', '표 A.5. 누락 인구를 달리 셌을 때의 결과.'), r6,
                 k('Five categories: residents excluded for at least one of education, childcare and welfare, health, retail and personal services. Without the three least precisely dated types: public libraries, community service centres, and fire stations and 119 safety centres are removed from the inventory (method C in Table A.6), which removes civic and safety services altogether. Paths, random seeds and alternative maps are those of the main analysis. —: no such k.',
                   '5범주: 교육·보육·복지·의료·소매·생활서비스 가운데 하나라도 누락된 주민. 시점 등급 C 세 유형 제외: 공공도서관·주민센터·소방서·119안전센터를 시설 목록에서 뺌(표 A.6의 방법 C). 행정·안전 범주가 통째로 빠진다. 경로·무작위 시드·대안 지도는 주분석과 같다. —: 해당 k 없음.'))
    return out


# ---------------------------------------------------------------- docx helpers
def base_doc(font='Times New Roman', east='Malgun Gothic', size=12, spacing=2.0, lines=True):
    d = Document(); st = d.styles['Normal']; st.font.name = font; st.font.size = Pt(size)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), east); pf = st.paragraph_format; pf.line_spacing = spacing; pf.space_after = Pt(0)
    for s in d.sections:
        s.page_height, s.page_width = Cm(29.7), Cm(21.0); s.left_margin = s.right_margin = Cm(2.5); s.top_margin = s.bottom_margin = Cm(2.5)
        if lines:
            ln = OxmlElement('w:lnNumType'); ln.set(qn('w:countBy'), '1'); ln.set(qn('w:restart'), 'continuous'); ln.set(qn('w:distance'), '360'); s._sectPr.append(ln)
        fp = s.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER; _field(fp, 'PAGE')
    return d


def _field(p, code):
    r = p.add_run(); a = OxmlElement('w:fldChar'); a.set(qn('w:fldCharType'), 'begin'); r._r.append(a)
    t = OxmlElement('w:instrText'); t.set(qn('xml:space'), 'preserve'); t.text = code; r._r.append(t)
    b = OxmlElement('w:fldChar'); b.set(qn('w:fldCharType'), 'end'); r._r.append(b)


def para(d, text, bold=False, italic=False, align=None, size=None, indent=True, space_before=0):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(space_before)
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.75)
    if align:
        p.alignment = align
    r = p.add_run(text); r.bold = bold; r.italic = italic
    if size:
        r.font.size = Pt(size)
    return p


def caption_para(d, cap, size=None, space_before=0):
    """AG 게재본(Kang & Eom 2026 등) 관례.
    표: 'Table 1'(굵게, 마침표 없음) 줄바꿈 후 제목(보통 글씨, 문장형, 마침표). 그림: 'Fig. 1.'(굵게) 뒤에 같은 줄로 제목."""
    m = re.match(r'^((?:Table|Fig\.|표|그림) \S+?)\.\s', cap)
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(space_before)
    if not m:
        r = p.add_run(cap)
        if size:
            r.font.size = Pt(size)
        return p
    is_table = cap.startswith(('Table', '표'))
    label = m.group(1) if is_table else m.group(1) + '.'
    r = p.add_run(label); r.bold = True
    if size:
        r.font.size = Pt(size)
    if is_table:
        r.add_break()
    r2 = p.add_run(cap[m.end():] if is_table else ' ' + cap[m.end():])
    if size:
        r2.font.size = Pt(size)
    return p


def heading(d, text, level):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(12 if level == 1 else 6); p.paragraph_format.keep_with_next = True
    r = p.add_run(text); r.bold = True; r.italic = level == 2
    return p


def _cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr(); b = tcPr.find(qn('w:tcBorders'))
    if b is None:
        b = OxmlElement('w:tcBorders'); tcPr.append(b)
    for edge, val in kw.items():
        el = OxmlElement(f'w:{edge}'); el.set(qn('w:val'), val); el.set(qn('w:sz'), '4'); el.set(qn('w:color'), '000000'); b.append(el)


def table(d, cap, rows, note, size=9):
    p = caption_para(d, cap, space_before=6); p.paragraph_format.keep_with_next = True; p.paragraph_format.line_spacing = 1.0
    t = d.add_table(rows=len(rows), cols=len(rows[0])); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    tb = OxmlElement('w:tblBorders')  # 표 단위 선은 모두 없앰(세로선·안쪽선 없음); 가로선 3개는 셀 단위로만 그림
    for e in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{e}'); el.set(qn('w:val'), 'nil'); tb.append(el)
    t._tbl.tblPr.append(tb)
    W = {3: [7.0, 4.5, 4.5], 4: ([3.3, 8.3, 2.2, 2.2] if 'A.1' in cap else [6.4, 3.2, 3.2, 3.2] if 'A.5' in cap else [5.2, 3.2, 3.2, 4.4]), 5: ([1.9, 2.5, 5.0, 4.9, 1.7] if 'A.6' in cap else [4.0, 3.0, 3.0, 3.0, 3.0]), 6: [2.0, 2.2, 2.3, 4.7, 2.4, 2.4]}[len(rows[0])]
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.width = Cm(W[j]); c.text = ''; pp = c.paragraphs[0]; pp.paragraph_format.line_spacing = 1.0; rr = pp.add_run(str(v)); rr.font.size = Pt(size)  # 머리행도 보통 글씨(AG 게재본)
            if i == 0:
                pp.paragraph_format.keep_with_next = True
            pp.alignment = WD_ALIGN_PARAGRAPH.LEFT  # AG 게재본: 숫자 열 포함 모든 칸 왼쪽 정렬
            _cell_border(c, top='single' if i == 0 else 'nil', bottom='single' if i in (0, len(rows) - 1) else 'nil', left='nil', right='nil')
        trPr = t.rows[i]._tr.get_or_add_trPr(); cs = OxmlElement('w:cantSplit'); trPr.append(cs)
        if i == 0:
            th = OxmlElement('w:tblHeader'); trPr.append(th)
    if note:  # AG 관례: 표 아래 'Note:'로 시작(한국어판 '주:')
        q = para(d, ('주: ' if cap.startswith('표') else 'Note: ') + note, indent=False, size=9); q.paragraph_format.line_spacing = 1.0
    d.add_paragraph()


def figure(d, key, cap, width=15.5):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing = 1.0; p.add_run().add_picture(str(FIG / f'{key}.png'), width=Cm(width))
    q = caption_para(d, cap, size=10); q.paragraph_format.line_spacing = 1.0; d.add_paragraph()


def math_para(d, text, lang='en', indent=True):
    p = d.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.75)
    return MATH.math_paragraph(p, text, lang)


def render(blocks, V, TB, caps, d, lang='en'):
    for kind, x in blocks:
        if kind == 'h1':
            heading(d, x, 1)
        elif kind == 'h2':
            heading(d, x, 2)
        elif kind == 'p':
            math_para(d, x.format_map(V), lang)
        elif kind == 'pc':
            math_para(d, x.format_map(V), lang, indent=False)
        elif kind == 'eq':
            MATH.display_equation(d, x, lang)
        elif kind == 'table':
            table(d, *TB[x])
        elif kind == 'fig':
            figure(d, x, caps[x], width=15.5 if x != 'Fig4' else 11)


REFS = [
    'Alexander, L., Jiang, S., Murga, M., & González, M. C. (2015). Origin–destination trips by purpose and time of day inferred from mobile phone data. Transportation Research Part C: Emerging Technologies, 58, 240–250. https://doi.org/10.1016/j.trc.2015.02.018',
    'Allam, Z., Nieuwenhuijsen, M., Chabaud, D., & Moreno, C. (2022). The 15-minute city offers a new framework for sustainability, liveability, and health. The Lancet Planetary Health, 6(3), e181–e183. https://doi.org/10.1016/S2542-5196(22)00014-6',
    'Boyne, G., & Powell, M. (1991). Territorial justice: A review of theory and evidence. Political Geography Quarterly, 10(3), 263–281. https://doi.org/10.1016/0260-9827(91)90038-V',
    'Chen, J., & Rodden, J. (2013). Unintentional gerrymandering: Political geography and electoral bias in legislatures. Quarterly Journal of Political Science, 8(3), 239–269. https://doi.org/10.1561/100.00012033',
    'Coombes, M., & Bond, S. (2008). Travel-to-work areas: The 2007 review. Office for National Statistics.',
    'Coombes, M. G., Green, A. E., & Openshaw, S. (1986). An efficient algorithm to generate official statistical reporting areas: The case of the 1984 travel-to-work-areas revision in Britain. Journal of the Operational Research Society, 37(10), 943–953. https://doi.org/10.1057/jors.1986.163',
    'DeFord, D., Duchin, M., & Solomon, J. (2021). Recombination: A family of Markov chains for redistricting. Harvard Data Science Review, 3(1). https://doi.org/10.1162/99608f92.eb30390f',
    'Farmer, C. J. Q., & Fotheringham, A. S. (2011). Network-based functional regions. Environment and Planning A, 43(11), 2723–2741. https://doi.org/10.1068/a44136',
    'Fotheringham, A. S., & Wong, D. W. S. (1991). The modifiable areal unit problem in multivariate statistical analysis. Environment and Planning A, 23(7), 1025–1044. https://doi.org/10.1068/a231025',
    'Gao, F., Kihal, W., Le Meur, N., Souris, M., & Deguen, S. (2017). Does the edge effect impact on the measure of spatial accessibility to healthcare providers? International Journal of Health Geographics, 16, Article 46. https://doi.org/10.1186/s12942-017-0119-3',
    'Geurs, K. T., & van Wee, B. (2004). Accessibility evaluation of land-use and transport strategies: Review and research directions. Journal of Transport Geography, 12(2), 127–140. https://doi.org/10.1016/j.jtrangeo.2003.10.005',
    'Geyer, C. J. (1992). Practical Markov chain Monte Carlo. Statistical Science, 7(4), 473–483. https://doi.org/10.1214/ss/1177011137',
    'Graells-Garrido, E., Serra-Burriel, F., Rowe, F., Cucchietti, F. M., & Reyes, P. (2021). A city of cities: Measuring how 15-minutes urban accessibility shapes human mobility in Barcelona. PLoS ONE, 16(5), Article e0250080. https://doi.org/10.1371/journal.pone.0250080',
    'Greater London Authority. (2016). The London Plan: The spatial development strategy for London consolidated with alterations since 2011 (Policy 2.5, Sub-regions). Greater London Authority. https://www.london.gov.uk/',
    'Greater Sydney Commission. (2018). Greater Sydney Region Plan: A metropolis of three cities. Government of New South Wales. https://www.planning.nsw.gov.au/',
    'Halás, M., Klapka, P., Tonev, P., & Bednář, M. (2015). An alternative definition and use for the constraint function for rule-based methods of functional regionalisation. Environment and Planning A, 47(5), 1175–1191. https://doi.org/10.1177/0308518X15592306',
    'Handy, S. L., & Niemeier, D. A. (1997). Measuring accessibility: An exploration of issues and alternatives. Environment and Planning A, 29(7), 1175–1194. https://doi.org/10.1068/a291175',
    'Hansen, W. G. (1959). How accessibility shapes land use. Journal of the American Institute of Planners, 25(2), 73–76. https://doi.org/10.1080/01944365908978307',
    'He, M., Glasser, J., Pritchard, N., Bhamidi, S., & Kaza, N. (2020). Demarcating geographic regions using community detection in commuting networks with significant self-loops. PLoS ONE, 15(4), Article e0230941. https://doi.org/10.1371/journal.pone.0230941',
    'Herschlag, G., Kang, H. S., Luo, J., Graves, C. V., Bangia, S., Ravier, R., & Mattingly, J. C. (2020). Quantifying gerrymandering in North Carolina. Statistics and Public Policy, 7(1), 30–38. https://doi.org/10.1080/2330443X.2020.1796400',
    'Hillsman, E. L., & Rhoda, R. (1978). Errors in measuring distances from populations to service centers. The Annals of Regional Science, 12(3), 74–88. https://doi.org/10.1007/BF01286124',
    'Kalcsics, J., Nickel, S., & Schröder, M. (2005). Towards a unified territorial design approach: Applications, algorithms and GIS integration. TOP, 13(1), 1–56. https://doi.org/10.1007/BF02578982',
    'Karlsson, C., & Olsson, M. (2006). The identification of functional regions: Theory, methods, and applications. The Annals of Regional Science, 40(1), 1–18. https://doi.org/10.1007/s00168-005-0019-5',
    'Klapka, P., Kraft, S., & Halás, M. (2020). Network based definition of functional regions: A graph theory approach for spatial distribution of traffic flows. Journal of Transport Geography, 88, Article 102855. https://doi.org/10.1016/j.jtrangeo.2020.102855',
    'Kwan, M.-P. (2012). The uncertain geographic context problem. Annals of the Association of American Geographers, 102(5), 958–968. https://doi.org/10.1080/00045608.2012.687349',
    'Logan, T. M., Hobbs, M. H., Conrow, L. C., Reid, N. L., Young, R. A., & Anderson, M. J. (2022). The x-minute city: Measuring the 10, 15, 20-minute city and an evaluation of its use for sustainable urban design. Cities, 131, Article 103924. https://doi.org/10.1016/j.cities.2022.103924',
    'Martínez-Bernabéu, L., & Casado-Díaz, J. M. (2021). Standard modularity is unsuitable for functional regionalization of spatial interaction data. Papers in Regional Science, 100(5), 1323–1331. https://doi.org/10.1111/pirs.12617',
    'Moreno, C., Allam, Z., Chabaud, D., Gall, C., & Pratlong, F. (2021). Introducing the “15-minute city”: Sustainability, resilience and place identity in future post-pandemic cities. Smart Cities, 4(1), 93–111. https://doi.org/10.3390/smartcities4010006',
    'Mouratidis, K. (2024). Time to challenge the 15-minute city: Seven pitfalls for sustainability, equity, livability, and spatial analysis. Cities, 153, Article 105274. https://doi.org/10.1016/j.cities.2024.105274',
    'Newman, M. E. J. (2006). Modularity and community structure in networks. Proceedings of the National Academy of Sciences, 103(23), 8577–8582. https://doi.org/10.1073/pnas.0601602103',
    'Olson, M. (1969). The principle of “fiscal equivalence”: The division of responsibilities among different levels of government. American Economic Review, 59(2), 479–487.',
    'Openshaw, S. (1984). The modifiable areal unit problem. Concepts and Techniques in Modern Geography 38. Geo Books.',
    'Openshaw, S., & Rao, L. (1995). Algorithms for reengineering 1991 census geography. Environment and Planning A, 27(3), 425–446. https://doi.org/10.1068/a270425',
    'Páez, A., Scott, D. M., & Morency, C. (2012). Measuring accessibility: Positive and normative implementations of various accessibility indicators. Journal of Transport Geography, 25, 141–153. https://doi.org/10.1016/j.jtrangeo.2012.03.016',
    'Park, J., Eom, S., & Lee, M.-H. (2026). Benchmarking living-zone plans with mobility community detection: Evidence from Seoul’s mobile-phone-based mobility data. Journal of Transport Geography, 135, Article 104753. https://doi.org/10.1016/j.jtrangeo.2026.104753',
    'Park, Y., & Rogers, G. O. (2015). Neighborhood planning theory, guidelines, and research: Can area, population, and boundary guide conceptual framing? Journal of Planning Literature, 30(1), 18–36. https://doi.org/10.1177/0885412214549422',
    'Perry, C. A. (1929). The neighborhood unit. In Regional survey of New York and its environs, Vol. VII: Neighborhood and community planning. Regional Plan of New York and Its Environs.',
    'Polsby, D. D., & Popper, R. D. (1991). The third criterion: Compactness as a procedural safeguard against partisan gerrymandering. Yale Law & Policy Review, 9(2), 301–353.',
    'Ratti, C., Sobolevsky, S., Calabrese, F., Andris, C., Reades, J., Martino, M., Claxton, R., & Strogatz, S. H. (2010). Redrawing the map of Great Britain from a network of human interactions. PLoS ONE, 5(12), Article e14248. https://doi.org/10.1371/journal.pone.0014248',
    'Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen. (2021). Lebensweltlich orientierte Räume (LOR) in Berlin [Lifeworld-oriented spaces (LOR) in Berlin]. https://www.berlin.de/sen/stadt/stadtdaten/stadtwissen/sozialraumorientierte-planungsgrundlagen/lebensweltlich-orientierte-raeume/',
    'Seoul Metropolitan Government. (2018). 2030 Seoul living-zone plan [in Korean]. Seoul Urban Planning Portal. https://urban.seoul.go.kr/view/html/PMNU3040000001',
    'Shen, Y., & Batty, M. (2019). Delineating the perceived functional regions of London from commuting flows. Environment and Planning A: Economy and Space, 51(3), 547–550. https://doi.org/10.1177/0308518X18786253',
    'Smart, M. W. (1974). Labour market areas: Uses and definition. Progress in Planning, 2, 239–353. https://doi.org/10.1016/0305-9006(74)90008-7',
    'Staricco, L. (2022). 15-, 10- or 5-minute city? A focus on accessibility to services in Turin, Italy. Journal of Urban Mobility, 2, Article 100030. https://doi.org/10.1016/j.urbmob.2022.100030',
    'Talen, E. (2003). Neighborhoods as service providers: A methodology for evaluating pedestrian access. Environment and Planning B: Planning and Design, 30(2), 181–200. https://doi.org/10.1068/b12977',
    'Talen, E., & Anselin, L. (1998). Assessing spatial equity: An evaluation of measures of accessibility to public playgrounds. Environment and Planning A, 30(4), 595–613. https://doi.org/10.1068/a300595',
    'Tao, Z., Cheng, Y., Zheng, Q., & Li, G. (2018). Measuring spatial accessibility to healthcare services with constraint of administrative boundary: A case study of Yanqing District, Beijing, China. International Journal for Equity in Health, 17, Article 7. https://doi.org/10.1186/s12939-018-0720-5',
    'Traag, V. A., Waltman, L., & van Eck, N. J. (2019). From Louvain to Leiden: Guaranteeing well-connected communities. Scientific Reports, 9, Article 5233. https://doi.org/10.1038/s41598-019-41695-z',
    'Wang, C., Wang, F., & Onega, T. (2021). Network optimization approach to delineating health care service areas: Spatially constrained Louvain and Leiden algorithms. Transactions in GIS, 25(2), 1065–1081. https://doi.org/10.1111/tgis.12722',
    'Weng, M., Ding, N., Li, J., Jin, X., Xiao, H., He, Z., & Su, S. (2019). The 15-minute walkable neighborhoods: Measurement, social inequalities and implications for building healthy communities in urban China. Journal of Transport & Health, 13, 259–273. https://doi.org/10.1016/j.jth.2019.05.005',
    'Willberg, E., Fink, C., & Toivonen, T. (2023). The 15-minute city for all? – Measuring individual and temporal variations in walking accessibility. Journal of Transport Geography, 106, Article 103521. https://doi.org/10.1016/j.jtrangeo.2022.103521',
]


def ref_keys():
    """참고문헌 항목 → 본문 인용 형태(첫 저자 성, 연도) 목록."""
    out = []
    for r in REFS:
        first = r.split(',')[0].strip(); yr = re.search(r'\((\d{4})\)', r).group(1); out.append((first, yr, r))
    return out


def check_citations(text):
    cites = set(re.findall(r'([A-Z][A-Za-zÀ-ſ\-]+)(?: et al\.| and [A-Z][A-Za-zÀ-ſ\-]+| & [A-Z][A-Za-zÀ-ſ\- ]+?)?,? \(?(\d{4})\)?', text))
    keys = ref_keys(); missing_in_refs = []; unused = []
    for first, yr, r in keys:
        if not re.search(re.escape(first.split(' ')[0]) + r'[^()]{0,90}?\(?' + yr, text):
            unused.append(r[:60])
    return unused


def body_text(blocks, V):
    return ' '.join(x.format_map(V) if k in ('p', 'pc') else x for k, x in blocks if k in ('p', 'pc', 'h1', 'h2', 'eq'))


def words(s):
    return len(re.findall(r'\S+', s))


def main():
    V, T = values(); TB = tables(V, T, 'en'); TBk = tables(V, T, 'ko'); AP = appendix_tables(V, T, 'en'); APk = appendix_tables(V, T, 'ko')
    for h in EN.HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    assert len(EN.KEYWORDS) <= 7
    btxt = body_text(EN.BODY, V); unused = check_citations(btxt + ' ' + ' '.join(TB['T3'][2:3]))
    assert not unused, unused
    # 익명 원고
    d = base_doc(); para(d, EN.TITLE, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=14); d.add_paragraph()
    heading(d, 'Abstract', 1); para(d, EN.ABSTRACT, indent=False)
    para(d, 'Keywords: ' + '; '.join(EN.KEYWORDS), indent=False, space_before=6)
    render(EN.BODY, V, TB, EN.CAPTIONS, d)
    heading(d, 'Declaration of generative AI and AI-assisted technologies in the manuscript preparation process', 1)
    para(d, AI_DECLARATION, indent=False)
    heading(d, 'Data availability', 1); para(d, 'All input datasets are publicly available from their providers. The facility inventory, derived results and analysis code are available in a public repository; the link is given on the title page.', indent=False)
    heading(d, 'References', 1)
    for r in REFS:
        p = para(d, r, indent=False); p.paragraph_format.left_indent = Cm(0.75); p.paragraph_format.first_line_indent = Cm(-0.75)
    d.save(MS / 'AG_manuscript_anonymised.docx')
    # 제목 면
    d = base_doc(lines=False); para(d, EN.TITLE, bold=True, indent=False, size=14); d.add_paragraph()
    for s in ['Jongha Park a (ORCID 0009-0004-8411-6509), daniel21c@hanyang.ac.kr', 'Sunyong Eom a,* (ORCID 0000-0002-8164-7097), sunyongeom@hanyang.ac.kr',
              'a Graduate School of Urban Studies, Hanyang University, 222 Wangsimni-ro, Seongdong-gu, Seoul 04763, Republic of Korea',
              '* Corresponding author. E-mail: sunyongeom@hanyang.ac.kr']:
        para(d, s, indent=False)
    heading(d, 'Declaration of competing interest', 1); para(d, 'The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.', indent=False)
    heading(d, 'Funding', 1); para(d, 'This work was supported by the research fund of Hanyang University (HY-202400000003290).', indent=False)
    heading(d, 'Acknowledgements', 1); para(d, 'None.', indent=False)
    heading(d, 'CRediT authorship contribution statement', 1)
    para(d, 'Jongha Park: Conceptualization, Methodology, Software, Data curation, Formal analysis, Investigation, Validation, Visualization, Writing – original draft, Writing – review & editing. Sunyong Eom: Conceptualization, Methodology, Supervision, Funding acquisition, Writing – review & editing.', indent=False)
    heading(d, 'Data and code availability', 1); para(d, 'Facility inventory, derived results and analysis code: https://github.com/daniel21c/research-workspace (folder 03_불일치_접근성_AG).', indent=False)
    heading(d, 'Declaration of generative AI', 1); para(d, 'See the declaration section at the end of the main text (before the references).', indent=False)
    d.save(MS / 'AG_title_page.docx')
    d = base_doc(lines=False); heading(d, 'Highlights', 1)
    for h in EN.HIGHLIGHTS:
        para(d, '• ' + h, indent=False)
    d.save(MS / 'AG_highlights.docx')
    # 부록
    d = base_doc(lines=False); para(d, 'Supplementary material', bold=True, indent=False, size=14); para(d, EN.TITLE, italic=True, indent=False); d.add_paragraph()
    heading(d, 'Appendix A. Facility inventory, exclusion by category and analyses not reported in the main text', 1)
    for key in ('A1', 'A2', 'A3', 'A5', 'A6', 'A4'):  # 표시 번호 A.1~A.6 순서(A5=A.4, A6=A.5, A4=A.6)
        table(d, *AP[key])
    para(d, 'Chain diagnostics. In Jongno, Jung, Seodaemun and Geumcheon the size and compactness rules admit very few partitions. Exhaustive enumeration of valid partitions (without looking at any outcome) found 4, 5–6, 1–2 and 7–8 partitions respectively, depending on the year. The chains visited every enumerated partition except the single alternative for Seodaemun in 2020. In the other 21 gu each chain saved at least ' + V['minstates'] + ' distinct states.', indent=False)
    d.save(MS / 'AG_supplementary_appendix.docx')
    # 투고 편지
    d = base_doc(lines=False, spacing=1.15)
    for s in ['Dear Editor,', '',
              f'We submit the manuscript “{EN.TITLE}” for consideration as a research article in Applied Geography.',
              'Cities that plan by living zones are being urged to redraw them with mobility data. The paper asks whether doing so keeps residents’ walkable services inside their zones, a consequence of boundary revision that flow-based delineation does not measure. Using Seoul’s official living-zone plan at two points in time, we compare flow-guided reassignment of boundary dongs with random reassignment of the same extent, place the official plan among size- and shape-matched alternative maps generated with a redistricting ensemble method, and test whether trips from boundary dongs go where walkable facilities are. In Seoul, following trips raised self-containment and lowered total exclusion from within-zone walkable services, mainly in culture and civic services, while random moves of the same extent raised it every time. We think the combination of an explicit coverage measure and explicit baselines will interest readers working on accessibility, functional regions and planning geography.',
              'The manuscript has not been published and is not under consideration elsewhere. A companion paper in preparation for a Korean planning journal uses the same mobility data to study how the mismatch between official zones and trips changed between 2020 and 2025; it does not examine facilities or accessibility, and its questions and results do not overlap with this submission. We have not cited it to preserve anonymity and because it has not yet been submitted.',
              'Both authors have approved the manuscript and agree with its submission. There are no competing interests.', '', 'Sincerely,', 'Jongha Park and Sunyong Eom (corresponding author, sunyongeom@hanyang.ac.kr)', 'Graduate School of Urban Studies, Hanyang University']:
        para(d, s, indent=False)
    d.save(MS / 'AG_cover_letter.docx')
    # 한국어 전문
    d = base_doc(font='Malgun Gothic', east='Malgun Gothic', size=10.5, spacing=1.5, lines=False)
    para(d, KO.TITLE, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, size=14); d.add_paragraph()
    heading(d, '초록', 1); para(d, KO.ABSTRACT, indent=False); para(d, '주제어: ' + ', '.join(KO.KEYWORDS), indent=False, space_before=6)
    heading(d, '연구 하이라이트(영문 원고용 번역)', 1)
    for h in ['경계 동을 통행을 따라 재배정하면 생활권 안 보행 시설 누락의 총량이 줄었다', '같은 규모의 무작위 재배정은 모의 경로 전부에서 서비스를 밖으로 밀어냈다',
              '감소는 문화·행정·안전에서 나왔고, 나머지 범주는 늘었지만 무작위보다 덜 늘었다', '서울 공식 생활권은 규모·모양을 맞춘 대안 지도 거의 전부보다 낫다', '경계 동의 통행은 걸어서 닿는 의료·소매·생활서비스가 있는 곳으로 간다']:
        para(d, '• ' + h, indent=False)
    d.add_page_break(); render(KO.BODY, V, TBk, KO.CAPTIONS, d, lang='ko')
    heading(d, '부록 A', 1)
    for key in ('A1', 'A2', 'A3', 'A5', 'A6', 'A4'):
        table(d, *APk[key])
    heading(d, '생성형 AI 사용 고지(영문 원고 본문 끝의 절)', 1); para(d, '이 연구를 준비하면서 저자들은 분석 코드 작성·점검과 본문 초안 작성·수정에 Claude(Anthropic)를 사용했다. 사용 후 저자들이 내용을 검토·수정했으며 출판물의 내용에 전적으로 책임진다.', indent=False)
    heading(d, '참고문헌', 1)
    for r in REFS:
        p = para(d, r, indent=False, size=9.5); p.paragraph_format.left_indent = Cm(0.75); p.paragraph_format.first_line_indent = Cm(-0.75)
    d.save(MS / 'AG_한국어_원고.docx')
    # 기록
    tab_words = sum(words(' '.join(map(str, sum(TB[k][1], [])))) + words(TB[k][0]) + words(TB[k][2]) for k in TB)
    wc = {'abstract': words(EN.ABSTRACT), 'body_incl_headings': words(btxt), 'figure_captions': words(' '.join(EN.CAPTIONS.values())), 'tables': tab_words,
          'references': words(' '.join(REFS)), 'n_references': len(REFS)}
    wc['ai_declaration'] = words(AI_DECLARATION)
    wc['total_AG_count(abstract+body+tables+captions+declaration+references)'] = wc['abstract'] + wc['body_incl_headings'] + wc['tables'] + wc['figure_captions'] + wc['ai_declaration'] + wc['references']
    (MS / 'word_count.json').write_text(json.dumps(wc, indent=1), encoding='utf-8')
    (MS / 'values_used.json').write_text(json.dumps({k: v for k, v in V.items()}, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(json.dumps(wc))


if __name__ == '__main__':
    main()
