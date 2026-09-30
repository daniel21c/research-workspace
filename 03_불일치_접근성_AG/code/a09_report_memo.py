# -*- coding: utf-8 -*-
"""교수님 보고용 2쪽 메모(한국어 docx). 수치는 results/에서 읽는다.
실행: python code/a09_report_memo.py     출력: manuscript/AG_교수님보고_20260930.docx (+ Downloads 사본은 호출자가 복사)
"""
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

AG = Path(__file__).resolve().parents[1]; RES = AG / 'results'; MS = AG / 'manuscript'; FIG = MS / 'figures'
COMMIT = '73be023'; REPO = 'https://github.com/daniel21c/research-workspace'


def n0(x):
    return f'{int(round(float(x))):,}'


def sgn(x):
    x = int(round(float(x))); return ('+' if x > 0 else '−' if x < 0 else '') + f'{abs(x):,}'


def main():
    A = {y: json.load(open(RES / str(y) / 'a01_summary.json', encoding='utf-8')) for y in (2020, 2025)}
    E = {y: json.load(open(RES / str(y) / 'a03_ensemble_summary.json', encoding='utf-8')) for y in (2020, 2025)}
    M = {y: json.load(open(RES / str(y) / 'a04_mechanism_summary.json', encoding='utf-8')) for y in (2020, 2025)}
    C = {y: json.load(open(RES / 'appendix' / f'constrained_paths_summary_{y}.json', encoding='utf-8')) for y in (2020, 2025)}
    end = {y: A[y]['curve'][-1] for y in (2020, 2025)}
    d = Document(); st = d.styles['Normal']; st.font.name = 'Malgun Gothic'; st.font.size = Pt(10); st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Malgun Gothic')
    st.paragraph_format.space_after = Pt(3); st.paragraph_format.line_spacing = 1.15
    for s in d.sections:
        s.left_margin = s.right_margin = Cm(2.0); s.top_margin = s.bottom_margin = Cm(1.8)

    def H(t, lv=1):
        p = d.add_paragraph(); r = p.add_run(t); r.bold = True; r.font.size = Pt(12 if lv == 1 else 10.5); p.paragraph_format.space_before = Pt(8 if lv == 1 else 4)

    def P(t):
        d.add_paragraph(t)

    def B(items):
        for t in items:
            p = d.add_paragraph(style='List Bullet'); p.add_run(t)

    def T(rows, widths):
        t = d.add_table(rows=len(rows), cols=len(rows[0])); t.style = 'Table Grid'
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ''; r = c.paragraphs[0].add_run(str(v)); r.font.size = Pt(9); r.bold = i == 0
                c.paragraphs[0].paragraph_format.space_after = Pt(0)
        d.add_paragraph()

    p = d.add_paragraph(); r = p.add_run('연구3 (AG) 투고 준비 보고 — 통행을 따라 고친 생활권 경계는 걸어서 쓰는 시설을 안에 남기는가'); r.bold = True; r.font.size = Pt(14)
    P('2026-09-30 · 박종하(1저자), 엄선용(교신) · 투고 대상 Applied Geography · 박사논문 4장 3절')
    P('영문 제목: Following trips, keeping services? Mobility-guided revision of neighbourhood planning zones and within-zone walkable service coverage in Seoul')

    H('1. 한 문단 요약')
    P('생활권을 이동 자료로 다시 그리자는 요구가 커지고 있지만, 생활권은 일상 서비스를 세고 약속하는 단위이기도 해서 통행을 따라 그은 경계가 걸어서 닿는 시설을 밖에 남길 수 있다. '
      '서울 공식 생활권 116개와 424개 동을 대상으로 2020·2025년 두 시점에 휴대전화 OD, 직접 구축한 시설 27종(7범주), OSM 보행망을 결합해, "어떤 범주의 시설에 15분 안에 걸어서 닿지만 자기 생활권 안에서는 닿지 못하는 주민 수(L)"를 잰다. '
      f'경계 동을 무작위로 재배정한 100경로는 경로 끝에서 L을 모두 늘렸고(중앙값 2020 {sgn(end[2020]["rand_median"])}명, 2025 {sgn(end[2025]["rand_median"])}명), 같은 횟수의 통행 기준(모듈성) 재배정은 L을 줄였다({sgn(end[2020]["flow_dL"])} / {sgn(end[2025]["flow_dL"])}명; 생활권 수 고정, 인구·형상 조밀도 제약 없음). '
      f'공식 생활권은 규모·형상을 맞춘 대안 지도 1,000장 중 {E[2020]["n_greater"]}장(2020)·{E[2025]["n_greater"]}장(2025)보다 L이 적었다. '
      f'경계 동의 통행은 걸어서 닿는 시설이 더 많은 인접 생활권으로 향했다(편상관 {M[2020]["partial_W_F_given_AP"]["est"]:.2f} / {M[2025]["partial_W_F_given_AP"]["est"]:.2f}). '
      '결론: 경계를 고칠 때 통행 포착과 서비스 포착을 함께 점검해야 하며, 경계 조정이 전면 재설계보다 나은지는 이 연구에서 검증하지 않았다.')

    H('2. 논지 프로세스')
    B(['전제(연구1에서 빌림): 생활권은 하루치 일상 서비스를 묶음으로 공급·약속하는 단위다. 그러므로 "시설이 생활권 안에 있는가"는 경계의 속성이다.',
       '문제: 기능지역·커뮤니티 탐지 문헌은 경계를 "통행을 얼마나 담나"로만 평가한다(자족성). 접근성 문헌은 경계를 측정 오차(MAUP·UGCoP)로만 다룬다. 경계를 통행으로 고치면 서비스 포착이 어떻게 되는지는 아무도 보지 않았다.',
       '질문 1: 경계 동을 통행을 따라 재배정하면, 같은 횟수의 무작위 재배정과 비교해 L이 늘어나나 줄어드나? → 무작위는 늘리고 통행 기준은 줄인다(두 해).',
       '질문 2: 공식 생활권은 같은 규모·형상 규칙을 따르는 대안 지도 속에서 어디에 있나? → 표본 대안 거의 전부보다 L이 적다. 공식안은 변경안을 평가하는 기준점이 된다(조정 vs 전면 재설계의 우열은 비교하지 않았음).',
       '질문 3: 통행과 시설은 같은 곳을 가리키는가(공존)? 경계 동의 통행이 향하는 인접 생활권에 그 동이 걸어서 쓰는 시설이 더 많다(의료·소매·생활서비스에서 양, 교육·보육에서는 0 근처). 앞의 두 결과와 부합하는 기술적 맥락이며 기제 입증은 아니다.',
       '조건과 한계를 본문에 명시: 인구·형상 조밀도 제약을 함께 걸면 2025년에는 통행 기준 경로도 L을 늘림 → 결과는 시험한 규칙·제약에 한정. 대안 지도는 균등 표본 아님. 사후 분석. 인과 아님.',
       '박사논문 흐름: 4.1 생활권 = 묶음 공급 단위 → 4.2(JTG) 통행으로 경계를 도출하고 공식안을 점검 → 4.3(AG) 통행으로 고쳐도 서비스가 남는가 → 4.4(KPA) 불일치의 시간 변화와 경계 동 재배정.',
       '원고 구성(JTG 게재본과 같은 5장 구조): 1 서론(생활권 개념·세계 동향·문제·Q1~Q3) → 2 선행연구(2.1 공통, 2.2~2.4 = Q1~Q3, 2.5 공백·질문) → 3 자료와 방법(3.1 공통, 3.2~3.4 = Q1~Q3) → 4 결과(4.1 기준값, 4.2~4.4 = Q1~Q3) → 5 논의와 결론(5.1~5.3 = Q1~Q3, 5.4 함의·한계·결론). 각 질문을 같은 번호로 따라갈 수 있다.'])

    H('3. 분석의 틀')
    T([['구성', '내용'],
       ['입력(연도마다 고정)', '424동(2023-07 경계), 공식 116생활권, 서울 생활이동 OD 2020·2025년 1월(09–20시 도착, 집–직장 제외, 자기 동 포함), SGIS 100 m 인구(2019·2024), 시설 27종 7범주(교육·보육복지·의료·문화·행정안전·소매·생활서비스; 체육시설업 제외), OSM 보행망 4 km/h 15분'],
       ['지표 1: IFR', '같은 생활권 안에서 시작해 끝나는 통행 비율(자족성)'],
       ['지표 2: L', '어떤 범주 시설에 15분 안에 걸어서 닿지만 자기 생활권 안에서는 닿지 않는 고유 주민 수. 계획 회계 개념(실제 이용·후생 아님). ΔL = 신규 누락 − 해소'],
       ['비교 기준 (a)', '경계 동 무작위 재배정 100경로(통행 기준 경로와 같은 구 순서·같은 횟수), 매 단계 평가'],
       ['비교 기준 (b)', '규모(구별 정렬 인구 ±20%)·형상 조밀도(Polsby–Popper 95%)를 맞춘 대안 생활권 지도 1,000장 — 선거구 획정의 ReCom 앙상블(DeFord et al., 2021)'],
       ['비교 기준 (c)', '같은 경계 동의 여러 인접 생활권: 통행 비율 W ~ 보행 시설 비율 F | 도달 면적·인구(+ 생활권 인구·종사자), 편 Spearman·동 고정효과·군집 부트스트랩'],
       ['통행 기준 재배정', '구별 무향 통행망의 모듈성(해상도 1)을 가장 높이는 인접 생활권 이동을 반복(KPA와 같은 규칙, AG 코드로 독립 구현·결과 동일)'],
       ['검증', 'a07 원고 수치 136개 자동 대조, 무작위·통행 경로 707개 상태와 앙상블 2,000장이 이전 독립 실행과 동일, 외부 검수 3라운드(문장 검수 종결)']], [3.2, 13.8])

    H('4. 핵심 결과')
    T([['항목', '2020', '2025'],
       ['공식 생활권 L(누락 인구)', f"{n0(A[2020]['L_LZ'])} ({A[2020]['L_LZ_share']*100:.1f}%)", f"{n0(A[2025]['L_LZ'])} ({A[2025]['L_LZ_share']*100:.1f}%)"],
       ['무작위 재배정 100경로, 경로 끝 ΔL 중앙값', sgn(end[2020]['rand_median']), sgn(end[2025]['rand_median'])],
       ['통행 기준 재배정, 경로 끝 ΔL (이동 수)', f"{sgn(end[2020]['flow_dL'])} ({A[2020]['n_flow_moves']})", f"{sgn(end[2025]['flow_dL'])} ({A[2025]['n_flow_moves']})"],
       ['통행 기준이 무작위 100경로 전부보다 낮아지는 k', str(A[2020]['first_k_from_which_flow_below_all_random']), str(A[2025]['first_k_from_which_flow_below_all_random'])],
       ['인구·형상 조밀도 제약을 함께 건 모듈성 경로 ΔL(부록)', sgn(C[2020]['MOD_end']['dL_unique']), sgn(C[2025]['MOD_end']['dL_unique'])],
       ['대안 지도 1,000장 중 L > 공식', f"{E[2020]['n_greater']}", f"{E[2025]['n_greater']}"],
       ['대안 중앙값 − 공식 L', sgn(E[2020]['median_minus_LZ']), sgn(E[2025]['median_minus_LZ'])],
       ['편상관 W~F | A,P [95% CI]', f"{M[2020]['partial_W_F_given_AP']['est']:.3f} [{M[2020]['partial_W_F_given_AP']['ci95'][0]:.3f}, {M[2020]['partial_W_F_given_AP']['ci95'][1]:.3f}]", f"{M[2025]['partial_W_F_given_AP']['est']:.3f} [{M[2025]['partial_W_F_given_AP']['ci95'][0]:.3f}, {M[2025]['partial_W_F_given_AP']['ci95'][1]:.3f}]"]], [7.5, 4.75, 4.75])
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(FIG / 'Fig2.png'), width=Cm(15))
    q = d.add_paragraph('그림. 경계 동 재배정 횟수 k에 따른 누락 인구 변화: 무작위 100경로(파랑) vs 통행 기준(빨강). 공식 생활권 대비.'); q.runs[0].font.size = Pt(8.5)

    H('5. 설계 변경 경위 (9/21 지도 지침 대비)')
    P('9/21 지침은 "불일치의 이유는 접근성인가"를 IFR 종속변수·MAI·Coverage 설명변수 회귀로 보는 것이었습니다. 지침대로 ΔIFR ~ ΔMAI 회귀를 먼저 실행했으나, 무작위로 그은 경계 98~100%가 같은 부호를 냈습니다. '
      '접근성이 자족성을 설명한 것이 아니라 경계 회계 자체가 만드는 결과였고, 대안 지도 1,000장 안에서도 IFR–L 상관은 −0.12로 약했습니다. 이 자료로 "왜 어긋나나"에는 답할 수 없다고 판단해, 계획가에게 실제로 필요한 옆 질문 "통행으로 고치면 서비스 포착은 어떻게 되나"로 질문을 바꿨습니다. '
      'IFR은 두 핵심 지표 중 하나로 유지했고, 회귀 대신 비교(무작위·대안 지도·인접 생활권)만 쓰므로 "분석 심플하게"에 부합합니다. 면적·형상 조밀도는 지침대로 통제(앙상블 제약)로만 씁니다. 시설은 승훈 씨 자료가 아니라 직접 구축한 27종 7범주(facility-v1.4)입니다. 폐기한 회귀는 원고 부록 A3에 기록했습니다.')

    H('6. 검수와 남은 절차')
    wc = json.load(open(MS / 'word_count.json', encoding='utf-8'))
    B(['외부 검수(ChatGPT) 5라운드(문장 검수 종결 판정, 구성 변경 검수 포함). 항목별 반영·미반영 사유는 패키지 docs/검수의견_대응표.',
       f"원고: 초록 {wc['abstract']}단어(숫자 없음), 본문·표·캡션·참고문헌 포함 {wc['total_AG_count(abstract+body+tables+captions+declaration+references)']:,}단어(AG 8,000 이하), 참고문헌 {wc['n_references']}편(Crossref 확인), 하이라이트 5개, 이중 익명. 생성형 AI 사용 고지(코드 작성·점검, 본문 초안·수정) 본문 끝에 기재.",
       '자료: 공개 자료(오픈데이터 논문용 사용 허락). 시설 목록·결과·코드는 공개 저장소.',
       '남은 것: 교수님 최종 검토·승인 → AG 투고. 투고 시스템의 선행 발표 항목(JTG 게재본은 3인칭 인용, KPA는 미투고라 투고 편지에만 언급).'])

    H('7. 첨부·링크')
    B([f'공동연구자 패키지 zip: AG_확정본_공동연구자패키지_20260930_{COMMIT}.zip — manuscript/(영문 익명본·제목면·하이라이트·부록·투고편지·한국어 전문, docx·pdf), results/, code/, docs/(설계·검수 대응표), README',
       f'GitHub 폴더: {REPO}/tree/{COMMIT}/03_%EB%B6%88%EC%9D%BC%EC%B9%98_%EC%A0%91%EA%B7%BC%EC%84%B1_AG',
       f'GitHub 커밋: {REPO}/commit/{COMMIT}',
       '먼저 보실 순서: 한국어 원고 PDF → 이 메모 4절 표 → 영문 익명본 PDF → docs/연구설계_AG확정본.md'])
    out = AG / '보고_20260930' / 'AG_교수님보고_20260930.docx'; out.parent.mkdir(exist_ok=True); d.save(out); print(out)


if __name__ == '__main__':
    main()
