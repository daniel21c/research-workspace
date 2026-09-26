# 서울 시설 접근성 패키지 2020 · 2025 (access-engine-v3)

서울 33종 시설(facility-v1.2) × 100 m 격자 인구 × OSM 보행망으로 **네 가지 접근성 지표**(도달시간·Coverage·MAI·2SFCA)를 두 시점, 다섯 경계 조건에서 계산한 결과와, 그것을 만든 입력·코드·정의·검증 문서를 한 폴더에 모은 패키지다. **다른 연구 코드는 이 패키지의 `데이터/결과/`만 참조한다.**

| 항목 | 값 |
|---|---|
| 본 결과 | `데이터/결과/main/unit_access_{2020,2025}_100.csv`(도달시간·Coverage·MAI), `데이터/결과/main/sfca_unit_{2020,2025}_100.csv`(2SFCA) |
| 시설 입력 | `시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet` = 배포목록 facility-v1.2 (SHA-256 `b87ed1cc…f39f`) |
| 시점 | 2020 = 시설 2019-12-31 + 인구 2019(SGIS) + 보행망 2020-01 / 2025 = 시설 2024-12-31 + 인구 2024 + 보행망 2025-01 |
| 경계 조건 b | 없음 · 동 424 · 공식 생활권 116 · Leiden 116(연도별) · 구 25 — "도착 격자가 출발 격자와 같은 단위 안" |
| 집계 단위 | 동 424 · 공식 생활권 116 · Leiden 116 · 구 25 · 서울 (상위 단위는 항상 격자 값의 분자합/분모합) |
| 검증 | `문서/검증보고서.md`, `데이터/검증결과.json` (입력 해시·단위시험·불변조건·2SFCA 독립 구현·재실행 결정성·판 변경·순위 안정성) |
| 해시 | `데이터/manifest_sha256.csv` — 패키지 모든 파일의 SHA-256 |
| 좌표계 | EPSG:5179 (SGIS 격자와 같음) |

## 1. 폴더

```
접근성분석_패키지/
├─ README.md                    ← 이 문서
├─ 문서/                        ← 공동연구자는 여기부터 (2절 읽는 순서)
│  ├─ 지표정의_확정.md            네 지표의 유일한 정의 출처
│  ├─ 검증보고서.md               무결성·신뢰성 검증 결과(코드가 생성)
│  ├─ 자료가공설계.md             자료 가공 단계 P1~P7, 연구별 사용
│  ├─ 접근성엔진_구축기록.md       엔진 규칙·검증값·한계
│  ├─ 격자마스터_·시설경계연결_·경계기하지표_·네트워크_소요시간표_구축기록.md
│  ├─ 선행연구_지표정의_조사.md
│  └─ 작업기록.md                 날짜별 경과
├─ 코드/                        ← a00(설정) ~ a10(검증), tests/, run_engine.bat, run_ttm.bat, requirements.txt
└─ 데이터/
   ├─ 입력/                     grid(100·250 m 격자 마스터), facility(시설–경계 연결표), boundary(코어엔진 정본 사본·기하 지표),
   │                           network(보행 그래프 2020·2025), ttm(격자→격자 보행 소요시간표, 30분 이내), external(비교용 원고 인쇄값)
   ├─ 결과/                     실행 세트(tag)별 폴더 + tables/ + figures/ + summary_sensitivity.md
   ├─ 검증결과.json
   └─ manifest_sha256.csv
```

## 2. 읽는 순서
1. **`문서/지표정의_확정.md`** — 네 지표의 식, 33종 → 기능 카테고리 8개, 경계 조건, 민감도 목록.
2. **`문서/검증보고서.md`** — 입력이 확정본과 같은지, 계산이 맞는지, 결과가 설정에 강건한지.
3. `데이터/결과/main/summary_main.md` — 본 분석 요약(서울 종합값, 카테고리별 값, 동별 Δ(Leiden − 공식), 2020→2025 변화, 2SFCA).
4. `데이터/결과/summary_sensitivity.md` — 민감도 비교와 2020→2025 변화의 보행망 몫 분해.
5. `데이터/결과/tables/`, `figures/` — 연구3 T5·F3, 구별 표(승훈 원고 비교), 2SFCA 경계 개방비.
6. `문서/접근성엔진_구축기록.md` — 구현 규칙과 한계. 코드: `코드/a00_config.py` → `a06_engine.py` → `tests/test_engine.py`.

