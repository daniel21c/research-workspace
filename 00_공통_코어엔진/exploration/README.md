# exploration — 생활권 개수(k) 탐색 · 최적화 검증 · 제안 경계 (x1~x14)

정본 파이프라인(`scripts/s01~s06`)은 구마다 개수를 공식 생활권 수로 **고정**한다(합 116).
이 폴더는 그 고정을 잠시 풀고 네 가지를 본다: "이동 자료가 스스로 고르면 몇 개인가"(x1~x9), "개수를 바꿔도 결과가 유지되나"(x10),
"최적화하면 공식 생활권과 무엇이 달라지나"(x11~x13), "인구 균형까지 지키면 경계가 어떻게 되나"(x14).
**정본(`data/`, `output/leiden/{연도}`)은 읽기만 하고 아무것도 바꾸지 않는다.** 결과는 `output/exploration/`, `output/proposal/`,
태그가 붙은 `output/leiden/{연도}_{태그}/` 에 쓴다. 전체 흐름과 결론은 [k최적화_작업정리.md](k최적화_작업정리.md), 결정과 근거는 `../결정기록.md` §12~16에 있다.

## 실행 (PC, 8코어 기준, 순서대로)

```powershell
cd D:\Research\00_박사논문_연구체계\00_공통_코어엔진\exploration
pip install -r requirements_exploration.txt   # 정본 requirements 위에 matplotlib 추가
.\run_exploration.bat      # ① 개수 탐색 x1~x4, x6~x9 (x5 는 건너뜀)                 30~50분
.\run_k_sensitivity.bat    # ② 개수 민감도: x10 → s03 --targets (_kmob_lo/_hi) → s06 --compare   약 45분
.\run_proposal.bat         # ③ 최적화 검증: x11 → s03 --targets (_qmax = P1) → x12 → x13         약 40분
.\run_dual_objective.bat   # ④ 이중 목표 제안 경계: x14 → x11 → x12 → x13                     15~30분
```

- ②③은 정본과 같은 시드(`--seed canonical`)로 목표 개수만 바꿔 s03을 다시 돌린다. 그래서 차이는 개수에서만 나온다. 태그 없이 설정을 바꾸면 s03이 실행을 거부한다.
- ③은 ①의 결과(x2 무작위 기준선, x4 귀무 Q, x6~x8 라벨)를, ④는 ③의 결과를 쓴다.
- 하나씩 돌릴 때는 bat 안의 `python …` 줄을 그대로 입력하면 된다.
- bat 파일은 일부러 영문 ASCII + CRLF 줄바꿈으로 둔다. 한글이나 LF 줄바꿈이 들어가면 cmd가 줄을 잘못 읽어 엉뚱한 명령을 실행하려 한다(2026-09-24에 실제로 겪음).

## 스크립트

| 파일 | 아이디어 | 무엇을 보나 | 입력 | 시간(8코어) |
|---|---|---|---|---|
| xcommon.py | — | 공통 함수: 정본 읽기, 구 그래프(KuGraph), SGIS 인구 → 424동, 무작위 연결 분할 | | |
| x1_frontier_knee.py | A1, C3 | 같은 개수에서 Leiden 이 얻는 최대 IFR 곡선 F(k); 공식 IFR 과 같은 값을 주는 "등가 개수"; 곡선 무릎점 | 정본 스캔 로그 | 수초 |
| x2_size_corrected_ifr.py | A2 | 같은 개수의 무작위 연결 경계(자유/동 수 균형/인구 균형) 대비 IFR z·백분위 | od, 인구 | 10~20분 |
| x3_q_band_plateau.py | B1, B4 | 개수별 최대 Q, Q 최대에서 ε 이내 개수 범위, 해상도 평탄 구간 | 정본 스캔 로그 | 수초 |
| x4_null_model_q.py | B3 | 통행 규모는 같고 구조는 없는 귀무 그래프 대비 Q 의 z; z 최대 개수 | od | 5~15분 |
| x5_sbm_mdl.py | B2 | 확률블록모형 + 최소 기술 길이로 개수 선택 (동류 PP 모형, 일반 가중 SBM) | od | **graph-tool 필요 → 클라우드에서 실행, 결과 동봉** |
| x6_ttwa_selfcontainment.py | C1 | 영국 TTWA 방식: 모든 권역이 자족성 문턱을 넘을 때까지 합침 → 개수는 결과 | od, 인구 | 1분 |
| x7_maxp_regions.py | C2 | max-p-regions: 인구 하한만 주고 개수 최대 | od, 인구 | 1~3분 |
| x8_citywide_leiden.py | D | 구 경계 없이 424동 전체 Leiden; 구에 걸친 커뮤니티 | od | 10~20분 |
| x9_summary.py | — | x1~x8 을 한 표·한 문서로 | 위 결과 | 수초 |
| x10_k_targets.py | 민감도 | 이동 기반 4개 방법의 구별 중앙값 → 목표 개수 파일 `kmob_lo`·`kmob_hi` (.5 를 공식 쪽 / 먼 쪽으로) | `k_methods.csv` (x9) | 수초 |
| x11_scenario_partitions.py | 검증 | 시나리오(P0 공식, P0c 정본, P2·P2a·P2b TTWA, P3 max-p, P4 서울 전체, P5 계열)의 동별 라벨을 한 파일로; P1 목표 개수 | x6~x8, x14 결과 | 수초 |
| x12_scorecard.py | 검증 | 시나리오 점수표: k, IFR, Q, z_pop, z_Q, 인구 CV, ARI (서울·구별) | x11, x2·x4 기준선, P1 경계 | 5~10분 |
| x13_changes_and_maps.py | 검증 | 공식 대비 바뀐 동, 두 해 공통 판정, P5 채택 판정, 제안 경계 gpkg, 지도 | x12 | 1~3분 |
| x14_dual_objective.py | 제안 | 개수 = 공식, Q 최대, 권역 인구 ≥ 2만(민감도 3만·5만), 공간 연속 — 제약 국소 탐색(담금질) | od, 인구, 정본 | 5~15분 |

