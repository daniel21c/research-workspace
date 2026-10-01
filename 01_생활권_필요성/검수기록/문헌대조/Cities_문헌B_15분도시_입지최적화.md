# Cities 투고용 문헌 대조 B: 15분 도시 측정, 15분 도시 입지 최적화, 입지모형의 형평성·집계오차

- 작성일: 2026-10-01
- 대상 원고: "Grids fill people, not places: Testing the necessity of living zones for walkable public services in Seoul"
- 검증 방법: 모든 문헌의 서지(제목·저자·연도·학술지·권호·쪽수/논문번호)는 Crossref API(`api.crossref.org/works/<DOI>`)로 실시간 확인함. 단, Zhai et al.(2023, 地理学报)은 DOI가 Crossref가 아닌 중국 DOI 등록기관에 있어 `doi.org/api/handles`와 학술지 누리집 메타데이터로 확인함.
- 초록 출처: OpenAlex `abstract_inverted_index`(복원), Crossref 초록 필드, Semantic Scholar API, PubMed efetch, 출판사 페이지 메타데이터(Springer `dc.description`, RePEc IDEAS), arXiv 본문. 출처는 항목마다 [초록: …]로 적음. 초록을 직접 받지 못하고 검색엔진 요약으로만 본 경우는 그렇다고 밝힘.
- 별표(★)는 원고에 우선 넣기를 권하는 핵심 문헌.
- 원고에 이미 인용된 문헌(Moreno 2021; Allam 2022; Logan 2022; Papadopoulos 2023; Willberg 2023; Mouratidis 2024; Teixeira 2024; Karsu & Morton 2015; Bertsimas et al. 2011)은 새 문헌으로 세지 않음. 서지 확인만 요청된 것(Abbiasov 2024; Hillsman & Rhoda 1978; Karsu & Morton 2015; Bertsimas et al. 2011)은 해당 절에 확인 결과를 적음.
- (d)항 표기: 목적함수 / 수요 단위 / 구역 단위 평가·제약(yes/no/partly/unclear).

---

## 1. 15분 도시(x분 도시) 측정: 다중 시설 완결성과 구역별 결과