이력 문서(`작업기록.md`, 2026-09-24 구축기록들)는 정리 전 폴더 이름으로 적혀 있다. 대응: `00_설계/`·`04_구축기록/` → `문서/`, `02_scripts/` → `코드/`, `01_data/` → `데이터/입력/`, `03_output/` → `데이터/결과/`.

## 3. 네 지표 (정의 원문은 `문서/지표정의_확정.md` 3절)

임계 T = 도보 15분(4.0 km/h), 기능 카테고리 c = 교육·보육·복지·의료·문화·체육·행정·안전·소매·생활서비스.

| 지표 | 격자 값 | 단위 값 | 뜻 |
|---|---|---|---|
| 도달시간 PWATT | 가장 가까운 c 시설까지 보행시간 | 15분 안에 닿은 인구만의 인구가중 평균(초) | 얼마나 가까운가 |
| Coverage (COV) | 15분 안에(경계 조건 아래) c 시설이 있으면 1 | 도달 인구 ÷ **전체 인구**, 종합 = 8개 평균 | 누가 닿는가 |
| MAI | 닿는 c 시설 격자 중 동시입지 카테고리 수의 최댓값 | 도달 인구 가중 평균(**분모 = 도달 인구**, 미도달은 정의 안 됨), 종합 = 값 있는 카테고리 평균(1~8) | 한 번 외출로 몇 가지 기능을 함께 쓰는가 |
| 2SFCA | 15분 안 시설들의 (시설 수 ÷ 그 시설에 닿는 인구) 합 | 인구가중 평균 × 10,000 = **인구 1만 명당 시설 수**, 종합 없음 | 닿는 시설을 몇 명이 나눠 쓰는가 |

- 2SFCA는 카테고리 8개와 시설 28종 각각에 대해 계산하고, 공공시설 7종(공공도서관, 주민센터, 보건소·보건지소, 어린이집, 유치원, 학교, 노인 이용시설)을 먼저 보고한다. 보조 산출 **경계 개방비** OR = 2SFCA(경계 없음) ÷ 2SFCA(그 단위 자신의 경계): 1에서 멀수록 그 단위가 이웃 단위와 시설을 주고받는다.
- MAI 필수 문구: MAI는 경계 안에서 해당 카테고리 시설에 도달한 인구만을 대상으로 한 조건부·상한 지표이며, 실제 통행사슬을 재현하지 않는다. 도달하지 못한 인구의 값은 0이 아니라 정의되지 않으며, 그 사정은 Coverage가 보여 준다.

## 4. 결과 파일

실행 세트(tag): `main`(본 분석) · `sens_T600`(10분) · `sens_speed36`(3.6 km/h) · `sens_grid250`(250 m) · `sens_A4`(카테고리 4개) · `sens_retail_without`(일상소매 제외) · `sens_union`(합집합 카테고리 수) · `sens_net2025`(2020 시설·인구 + 2025 보행망) · `sens_snap`(스냅 거리 포함, 2026-09-26 추가) · `natstd_B`(국가 최저기준 충족률).

| 파일 | 열 |
|---|---|
| `unit_access_{연도}_{격자}.csv` | year, grid_m, T_sec, speed_kmh, catset, retail, unit_level(dong424·lz116·ld·ku·seoul), unit_id, b(none·dong424·lz116·ld·ku), cat(8개+종합), pop_total, pop_reach, COV, MAI, PWATT_sec, n_cat_mai (+ sens_union: UNI, UNI_allpop) |
| `sfca_unit_{연도}_{격자}.csv` | year, grid_m, T_sec, speed_kmh, retail, unit_level, unit_id, b, item_type(category·facility), item, pop_total, supply_in_unit, supply_unassigned_in_unit, SFCA_per10k, pop_share_A0(15분 안 시설 없는 인구 비율), open_ratio(b = none 행만) |
| `grid_access_{연도}_{격자}.parquet` | 격자 × b × 카테고리: grid_cd, b, cat, pop, r, m, t_min_sec |
| `grid_sfca_{연도}_100.parquet` (main만) | 격자 × b × 항목: grid_cd, b, item, A_per10k |
| `natstd_B/nat_standard_coverage_{연도}_100.csv` | 국가 최저기준 5개 카테고리·하위유형별 충족률 |
| `run_meta_*.json` | 설정, 입력 행 수, 불변조건 검사, 결과 파일 해시 |