문서: 설계 [최적화검증_설계.md](최적화검증_설계.md)(x11~x13)·[이중목표_제안경계_설계.md](이중목표_제안경계_설계.md)(x14), 해석 [해석_메모.md](해석_메모.md)(x1~x9), 논문 문단 초안 [개수고정_근거_초안.md](개수고정_근거_초안.md), 전체 정리 [k최적화_작업정리.md](k최적화_작업정리.md).

## 출력

`output/exploration/` (x1~x10)
- `탐색결과_요약.md` — 모든 방법의 합계·구별 개수·품질 지표 한곳에. `exploration/해석_메모.md` 가 뒤에 붙는다.
- `k_methods.csv` — 구·연도 × 방법별 개수, `k_totals.csv` — 방법별 합계, `k_targets_kmob_{lo,hi}.csv` — x10 목표 개수
- `x1/ … x8/` — 방법별 csv 와 `x*_report.md`
- `_cache/pop_dong424_{연도}.csv` — SGIS 총인구를 424동에 붙인 값 (2020 이동 ↔ 2019 인구, 2025 ↔ 2024)

`output/proposal/` (x11~x14)
- `scorecard.md`, `scorecard_{seoul,ku,change}.csv` — 시나리오 점수표 (2026-09-25 서울 IFR 정정본, `../결정기록.md` §16)
- `robust_changes.md`, `changes_{연도}.md` — 공식 대비 변화와 두 해 공통 판정
- `p5_cost_of_balance.md`, `p5_adoption.md`, `p5_partitions.csv` — 이중 목표 결과와 구별 채택 판정
- `proposal_boundary_{연도}.gpkg` — 제안 경계(두 해 모두 'P5 채택'인 구는 P5, 나머지는 공식). **탐색 산출물이며 배포본이 아니다.**
- `maps/` — 구별 25장 + 서울 1장

`output/sensitivity/` (정본 s06) — `sensitivity_compare_20260924_143322.md`(개수 민감도 kmob), `k_diagnostic.md`

`output/leiden/{연도}_{kmob_lo,kmob_hi,qmax}/` — 목표 개수를 바꾼 s03 경계(정본과 같은 시드)

## 주의

- 전부 **탐색용**이다. 정본 경계·개수를 바꾸자는 결과가 나오더라도, 바꾸는 것은 따로 결정한 뒤 정본 파이프라인에서 한다.
- 시드: 확률적인 스크립트(x2, x4, x7, x8, x14)는 `--seed` 기본값 20260924 로 고정해 재현되게 했다 (정본과 달리 탐색은 재현성이 우선).
- 시나리오 라벨은 구마다 0부터 다시 매긴다. 서울 전체로 모아 비교할 때는 반드시 구 코드를 붙인 라벨을 쓴다(x12 서울 IFR 오류의 원인, §16).
- x5 에서 graph-tool 의 `get_blocks().a` 는 복사하지 않으면 상태가 해제될 때 덮어써진다 → 복사하도록 고침 (첫 실행 결과는 폐기).
- x5 의 동류 SBM 은 통행량을 정수 간선 수로 바꿔 쓴다. 나누는 값(`--scale`) 31·310·3100 에서는 결과가 거의 같고,
  31000(하루 1,000통행 단위)에서는 약한 연결이 모두 1 로 올려져 구조가 흐려진다 → 요약에는 310 을 쓴다.
