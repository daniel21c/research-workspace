# 연구1 공동연구자 검토본 (2026-10-02, 설계 4판) — 받는 분 안내

## 1. 푸는 위치
공유받은 허브 폴더 `00_박사논문_연구체계/`의 **루트에 그대로 푼다.** ZIP 안 경로가 허브 루트 기준이라 파일이 제자리에 들어간다.
- 같은 이름의 연구1 파일(예: `01_생활권_필요성/연구설계.md`, `작업기록.md`)은 이 판으로 덮어써진다. 이전 판은 Git 이력과 작성자 PC의 허브 밖 보관 폴더에 있다.
- 다른 연구 폴더(02~07), 접근성 패키지, 시설 v1.4, 경계 자료는 **들어 있지 않고 바꾸지도 않는다.**
- 허브 문서 사본(`README.md`, `박사논문_연구설계.md`, `데이터_배포목록.md`, `공유_안내.md`)은 작성자 PC의 현재본이다. 받은 분의 허브에 더 새 판이 있으면 그쪽을 두고 이 사본은 건너뛴다.

## 2. 무엇을 봐 주시면 되나
`01_생활권_필요성/package/공동연구자_검토요청_20261002.md`(4판)에 답, 읽는 순서, 결과 요약, 검토 항목 7개가 있다. 4쪽 요약은 `보고_20261002/교수님_보고_20261002.md`. 의견은 그 옆에 `공동연구자_검토의견_YYYYMMDD.md`로 남기거나 편한 방식으로 보내 주시면 된다.

## 3. 들어 있는 것
| 경로 | 내용 |
|---|---|
| `01_생활권_필요성/*.md` | README, 연구설계(4판), 작업기록, 검수의견 대응표, 구성변경 대조표 |
| `01_생활권_필요성/manuscript/` | 결과총람(분석항목 25개), 원고구성, 문헌대조, 그림 |
| `01_생활권_필요성/package/` | 이 안내, 공동연구자 검토요청, `make_package.py` |
| `01_생활권_필요성/보고_20261002/` | 교수님 보고 md, Teams 보고글, 그림 A·B, 다른 연구 알림 |
| `01_생활권_필요성/code/` | 실험 코드 전부(공통 `r1lib.py`, `bundlelib.py`) |
| `01_생활권_필요성/results/` | 결과 표 `표4.1-*`(exp20은 `표4.1-23_권역최저선_*`), 그림 `그림_필요성A·B`, `그림_묶음1~4`, `그림4.1-*`, 정수해 대조, 배치·정수계획 입지 JSON(`exp14_placements_*`, `exp16_milp_picks_*`, `exp20_picks_*`) |
| `01_생활권_필요성/results/run0930/`, `run1002/` | 9/30 실행 로그·종합 정리(10-01 기준), 10/02 재실행·exp20 로그 |
| `01_생활권_필요성/검수기록/` | 외부 검토 1~3차 원문·검증 파일·프롬프트 |
| `시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001/` | 공원·공공체육·지역아동센터 부가 층 parquet, 원자료, 구축코드, 해시 |
| `00_선행연구/pdf/2026_JassoChavez_…md` | Jasso Chávez 외(2026) 본문 요지 사본 |
| `검토본_목록.csv` | ZIP 안 모든 파일의 크기·SHA-256 |

넣지 않은 것: 선행연구 PDF(서지·DOI는 `manuscript/문헌대조/원문대조표_D3_20261001.md`), 연구1 `packages/`·`_archive_codex_20260929/`(9/29 Codex 산출물, 현재 설계에서 쓰지 않음), 가상 통제실험의 세계별 원자료.

## 4. 다시 돌려 보려면
필요한 입력은 공유 허브에 이미 있다: `06_접근성분석/접근성분석_패키지/데이터/`(격자·보행 TTM·시설 v1.4·접근성 결과), `00_공통_코어엔진/`(경계, `exploration/xcommon.py`), 부가 층(이 ZIP). 코드는 허브 상대경로만 쓴다.

환경: Python 3.12, numpy·pandas·pyarrow(공유 안내의 requirements), **scipy 1.9 이상**(정수계획 `scipy.optimize.milp`, 작성자 1.17.1), matplotlib. 부가 층을 다시 만들 때만 geopandas·shapely·pyproj.

```
cd 01_생활권_필요성/code
python exp13_bundle_defs.py 2020            # 묶음 정의별 완결·결손 수·곡선 (표4.1-16), 2025도
python exp14_bundle_place.py seoul 2020     # 유형별·조정·하한·권역별 배치 (표4.1-18), logan7 / 2025도
python exp16_bundle_milp.py seoul 2025 3600 # 정수계획 (표4.1-19)
python exp16_bundle_milp.py seoul 2020 10800 nolp   # 2020은 3시간, LP 상한 생략
python exp16_bundle_milp.py seoul 2025 7200 nolp T900  # 15분 변형(T720 도 가능)
python exp16_low20.py                       # 정수계획·IND 정확해 입지의 하위 20% 완결률 (표4.1-19_정확해_하위20)
python test_greedy_exact.py                 # 정확 탐욕 검정
python exp17_centers.py seoul               # 중심 구조 (표4.1-20)
python exp18_service_vs_common.py seoul 2020 5      # 서비스별 vs 공통 권역·요인 비교·공유/개별 짝 비교 (표4.1-21), 2025도
python exp19_holdout_sens.py                # 시간 외 표본·추가 수·자료 민감도 (표4.1-22)
python exp15_usage.py 2020                  # 15분 이용 vs 접근 (표4.1-17), 2025도
python exp20_bundle_floor.py 2025 공식LZ 0.05 14400   # 권역별 묶음 최저선 (표4.1-23); 단위 공식LZ|Leiden|구|동|rand116_<seed>, τ 0.01|0.05
python run_exp20.py 5 5400                  # exp20 20개 설정 일괄(동시 5개)
python fig_bundle.py                        # 그림_묶음1~4
python fig_necessity.py                     # 그림_필요성A(빈 생활권 지도)·B(규칙별 빈 생활권)
python report_docx.py                       # 교수님 보고 docx
```
결과는 `01_생활권_필요성/results/`에 덮어쓴다. 받은 결과와 비교하려면 먼저 `results/`을 복사해 두고 돌린다. 앞 단계 실험(표4.1-1~13)의 정확한 명령은 `results/run0930/queues.sh`에 있다.

부가 층 재구축(선택): `python "시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001/build_addon.py"` 후 `manifest_sha256.csv`와 대조.