```python
import pandas as pd
R = r'.../06_접근성분석/접근성분석_패키지/데이터/결과'
u = pd.read_csv(fr'{R}\main\unit_access_2025_100.csv')
dong = u[(u.unit_level == 'dong424') & (u.cat == '종합') & (u.b.isin(['lz116', 'ld']))]      # 연구3: 동별 공식·Leiden 값
s = pd.read_csv(fr'{R}\main\sfca_unit_2025_100.csv')
lib = s[(s.unit_level == 'dong424') & (s.b == 'none') & (s.item == '공공도서관')]            # 동별 도서관 1만 명당
```

## 5. 다시 만들기 (`코드/`)
```
pip install -r 코드/requirements.txt                 # numpy, pandas, pyarrow, scipy, geopandas, matplotlib 등
코드/run_engine.bat                                   # 시험 → 전 실행 세트 → 요약·표·그림 → 검증(a10). 이 PC 약 8분 (facility 옵션 포함 약 9분)
코드/run_engine.bat facility                          # 시설 자료가 바뀌었을 때: a02(시설–경계 연결)부터
python 코드/a10_verify.py --check-only                # 받은 파일의 해시만 확인(계산 없음)
```
- 입력 자료를 처음부터 만들기: `a01_grid_master.py`(SGIS 격자) → `a02`(시설) → `a03`(경계 기하) → `run_ttm.bat`(a04 보행망, a05 소요시간표) → `a05c_ttm_supplement.py`(네트워크 고정용 보충표). 원천은 `시설데이터 구축/시설데이터_패키지/`(시설·SGIS·OSM 원본)와 `00_공통_코어엔진/data/`(경계 정본).
- 한 구만 시험: `코드/run_engine.bat test` (출력은 %TEMP%). 2SFCA는 집수역이 구를 넘으므로 서울 전체 실행에서만 계산한다.

## 6. 변경 이력
| 판 | 날짜 | 내용 |
|---|---|---|
| access-engine-v1 | 2026-09-24 | 도달시간·Coverage·MAI, 8개 실행 세트, facility-v1 |
| (v1 재계산) | 2026-09-25 | facility-v1.1, 네트워크 고정 민감도(sens_net2025) 추가 |
| access-engine-v2 | 2026-09-25 | **2SFCA 추가(네 번째 지표)**, facility-v1.2로 전 세트 재계산, 06 폴더를 이 패키지 하나로 정리, 무결성·신뢰성 검증 스크립트(a10) |
| **access-engine-v3** | 2026-09-26 | 코드 점검(중복·누락·호환성) 반영 후 전 세트 재계산(**확정본**): 2SFCA 공급 중복 제거(문화기반시설의 공공도서관, 같은 이름·좌표 행), 연구3 ΔMAI 종합 = 두 경계 공통 카테고리의 Δ 평균(`코드/a06c_delta.py`), 시설–경계 연결표의 원본 해시 기록·검증(`데이터/입력/facility/facility_2020_2025_units.source.json`), `run_meta`에 실행 환경(파이썬·numpy·pandas·pyarrow 판) 기록, 단위시험 16개. 도달시간·Coverage·MAI 값은 v2와 모든 행이 같다(`문서/검증보고서.md` 3절). |

정리하면서 뺀 코드·문서(옛 공유패키지 문서, 옛 _archive 기록, a09)는 `D:\Research\_archive\접근성분석_정리_20260925\`에 있다. 이전 판 결과 추출본(access-engine-v1·v1.1·v2 결과, 시설 csv 사본)은 v3 확정과 함께 삭제했다(2026-09-26 사용자 결정; 이력은 `문서/작업기록.md`·`데이터_배포목록.md`의 해시).