**B1 ★ (서지 확인 요청분)** Abbiasov, T., Heine, C., Sabouri, S., Salazar-Miranda, A., Santi, P., Glaeser, E., & Ratti, C. (2024). The 15-minute city quantified using human mobility data. *Nature Human Behaviour, 8*(3), 445–455. https://doi.org/10.1038/s41562-023-01770-y
- verified: yes (Crossref: 8권 3호 445–455쪽, 2024-02-05 온라인. PubMed PMID 38316977도 같음. 정오표 *Nat Hum Behav* 8(4):795, https://doi.org/10.1038/s41562-024-01874-z 있음) [초록: PubMed]
- 발견: 미국 모바일 기기 4천만 대의 GPS 자료로 집에서 걸어서 15분 안에 이뤄진 소비 통행의 비율("15-minute usage")을 정의했고, 중위 거주자는 일일 소비 통행의 14%만 근거리에서 한다. 근거리 시설 접근성 차이가 도시권 간 변동의 84%, 도시권 내 변동의 74%를 설명했다.
- 원고 활용: Intro. 근거리 시설 공급이 실제 근거리 이용을 좌우한다는 근거이므로, 시설을 "어디에" 두느냐가 정책 변수라는 전제를 뒷받침함.

**B2 ★** Calafiore, A., Dunning, R., Nurse, A., & Singleton, A. (2022). The 20-minute city: An equity analysis of Liverpool City Region. *Transportation Research Part D: Transport and Environment, 102*, 103111. https://doi.org/10.1016/j.trd.2021.103111
- verified: yes [초록: 같은 논문의 OSF 사전공개본(https://doi.org/10.31219/osf.io/ftkw2) 초록, OpenAlex. 학술지판 초록은 받지 못함]
- 발견: 넓은 도시권에서 "20분 근린"이 어디에 있는지 찾아내는 방법을 내놓았고, 그런 근린의 분포가 사회·공간 불평등과 어떻게 맞물리는지 평가했다.
- 원고 활용: 2.1 / Discussion. 다중 시설 기준을 근린(구역) 단위로 판정해 "어느 근린이 기준을 못 채우는가"를 보고하는 측정 연구의 예.

**B3 ★** Weng, M., Ding, N., Li, J., Jin, X., Xiao, H., He, Z., & Su, S. (2019). The 15-minute walkable neighborhoods: Measurement, social inequalities and implications for building healthy communities in urban China. *Journal of Transport & Health, 13*, 259–273. https://doi.org/10.1016/j.jth.2019.05.005
- verified: yes [초록: Semantic Scholar]
- 발견: Walk Score를 고쳐 상하이의 15분 보행 근린 점수를 보행자 집단(전체·아동·성인·노인)별로 쟀고, 보행성이 높은 커뮤니티는 도심에 몰리고 낮은 커뮤니티는 외곽에 흩어져 있었다. 커뮤니티의 사회경제적 지위와 점수 사이의 관계를 공간회귀로 확인했다.
- 원고 활용: 2.1. 결과를 커뮤니티(구역) 단위로 보고하고 취약 집단을 따로 본 15분 측정의 대표 사례.

**B4 ★** Olivari, B., Cipriano, P., Napolitano, M., & Giovannini, L. (2023). Are Italian cities already 15-minute? Presenting the Next Proximity Index: A novel and scalable way to measure it, based on open data. *Journal of Urban Mobility, 4*, 100057. https://doi.org/10.1016/j.urbmob.2023.100057
- verified: yes [초록: OpenAlex]
- 발견: OpenStreetMap 기반 보행 근접성 지수(NEXI)를 육각 격자 위에서 계산해 이탈리아 전역에 제공하고, 어느 지역이 이미 15분 원칙을 따르는지 찾는다. 인구 같은 지역 자료와 결합한 사례를 페라라·볼로냐에서 보였다.
- 원고 활용: 2.2. 15분 측정이 이미 "격자" 단위로 이뤄진다는 근거(격자로 충분하다는 반론의 출처로 인용 가능).

**B5** Staricco, L. (2022). 15-, 10- or 5-minute city? A focus on accessibility to services in Turin, Italy. *Journal of Urban Mobility, 2*, 100030. https://doi.org/10.1016/j.urbmob.2022.100030
- verified: yes [초록: OpenAlex]
- 발견: 토리노에서 서비스별로 5·10·15분 안에 걸어서 닿는 인구 비율과 도시 내 위치를 계산했고, 밀도 높은 유럽 도시에서는 많은 서비스가 이미 15분보다 짧게 닿으므로 15분이 늘 적절한 목표는 아니라고 보았다. 접근성 수준은 서비스 입지의 수와 분포에 크게 좌우된다.
- 원고 활용: Methods(10분 기준 선택의 근거) / 2.2.

**B6 ★** Ferrer-Ortiz, C., Marquet, O., Mojica, L., & Vich, G. (2022). Barcelona under the 15-minute city lens: Mapping the accessibility and proximity potential based on pedestrian travel times. *Smart Cities, 5*(1), 146–161. https://doi.org/10.3390/smartcities5010010
- verified: yes [초록: OpenAlex]
- 발견: 지적 필지 단위로 보행 네트워크 분석을 해 교육·장보기·여가·대중교통·돌봄 등 부문별 지수와 종합지수를 만들었다. 조밀한 바르셀로나에서도 대다수 주민은 15분 조건을 채우지만 외곽에 결손이 남았다.
- 원고 활용: 2.1 / Results 해석. 도시 전체는 대체로 충족해도 "특정 구역"에 결손이 몰린다는 패턴의 선례.

**B7** Vale, D., & Lopes, A. S. (2023). Accessibility inequality across Europe: A comparison of 15-minute pedestrian accessibility in cities with 100,000 or more inhabitants. *npj Urban Sustainability, 3*, 55. https://doi.org/10.1038/s42949-023-00133-w
- verified: yes [초록: OpenAlex]
- 발견: 누적 기회와 시설 종류 다양성(Variety)의 두 지표로 유럽 도시들의 15분 보행 접근성과 도시 내 불평등(유사 지니)을 쟀고, 유럽 도시들은 아직 15분 도시가 아니며 도시 내부 불평등이 크다. 시설 종류의 다양성을 늘리면 접근성은 높이고 내부 불평등은 줄일 수 있다고 보았다.
- 원고 활용: 2.1. 다중 시설(종류 수) 기준과 도시 내 불평등을 함께 다룬 비교 연구.

**B8** Nicoletti, L., Sirenko, M., & Verma, T. (2023). Disadvantaged communities have lower access to urban infrastructure. *Environment and Planning B: Urban Analytics and City Science, 50*(3), 831–849. https://doi.org/10.1177/23998083221131044
- verified: yes [초록: OpenAlex]
- 발견: 54개 도시에서 여러 기반시설 접근성 분포가 지프 법칙을 따랐고, 10개 도시의 사회경제 유형별 분석에서 소수자 비중이 크고 소득·학력이 낮은 집단의 접근성이 낮았다.
- 원고 활용: Intro / 2.3. 취약성 가중 규칙(vulnerability-weighted)의 정당화 근거.

**B9** Zhang, S., Zhen, F., Kong, Y., Lobsang, T., & Zou, S. (2023). Towards a 15-minute city: A network-based evaluation framework. *Environment and Planning B: Urban Analytics and City Science, 50*(2), 500–514. https://doi.org/10.1177/23998083221118570
- verified: yes [초록: OpenAlex]
- 발견: 현재 시설 분포 아래에서 인간 이동을 최대화하는 "최적 이동 네트워크"를 가정하고 실제 이동과 비교해 시설 공급이 지역 수요와 어긋나는 장소를 찾는 틀을 난징에 적용했다.
- 원고 활용: 2.2. 측정 틀 안에 최적화 개념을 넣은 사례(입지 결정 모형은 아님).

**B10** Graells-Garrido, E., Serra-Burriel, F., Rowe, F., Cucchietti, F. M., & Reyes, P. (2021). A city of cities: Measuring how 15-minutes urban accessibility shapes human mobility in Barcelona. *PLOS ONE, 16*(5), e0250080. https://doi.org/10.1371/journal.pone.0250080
- verified: yes [초록: OpenAlex]
- 발견: 휴대전화 OD 자료와 지리가중 음이항 회귀로, 사람들은 교육·소매 접근성이 좋은 동네를 더 찾고 그 관계의 부호와 크기가 동네마다 달랐다. 저자들은 이 국지적 차이가 행정경계로 설명되지 않는다고 보고했다.
- 원고 활용: 2.2 / Discussion. "행정구역이 접근성 차이를 설명하지 못한다"는 격자 옹호 쪽 근거이므로, 원고가 구역의 필요성을 주장할 때 마주해야 할 반론으로 인용.

**B11 ★** Song, L., Kong, X., & Cheng, P. (2024). Supply-demand matching assessment of the public service facilities in 15-minute community life circle based on residents' behaviors. *Cities, 144*, 104637. https://doi.org/10.1016/j.cities.2023.104637
- verified: yes [초록: 직접 받지 못함. 내용은 검색엔진의 ScienceDirect 초록 요약으로만 확인]
- 발견(검색 요약 기준): 연령 집단별 다집단 Huff 3SFCA 모형으로 난징 주요 도시지역의 15분 커뮤니티 생활권 공공서비스 수급 정합도를 평가했고, 의료시설은 모든 연령 집단에 크게 부족했다.
- 원고 활용: 2.1. *Cities*에 실린 생활권(life circle) 단위 수급 평가. 인용 전에 원문 초록 대조 필요.

**B12** Wu, H., Wang, L., Zhang, Z., & Gao, J. (2021). Analysis and optimization of 15-minute community life circle based on supply and demand matching: A case study of Shanghai. *PLOS ONE, 16*(8), e0256904. https://doi.org/10.1371/journal.pone.0256904
- verified: yes [초록: OpenAlex]
- 발견: POI·OSM·LandScan으로 상하이 15분 생활권의 서비스 편의도를 평가했고, 도심은 높고 교외·외곽은 낮으며 일부 외곽에는 시설이 과잉 공급됐다. 제목과 달리 수리적 입지 최적화가 아니라 지역별 정책 제안("optimization strategies")이다.
- 원고 활용: 2.3. "optimization"이라는 제목의 생활권 연구가 실제로는 평가+제안에 그친다는 점을 보일 때.

**B13** Gaglione, F., Gargiulo, C., Zucaro, F., & Cottrill, C. (2022). Urban accessibility in a 15-minute city: A measure in the city of Naples, Italy. *Transportation Research Procedia, 60*, 378–385. https://doi.org/10.1016/j.trpro.2021.12.049
- verified: yes [초록: OpenAlex]
- 발견: 15분 도시의 기원을 근린주구(neighbourhood unit) 개념에서 찾고, 지형·물리·기능·사회경제 특성에 가중치를 주어 나폴리 일부 구역의 15분 접근 가능 범위를 정했다.
- 원고 활용: Intro(15분 도시와 근린주구의 계보). 우선순위 낮음.

---

## 2. 15분 도시를 위한 입지 최적화·재배치 연구 (핵심)

**B14 ★★** Bruno, M., Monteiro Melo, H. P., Campanelli, B., & Loreto, V. (2024). A universal framework for inclusive 15-minute cities. *Nature Cities, 1*(10), 633–641. https://doi.org/10.1038/s44284-024-00119-4
- verified: yes [초록: Semantic Scholar. 방법 세부: arXiv 사전공개본 2408.03794 본문]
- 발견: 전 세계 도시의 필수 서비스 접근 시간을 재서 도시 안팎의 큰 이질성과 인구밀도의 역할을 보였고, 같은 시설 수로 재배치하거나 시설을 무한히 늘리는 경우를 모의해 15분 도시에 필요한 추가 시설 수가 도시마다 크게 다름을 보였다.
- (d) 목적: 15분 반경마다 1인당 시설 수를 같게 만들기(가장 많은 인구가 닿는 셀에 시설을 하나씩 두고 수요를 차감하는 탐욕 재배치) / 수요 단위: 한 변 200 m 육각 격자 / 구역 평가: no(셀별 점수, 도시 전체 지표, 지니계수로만 평가. 행정구역·근린 단위의 제약이나 평가 없음, arXiv 본문 기준).
- 원고 활용: Intro / 2.3 / Discussion. 원고의 "격자 규칙"과 가장 가까운 선행 연구. 격자 기반 재배치가 사람을 채우지만 구역 단위 결과는 묻지 않는다는 공백 주장의 첫 근거.

**B15 ★★** Huang, W., & Khalil, E. B. (2023). Walkability optimization: Formulations, algorithms, and a case study of Toronto. *Proceedings of the AAAI Conference on Artificial Intelligence, 37*(12), 14249–14258. https://doi.org/10.1609/aaai.v37i12.26667
- verified: yes [초록: OpenAlex]
- 발견: 기존 시설을 고려해 새 시설(식료품점·학교·식당 등)을 둘 위치를 고르는 보행성 최적화를 MILP·CP로 정식화했고, 목적함수가 특수한 경우 부분모듈(submodular)임을 보여 탐욕 휴리스틱을 정당화했다. 토론토 저보행 근린 31곳에서 시설 3개씩을 더하면 4개 근린의 WalkScore가 50점 넘게 오르고 주거지점 75%의 모든 시설 유형 보행거리가 10분 이내가 된다.
- (d) 목적: 가중 WalkScore(다중 시설 유형 접근성) 최대화 / 수요 단위: 주거 위치(residential locations) / 구역 평가: partly(사례가 근린 31곳이고 결과를 근린별로 보고하지만, 근린 간 최소기준이나 "빈 근린" 수는 다루지 않음. 근린마다 따로 푸는지 여부는 초록·arXiv 초록에서 확인 안 됨).
- 원고 활용: 2.3. 다중 시설 유형을 한 번에 다루는 MILP·탐욕 해법의 선례. 원고의 탐욕 MCLP 규칙의 방법론적 근거로 인용.

**B16 ★★** Pemberton, S., Saghapour, T., Giles-Corti, B., Abdollahyar, M., Both, A., Pearson, D., Higgs, C., Jafari, A., Singh, D., Gunn, L., Woodcock, J., & Zapata-Diomedi, B. (2026). Infrastructure and accessibility implications of implementing x-minute city policies in low-density contexts. *Cities, 171*, 106717. https://doi.org/10.1016/j.cities.2025.106717
- verified: yes [초록: 학술지판 초록은 직접 받지 못함. 같은 연구의 SSRN 사전공개본(https://doi.org/10.2139/ssrn.4918680) 초록을 Crossref에서 받았고, 학술지판 내용은 검색엔진 요약으로 대조함]
- 발견: 멜버른 20분 근린 정책에 맞춰 14개 목적지 유형을 정하고, 각 활동중심지 집수구역(800 m 보행권) 안 인구의 80% 이상이 유형마다 10분 보행권에 들도록 추가 목적지를 배치하는 방법을 만들었다. 도시 전체 접근성은 크게 나아지지만 저밀 외곽에서는 새 시설의 이용률이 낮아 실행이 어렵다.
- (d) 목적: 집수구역별 최소 커버율(80%)을 채우는 추가 배치 / 수요 단위: 주거 인구(활동중심지 800 m 집수구역 안) / 구역 평가: **yes(구역별 최소기준을 제약으로 둠)**.
- 원고 활용: 2.3 / Discussion. **공백 주장에 대한 가장 중요한 반례이자 선행 연구.** 구역 단위 최소기준을 쓴 x분 도시 배치 연구가 이미 *Cities*에 있음. 다만 (i) 구역이 도시 전체를 덮는 계획 생활권이 아니라 활동중심지 주변 집수구역이고, (ii) 격자 규칙과 구역 규칙을 같은 시설 집합으로 비교하지 않으며, (iii) "아무도 모든 부문에 닿지 못하는 구역 수"를 세지 않는다. 원고는 이 점을 들어 차별화해야 함. 투고 학술지가 같으므로 반드시 인용 권함.

**B17 ★** Jafari, A., Singh, D., & Giles-Corti, B. (2023). Residential density and 20-minute neighbourhoods: A multi-neighbourhood destination location optimisation approach. *Health & Place, 83*, 103070. https://doi.org/10.1016/j.healthplace.2023.103070
- verified: yes [초록: PubMed PMID 37393629]
- 발견: 가상의 신도시(greenfield)에서 여러 근린과 공유 목적지를 함께 다루는 최적화 모형으로, 목적지별로 800 m 안에 닿는 인구 비율 목표(작은 목적지 95%~큰 목적지 70%)를 두고 주거밀도와 20분 근린 달성의 관계를 분석했다. 1.2 km 안 접근에는 최소 25호/ha, 1 km 안에는 35호/ha가 필요했다.
- (d) 목적: 목적지 유형별 인구 커버율 목표 충족 + 건설비·토지 / 수요 단위: 주거(가상 개발지) / 구역 평가: unclear(제목·초록은 "multi-neighbourhood"를 강조하지만, 커버율 목표가 근린별인지 전체인지는 초록에서 확인 안 됨).
- 원고 활용: 2.3. 다중 목적지 커버율 목표를 쓰는 최적화의 선례. 기존 도시 재정비가 아닌 가상 신도시라는 점이 원고와 다름.

**B18 ★** Horton, D., Logan, T. M., Speakman, E., & Skipper, D. (2025). Hundreds of grocery outlets needed across the United States to achieve walkable cities. *Nature Communications, 16*, 6051. https://doi.org/10.1038/s41467-025-61454-1
- verified: yes [초록: Semantic Scholar. 수요·후보지 단위: 학술지 본문(오픈액세스)]
- 발견: 미국 500개 도시에서 평균 거리와 그 분포의 불평등을 함께 줄이는 최적화로 슈퍼마켓 보행 접근을 분석했고, 25% 도시는 최적 위치에 5곳 이하를 더해 15분 보행 접근을 이루지만 5분 목표에는 대부분 100곳 넘게 필요했다.
- (d) 목적: Kolm–Pollak EDE(평균+불평등) 최소화 / 수요 단위: 센서스 블록(후보지는 블록그룹 중심점) / 구역 평가: no(도시 단위 목표와 블록별 전후 산점도로 평가. 근린 단위 제약은 본문에서 찾지 못함).
- 원고 활용: 2.3. 형평성 가중 입지 최적화가 미세 단위에서 "사람"의 분포만 다룬다는 근거. 단일 시설 유형이라는 점도 원고(6개 부문 동시)와 대비.

**B19 ★** Horton, D., Murrell, J., Skipper, D., Speakman, E., & Logan, T. (2025). A scalable optimization approach for equitable facility location: Methodology and transportation applications. *Transportation Research Part B: Methodological, 201*, 103319. https://doi.org/10.1016/j.trb.2025.103319
- verified: yes [초록: OpenAlex]
- 발견: Kolm–Pollak EDE의 선형 대리지표로 대규모 형평 입지 문제를 풀 수 있게 했고, 최적해는 가장 불리한 거주자의 거리를 크게 줄이면서 평균도 거의 최적으로 유지했다. 미국 428개 도시에서 p-median·p-center·p-centdian과 비교했다.
- (d) 목적: 형평 가중 거리(EDE) 최소화 / 수요 단위: 거주자 분포(블록 수준 사례) / 구역 평가: no(초록 기준).
- 원고 활용: 2.3 / Methods. 취약성·형평 가중 규칙의 최신 방법론 출처.

**B20** Young, A., Tucker, E. L., Fernandez, M., White, D., Brookover, R., & Harris, B. (2024). An optimization approach to improve equitable access to local parks. *Socio-Economic Planning Sciences, 92*, 101826. https://doi.org/10.1016/j.seps.2024.101826
- verified: yes [초록: Semantic Scholar]
- 발견: 거리·용량·환경 특성의 가중 편차로 정의한 "불충분한 접근"을 줄이는 혼합정수계획을 만들고, 최소최대(min-max) 형평 목적과 총편차 목적을 함께 다뤄 애슈빌 공원 계획에 적용했다.
- (d) 목적: 불충분 접근의 min-max 또는 총합 최소화 / 수요 단위: 초록에 명시 없음(unclear) / 구역 평가: unclear.
- 원고 활용: 2.3. 형평 목적(min-max)과 효율 목적을 나란히 비교한 공공시설 입지 사례.

**B21 ★** Xu, Y., Olmos, L. E., Abbar, S., & González, M. C. (2020). Deconstructing laws of accessibility and facility distribution in cities. *Science Advances, 6*(37), eabb4112. https://doi.org/10.1126/sciadv.abb4112
- verified: yes [초록: OpenAlex]
- 발견: 6개 도시에서 시설을 재배치하면 통행비용을 절반으로 줄일 수 있었고, 최적 상태의 평균 통행거리는 시설 수와 인구밀도의 함수로 표현됐다. 이를 이용해 목표 평균거리에 필요한 시설 수를 추정할 수 있다.
- (d) 목적: 도로망 위 평균 접근거리 최소화(접근성 최대화) / 수요 단위: 인구 분포(초록에 셀 크기 명시 없음) / 구역 평가: no(도시 평균 기준, 초록 기준).
- 원고 활용: Intro / 2.3. "격자·인구 기반 최적화가 도시 평균을 크게 개선한다"는 효율 쪽 대표 근거.

**B22 ★** Chen, L., Zeng, H., Wu, L., Tian, Q., Zhang, N., He, R., Xue, H., Zheng, J., Liu, J., Liang, F., & Zhu, B. (2023). Spatial accessibility evaluation and location optimization of primary healthcare in China: A case study of Shenzhen. *GeoHealth, 7*(5), e2022GH000753. https://doi.org/10.1029/2022GH000753
- verified: yes [초록: OpenAlex]
- 발견: 가우시안 2SFCA로 선전 지역사회 보건센터 접근성을 재서 구별로 보고했고(난산·뤄후·푸톈 등 높음), MCLP로 신규 후보지를 최대 567곳 골라 15분 임피던스 안 커버 인구를 63.46% 늘렸다.
- (d) 목적: 15분 내 커버 인구 최대화(MCLP) / 수요 단위: 거주 지점(resident points)+센서스 / 구역 평가: partly(현황 접근성은 구(district)별로 보고하지만, 최적화 결과를 구역별로 제약·평가했는지는 초록에서 확인 안 됨).
- 원고 활용: 2.3. 15분 MCLP 신규 입지의 전형. 커버 인구 증가로만 성과를 보고하는 관행의 예.

**B23 ★** Zhai, S., Kong, Y., Song, G., & Luo, J. (2023). A new facility location problem for urban public facility planning toward 15-minute life circle: Model and experiment [面向15 min生活圈的城市公共服务设施区位问题：模型与实验]. *Acta Geographica Sinica, 78*(6), 1484–1497. https://doi.org/10.11821/dlxb202306010
- verified: yes (Crossref에는 없음. `doi.org/api/handles`로 DOI가 학술지 누리집으로 연결됨을 확인했고, 저자·권호·쪽수는 학술지 영문 페이지에서 확인) [초록: 학술지 누리집 메타데이터(중국어 초록)]
- 발견: 고전 용량제약 입지문제(CFLP)를 서비스 반경과 커버율의 이중 제약 아래 부분 커버 문제(μCFLP)로 고쳐 혼합정수 모형과 수리 휴리스틱을 만들었고, 6개 도시 사례지역의 지역사회 보건센터 배치 실험에서 공급비용·접근성·형평의 균형을 보였다. 인구밀도가 낮은 도시는 반경·커버율 설정에 민감했고, 고밀 대도시는 15분 생활권 기준을 채우기 쉬웠다.
- (d) 목적: 커버율·반경 제약 아래 시설 수·비용 최소화 / 수요 단위: 초록에 명시 없음(unclear) / 구역 평가: no(커버율 제약은 사례지역 전체 단위로 서술됨, 초록 기준).
- 원고 활용: 2.3. "생활권"을 이름에 걸었지만 커버율을 지역 전체로 거는 모형. 단일 시설 유형.

**B24** Wu, M., Chen, J., Zheng, K., Zhang, J., & Wu, S. (2026). Evaluating and optimizing public service facilities within the 15-min community life circle—evidence from Nanchang, China. *Scientific Reports, 16*, 26400. https://doi.org/10.1038/s41598-026-55086-8
- verified: yes [초록: PubMed PMID 42270874]
- 발견: 난창 6개 구·3개 현의 공공서비스 시설 28,082곳(24개 유형)을 분석해 커버 효율이 낮고 유형 간 격차와 수급 불일치가 있음을 보였고, 입지배분(location-allocation) 모형으로 수급 불일치 지역에 대한 최적화 전략을 제안했다.
- (d) 목적: 입지배분 모형(초록에 세부 목적함수 없음) / 수요 단위: unclear / 구역 평가: unclear.
- 원고 활용: 2.3 보조 인용. 우선순위 낮음.

**B25** Lima, F. T., Brown, N. C., & Duarte, J. P. (2022). A grammar-based optimization approach for designing urban fabrics and locating amenities for 15-minute cities. *Buildings, 12*(8), 1157. https://doi.org/10.3390/buildings12081157
- verified: yes [초록: Semantic Scholar]
- 발견: 형태문법(shape grammar)과 다목적 최적화를 결합해 가로 길이(기반시설 비용)와 시설 수는 줄이고 보행 접근성(통합도, 모든 필지에서 가장 가까운 시설까지 평균거리)은 높이는 15분 근린 배치를 생성했다.
- (d) 목적: 비용·시설 수 최소화와 평균 접근거리 최소화의 다목적 / 수요 단위: 필지(plots) / 구역 평가: no(단일 근린 설계 문제).
- 원고 활용: 2.3. 설계 단계의 15분 최적화. 기존 도시의 구역 간 배분과는 다른 문제임을 보일 때.

**B26** Zheng, Y., Lin, Y., Zhao, L., Wu, T., Jin, D., & Li, Y. (2023). Spatial planning of urban communities via deep reinforcement learning. *Nature Computational Science, 3*(9), 748–762. https://doi.org/10.1038/s43588-023-00503-5
- verified: yes [초록: PubMed PMID 38177774. 서비스 지표 정의: 저자 기관이 공개한 본문 PDF]
- 발견: 도시 형태를 그래프로 표현하고 토지이용·도로 배치를 순차 의사결정으로 정식화한 그래프신경망 강화학습 모형이 합성·실제 커뮤니티에서 전문가 계획보다 객관 지표가 좋았다. 본문에서 서비스 지표는 "15분 생활권"(교육·의료·업무·쇼핑·여가 5개 서비스가 주거에서 500 m 안)에 닿는 비율로 정의된다.
- (d) 목적: 서비스·교통·생태 효율의 복합 보상 / 수요 단위: 커뮤니티 안의 주거 구역(그래프 노드) / 구역 평가: no(한 커뮤니티 안의 설계 문제).
- 원고 활용: 2.3. 다중 서비스 15분 기준을 목적함수에 넣은 최적화 사례(단일 커뮤니티 범위).

**B27 ★** Rhoads, D., Solé-Ribalta, A., & Borge-Holthoefer, J. (2023). The inclusive 15-minute city: Walkability analysis with sidewalk networks. *Computers, Environment and Urban Systems, 100*, 101936. https://doi.org/10.1016/j.compenvurbsys.2022.101936
- verified: yes [초록: OpenAlex]
- 발견: 보도 네트워크 모형과 퍼콜레이션 이론으로 다요인 보행성을 평가하는 틀을 바르셀로나에 적용했고, 이를 취약 인구(노인·아동)를 위한 서비스 입지 최적화에 쓸 수 있음을 보였다.
- (d) 목적: 취약 인구의 서비스 접근 개선(초록 수준. 세부 목적함수는 초록에 없음) / 수요 단위: 보도 네트워크 / 구역 평가: unclear.
- 원고 활용: 2.3. 취약 집단 중심 서비스 입지의 15분 사례.

**B28 ★** Arslan, O., & Laporte, G. (2025). The 15-minute city concept: An operations research perspective and a research agenda. *Transportation Research Part E: Logistics and Transportation Review, 202*, 104287. https://doi.org/10.1016/j.tre.2025.104287
- verified: yes [초록: OpenAlex. 본문은 열람 못 함]
- 발견: 15분 도시 문헌이 주로 접근성의 정의와 측정에 머물렀다고 보고, 시설 입지·이동 시스템·공유교통·통합 거버넌스를 포함한 운영연구(OR) 연구 의제를 제안했다.
- (d) 해당 없음(리뷰).
- 원고 활용: Intro / 2.3. "15분 도시 연구는 측정에 치우쳤고 최적화 기반 실행 연구는 적다"는 진술의 직접 출처.

---

## 3. 입지모형의 형평성, 구역·지점 수요 집계오차

**B29 ★ (서지 확인 요청분)** Hillsman, E. L., & Rhoda, R. (1978). Errors in measuring distances from populations to service centers. *The Annals of Regional Science, 12*(3), 74–88. https://doi.org/10.1007/BF01286124
- verified: yes (Crossref: 12권 3호 74–88쪽, 1978-11. **DOI는 10.1007/BF01286124**이므로 원고에 다른 DOI가 있으면 고칠 것) [초록: Springer 페이지 메타데이터]
- 발견: 군·센서스 구역 인구를 한 점으로 대표해 서비스 중심지까지 거리를 재는 관행은 이론적 공간에서도 실제 거리와 최대 8% 차이가 나고 실제 공간에서는 더 클 수 있으며, 이는 대안 입지계획 평가에 중요한 함의를 갖는다.
- 원고 활용: 2.2 / Methods. 구역을 한 점(중심점)으로 대표하는 방식의 오차, 즉 "구역 기반 측정"에 대한 고전적 비판. 원고가 구역을 측정 단위가 아닌 "평가·배분 단위"로만 쓴다는 점을 밝힐 때 함께 인용.

**B30 ★** Current, J. R., & Schilling, D. A. (1990). Analysis of errors due to demand data aggregation in the set covering and maximal covering location problems. *Geographical Analysis, 22*(2), 116–126. https://doi.org/10.1111/j.1538-4632.1990.tb00199.x
- verified: yes [초록: Crossref]
- 발견: Hillsman & Rhoda의 A·B·C형 집계오차를 커버 모형으로 확장했고, 커버 문제는 거리가 이진값이라 p-median보다 집계오차가 더 클 수 있다고 보았다. 집계 시 오차를 줄이는 세 규칙을 제시했다.
- 원고 활용: Methods. 원고가 MCLP를 격자 수요로 푸는 이유(집계 단위가 커지면 커버 판정 오차가 커짐).

**B31** Francis, R. L., Lowe, T. J., Rayco, M. B., & Tamir, A. (2009). Aggregation error for location models: Survey and analysis. *Annals of Operations Research, 167*(1), 171–208. https://doi.org/10.1007/s10479-008-0344-z
- verified: yes (온라인 2008, 인쇄 2009) [초록: Springer 페이지 메타데이터]
- 발견: 도시·지역 입지 문제에서 수만 개 수요점(대개 개별 주택)을 다루기 쉽게 집계하는 접근들을 개관하고, 여러 집계오차 척도를 비교해 효과적인 것과 아닌 것을 가렸다.
- 원고 활용: Methods. 집계오차 문헌의 표준 리뷰.

**B32 ★** Marsh, M. T., & Schilling, D. A. (1994). Equity measurement in facility location analysis: A review and framework. *European Journal of Operational Research, 74*(1), 1–17. https://doi.org/10.1016/0377-2217(94)90200-3
- verified: yes [초록: 출판사 초록을 API로 받지 못함. 검색엔진의 ScienceDirect/IDEAS 요약으로만 확인]
- 발견(검색 요약 기준): 공공부문 입지에서 형평이 중요해졌지만 형평을 어떻게 잴지에 대한 합의가 없다고 보고, 문헌의 형평 척도들을 정리해 입지모형에 형평을 넣는 틀을 제시했다.
- 원고 활용: 2.3. 형평 입지 리뷰의 고전. 원고에서 Karsu & Morton(2015)과 함께 인용.

**B33** Barbati, M., & Piccolo, C. (2016). Equality measures properties for location problems. *Optimization Letters, 10*(5), 903–920. https://doi.org/10.1007/s11590-015-0968-2
- verified: yes (온라인 2015, 인쇄 2016) [초록: Springer 페이지 메타데이터]
- 발견: 공공부문 입지에서 형평 척도가 많아 선택이 문제라는 점에서, 최적화 과정에서 척도가 어떻게 행동하는지를 기술하는 새 성질들을 제안하고 균등 수요 공간에서 실험했다.
- 원고 활용: 2.3 보조.

**B34 ★** Chanta, S., Mayorga, M. E., & McLay, L. A. (2014). Improving emergency service in rural areas: A bi-objective covering location model for EMS systems. *Annals of Operations Research, 221*(1), 133–159. https://doi.org/10.1007/s10479-011-0972-6
- verified: yes (온라인 2011, 인쇄 2014) [초록: Springer 페이지 메타데이터]
- 발견: 전통적 커버 모형은 커버 수요를 최대화하므로 인구 밀집지에 구급차를 몰아 농촌 응답시간을 늘린다고 지적하고, 도시·농촌 간 형평을 두 번째 목적으로 넣은 이목적 커버 모형 세 가지를 제안했다.
- 원고 활용: 2.3 / Discussion. **"최대 커버는 사람이 많은 곳을 채우고 희박한 지역을 남긴다"는 원고 핵심 기제의 직접 선례.** 다만 지역 구분이 도시/농촌 2분이고 계획 생활권 단위가 아님.

**B35** Mandell, M. B. (1991). Modelling effectiveness-equity trade-offs in public service delivery systems. *Management Science, 37*(4), 467–482. https://doi.org/10.1287/mnsc.37.4.467
- verified: yes [초록: Crossref]
- 발견: 서비스 자원을 여러 지점(지소)에 배분할 때 전체 산출(효과성)과 형평 사이의 상충을 찾는 이기준 수리계획 모형 두 가지를 개발하고 공공도서관 지소 간 신간 배분에 적용했다.
- 원고 활용: 2.3. 단위(지소·구역) 간 배분 형평을 명시적으로 다룬 초기 모형. 구역별 최소기준 규칙의 이론적 뿌리로 인용 가능.

**B36** McAllister, D. M. (1976). Equity and efficiency in public facility location. *Geographical Analysis, 8*(1), 47–63. https://doi.org/10.1111/j.1538-4632.1976.tb00528.x
- verified: yes [초록: Crossref]
- 발견: 공공서비스 중심지의 규모와 간격 선택에 따른 형평·효율 효과를 평가하는 개념을 세웠고, 형평이 효율보다 규모·간격 선택에 더 민감하므로 입지 문헌에서 더 다뤄야 한다고 주장했다.
- 원고 활용: 2.3 보조(형평-효율 상충의 고전).

**B37** Batta, R., Lejeune, M., & Prasad, S. (2014). Public facility location using dispersion, population, and equity criteria. *European Journal of Operational Research, 234*(3), 819–829. https://doi.org/10.1016/j.ejor.2013.10.032
- verified: yes [초록: RePEc IDEAS 페이지]
- 발견: 분산·인구·형평 기준을 부가제약으로 둔 p-maxian 모형을 만들고 NP-완전성을 보였으며, 이 기준들을 적절히 쓰면 p-median 목적에서도 꽤 좋은 해를 얻는다고 보였다.
- 원고 활용: 2.3. 형평을 "목적"이 아니라 "부가제약(최소기준)"으로 거는 방식의 선례. 원고의 구역 최소기준 규칙과 형식이 같음.

**B38** Murray, A. T. (2016). Maximal coverage location problem: Impacts, significance, and evolution. *International Regional Science Review, 39*(1), 5–27. https://doi.org/10.1177/0160017615600222
- verified: yes (온라인 2015, 인쇄 2016) [초록: Crossref]
- 발견: Church & ReVelle(1974)의 MCLP가 기술적·실무적으로 얼마나 중요한지, 그리고 그 응용·해법·확장의 흐름을 개관했다.
- 원고 활용: Methods. MCLP 규칙의 표준 출처(Church & ReVelle 1974와 함께).

**B39** Church, R., & ReVelle, C. (1974). The maximal covering location problem. *Papers of the Regional Science Association, 32*(1), 101–118. https://doi.org/10.1007/BF01942293
- verified: yes [초록: 받지 못함. 서지만 확인]
- 발견: 초록을 받지 못해 내용 진술 없음(MCLP 원전으로서 서지 인용만).
- 원고 활용: Methods(원전 인용).

**B40 (서지 확인 요청분)** Karsu, Ö., & Morton, A. (2015). Inequity averse optimization in operational research. *European Journal of Operational Research, 245*(2), 343–359. https://doi.org/10.1016/j.ejor.2015.02.035
- verified: yes [초록: RePEc IDEAS 페이지]
- 발견: 배낭·일정·배정 등 여러 OR 문제를 형평 관점에서 다룬 문헌을 효율-형평 상충을 중심으로 개관했다.
- 원고 활용: 기존 인용 유지.

**B41 (서지 확인 요청분)** Bertsimas, D., Farias, V. F., & Trichakis, N. (2011). The price of fairness. *Operations Research, 59*(1), 17–31. https://doi.org/10.1287/opre.1100.0865
- verified: yes [초록: Semantic Scholar]
- 발견: 중앙 의사결정자가 여러 참여자에게 자원을 배분할 때, 효용 합 최대화 대비 "공정한" 배분(비례 공정성, 최대최소 공정성)이 낳는 상대적 효율 손실을 "공정성의 대가"로 정의하고 넓은 문제군에서 그 크기를 엄밀하게 규정했다.
- 원고 활용: 기존 인용 유지(구역 최소기준 규칙의 커버 손실을 "price of fairness"로 해석할 때).

---

## 4. 공백 주장은 성립하는가?

**판정: 대체로 성립하지만, 그대로 쓰면 반박당할 수 있어 좁혀서 써야 함.**

근거:
1. **격자·지점 단위로 사람을 채우는 연구가 주류다.** Bruno et al.(2024)은 200 m 육각 격자에서 1인당 시설 수를 같게 하는 탐욕 재배치를 하고 셀·도시 지표와 지니로만 평가한다. Horton et al.(2025, *Nat Commun*; 2025, *TR-B*)은 센서스 블록 수요에서 Kolm–Pollak EDE를 최소화하고 도시 단위로 평가한다. Xu et al.(2020)은 도시 평균거리를, Chen et al.(2023)은 15분 커버 인구(MCLP)를 성과로 보고한다. 이 연구들은 해가 어떤 계획 구역을 비워 두는지 묻지 않는다.
2. **"생활권"을 내건 중국의 최적화 연구도 구역 결과를 시험하지 않는다.** Zhai et al.(2023)의 μCFLP는 커버율 제약을 사례지역 전체로 걸고, Wu et al.(2021)과 Wu et al.(2026)은 평가 뒤 전략 제안이거나 목적함수가 초록에 드러나지 않는다.
3. **설계형 최적화는 한 근린 안의 문제다.** Lima et al.(2022), Zheng et al.(2023)은 단일 근린·커뮤니티 배치를 최적화하므로 구역 간 배분 문제가 아니다.
4. **반례·부분 반례가 있다. 원고는 이를 반드시 인정해야 한다.**
   - **Pemberton et al.(2026, *Cities*)**은 활동중심지 집수구역마다 "인구 80% 이상이 각 목적지 유형에 10분 안에 닿도록" 추가 배치한다. 구역별 최소기준을 제약으로 둔 x분 도시 배치 연구가 투고 학술지에 이미 있다는 뜻이다.
   - Jafari et al.(2023)은 여러 근린을 함께 다루며 목적지별 커버율 목표를 둔다(근린별인지는 초록으로 확인 안 됨).
   - Huang & Khalil(2023)은 근린 31곳을 사례로 결과를 근린별로 보고한다.
   - 입지 OR 문헌에서는 Chanta et al.(2014)이 최대 커버가 밀집지를 편애해 희박 지역을 남긴다는 점을 이미 지적했고, Batta et al.(2014)과 Mandell(1991)은 형평을 부가제약이나 단위 간 배분으로 넣었다.
5. **그래도 남는 공백**: 확인한 문헌 가운데 (a) 같은 실제 추가 시설 집합을 격자 규칙(최대 커버, 취약성 가중)과 구역 규칙(구·생활권·동 최소기준)으로 함께 배치해 비교하고, (b) 다부문 완결성(6개 부문 모두 10분 안)을 기준으로 (c) "아무도 완결 접근을 못 하는 계획 구역 수"를 결과 지표로 센 연구는 없었다. 구역 기준을 쓴 연구(Pemberton, Jafari)는 구역을 처음부터 제약으로 넣을 뿐, 구역이 "필요한지"를 격자 규칙과 맞대어 시험하지 않는다.

**원고 문장 수정 제안**: "location studies optimise people but do not test whether solutions leave planning zones empty" → "Location studies for the 15-minute city mostly optimise population coverage or distributional equity on fine grids or blocks (Bruno et al., 2024; Horton et al., 2025; Xu et al., 2020); where zones enter, they are imposed as targets from the outset (Jafari et al., 2023; Pemberton et al., 2026) rather than tested against grid rules. No study we found compares grid- and zone-based rules on the same facilities and counts the planning zones left without complete multi-domain access."

---

## 5. 확인하지 못한 것(원고에 넣지 말 것 또는 원문 대조 필요)

- **Barbieri et al.(2023)**: 15분 도시 관련 해당 논문을 찾지 못함. 제외.
- **Song et al.(2022) 용량제약 p-median**, **Wang et al.(2022)**: 검색엔진 요약에서 Arslan & Laporte(2025) 리뷰가 인용한 것으로 나왔으나 원 논문을 특정·확인하지 못함. Wang et al.(2022)가 Lima et al.(2022, B25)을 잘못 적은 것인지도 확인 못 함. 제외.
- **Arslan & Laporte(2025)가 최적화 연구를 몇 편 다뤘는지**("7편 중 6편이 입지"): 검색엔진 요약으로만 봤고 본문을 열람하지 못함. 원고에 수치로 쓰지 말 것.
- **Ogryczak(2000), *EJOR* 122(2), 374–391**: 서지는 Crossref로 확인했으나 초록을 받지 못해 목록에서 뺌.
- **Current & Schilling(1987)**(p-median의 A·B 오차 제거): 확인하지 않음.
- **arXiv 2603.12122 "Why urban heterogeneity limits the 15-minute city"**, **Urban Science 8(4):259(2024) AI·15분 도시 최적화 리뷰**: 검색에 나왔으나 확인하지 않음(앞의 것은 심사 전 사전공개본).
- **초록을 API로 직접 받지 못하고 검색엔진 요약으로 대조한 항목**: Song et al.(2024, B11), Marsh & Schilling(1994, B32), Pemberton et al.(2026, B16, 학술지판; SSRN판 초록은 Crossref로 받음). 인용 전에 원문 초록과 대조 권함.
- **세부 설계를 초록으로 판정하지 못한 항목**: Huang & Khalil(근린별로 따로 푸는지), Jafari et al.(커버율 목표가 근린별인지), Chen et al.(최적화 결과의 구별 평가 여부), Young et al.·Zhai et al.·Wu et al. 2026·Rhoads et al.(수요 단위). 해당 칸은 unclear/partly로 표시함.
- Church & ReVelle(1974): 서지만 확인, 초록 없음(내용 진술 안 함).
