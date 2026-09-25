# 06_접근성분석 — 서울 시설 접근성 공통 엔진 (2020 / 2025)

- 담당: 시설데이터 구축·접근성 대화(Cowork/Claude). 사용자 확정 2026-09-24.
- 하는 일: 33종 시설 × 100m 격자 인구 × 보행 네트워크로 **Coverage · MAI · 도달시간**을 두 시점(2019-12-31, 2024-12-31), 다섯 경계 조건(없음·동·공식 생활권·Leiden·구)에서 계산해 연구1(필요성)·연구3(AG)·연구4(KPA)가 같은 입력을 쓰게 한다.
- 공동연구자는 `00_설계/`의 두 문서(지표 정의, 자료 가공 설계)와 `04_구축기록/`만 읽으면 무엇을 왜 어떻게 만들었는지 알 수 있다. 코드는 단계 번호 순서대로 실행하면 재현된다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `00_설계/` | `지표정의_확정.md`(유일한 정의 출처), `자료가공설계.md`, `선행연구_지표정의_조사.md` |
| `01_data/` | 입력·중간 산출: `grid/`(격자 마스터 100m·250m), `facility/`(경계 열 붙은 33종), `boundary/`(코어엔진 정본 사본 + 기하 지표·인접행렬), `network/`(보행 그래프 2020·2025), `ttm/`(격자→격자 보행 소요시간표; `ttm100_2025_for2020/` = 네트워크 고정 민감도용 보충표), `external/`(승훈 씨 원고 인쇄값 전사, 비교용) |
| `02_scripts/` | `a00_config.py`(경로·상수 한 곳), `a01_grid_master.py`, `a02_facility_boundary.py`, `a03_boundary_metrics.py`, `a04_network.py`, `a05_ttm.py`(+ `a05b_record.py` 기록 생성, `run_ttm.bat` PC용, `requirements.txt`), `a05c_ttm_supplement.py`(다른 시점 보행망용 보충 소요시간표), `a06_engine.py`(접근성 엔진, `--net-year` 네트워크 고정), `a06b_summary.py`(요약표·네트워크 분해), `a07_study3_outputs.py`(연구3 T5·F3), `a08_ku_compare.py`(경계 없는 구별 표·승훈 원고 비교), `a09_share_package.py`(공유 패키지), `a99_manifest.py`(해시 목록 갱신), `run_engine.bat`(P5 전체 재현, PC용), `tests/`(`test_engine.py` 손계산 예제·독립 구현 대조, `test_geometry.py`) |
| `03_output/` | P5 엔진 결과. 실행 세트(tag)별 폴더: `main`(본 분석), `sens_T600`·`sens_speed36`·`sens_grid250`·`sens_A4`·`sens_retail_without`·`sens_union`(민감도), `natstd_B`(국가 최저기준), `sens_net2025`(2020 시설·인구 + 2025 보행망; 2020→2025 변화의 네트워크 몫 분해 `decomp_network_2020_2025.csv`), `tables/`(T5, F3 자료, 구별 표·승훈 비교), `figures/`(F3 지도). 각 폴더에 `grid_access_{연도}_{격자}.parquet`(격자 × 경계 조건 b × 카테고리: r, m, t_min_sec), `unit_access_{연도}_{격자}.csv`(동424·LZ116·LD·구·서울 × b × 카테고리+종합: 전체·도달 인구, COV, MAI, PWATT_sec), `run_meta_*.json`(설정·입력 수·불변조건·해시), `summary_{tag}.md`. 묶음 B는 `nat_standard_coverage_*.csv`. 민감도 비교는 `summary_sensitivity.md` |
| `04_구축기록/` | 단계별 구축기록(원천·해시·규칙·검증값), 작업기록 |
| `05_공유패키지/` | 교수님·공동연구자용 묶음(정의·코드·결과 CSV·해시). 읽는 순서는 그 폴더 `README.md`. `a09_share_package.py`로 다시 만든다(압축 파일 없음) |
| `_archive/` | 이전 판·안 쓰는 파일(삭제하지 않음). `2026-09-24_정리/README.md`에 옮긴 목록 |

## 실행 순서

```
python 02_scripts/a01_grid_master.py            # 격자 마스터 100m·250m
python 02_scripts/a02_facility_boundary.py      # 시설에 동424·LZ·LD·카테고리 열
python 02_scripts/a03_boundary_metrics.py       # 생활권 면적·컴팩트성, 동 인접행렬
python 02_scripts/a04_network.py --year 2020    # OSM → 보행 그래프 (2025도)
python 02_scripts/a05_ttm.py --year 2020 --grid 100   # 소요시간표 (전체 4조합: run_ttm.bat; 기록: a05b_record.py)
python 02_scripts/a06_engine.py --year 2020 --grid 100 # Coverage·MAI·도달시간 (본 분석 tag=main; 민감도·묶음 B 전체는 run_engine.bat)
python 02_scripts/a05c_ttm_supplement.py --net 2025 --for-year 2020 --grid 100   # 보충 소요시간표 (네트워크 고정용)
python 02_scripts/a06_engine.py --year 2020 --grid 100 --net-year 2025 --tag sens_net2025
python 02_scripts/a06b_summary.py               # 03_output 요약표
python 02_scripts/a07_study3_outputs.py         # 연구3 T5·F3
python 02_scripts/a08_ku_compare.py             # 경계 없는 구별 COV·MAI, 승훈 원고 비교
python 02_scripts/a09_share_package.py          # 05_공유패키지 다시 만들기
python 02_scripts/tests/test_engine.py          # 손계산 예제·독립 구현 대조 (pytest 있으면 python -m pytest 02_scripts/tests)
```

## 원칙
- 지표 정의는 `00_설계/지표정의_확정.md`에서만 바꾼다.
- 원천 폴더(`시설데이터 구축/`, `00_공통_코어엔진/`, SGIS)는 읽기만 한다. 결과는 이 폴더에만 쓴다.
- 모든 산출 파일은 `04_구축기록/manifest_sha256.csv`에 해시를 남긴다.
- 무거운 계산(소요시간표 전체)은 사용자 PC에서 `.bat`으로 실행한다(CRLF·ASCII).
- 논문 수치는 `03_output/`의 파일에서만 나온다. 문서에 손으로 숫자를 적지 않는다.
- API 키는 `D:\Research\_secrets\facility_api.env`에서만 읽고 어디에도 기록하지 않는다.

## 관련 문서
- 기준: `../박사논문_연구설계.md` 7절 공통 정의표 (이 폴더 정의를 참조)
- 시설 자료: `../시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet` (facility-v1.2, 패키지 안내 `../시설데이터 구축/시설데이터_패키지/README.md`), 보고서 Claude Docs 「서울 시설 데이터(2020·2025) 구축 및 신뢰성 보고서」
- 경계: `../00_공통_코어엔진/data/` (boundary-v2-dong, boundary-v2-leiden, od-daily-v1)
- 배포목록: `../데이터_배포목록.md` (pop-grid-100m-v1, grid-master-250m-v1, network-walk-v1, ttm-walk-v1, access-engine-v1 모두 확정 2026-09-24)
- 엔진 기록: `04_구축기록/접근성엔진_구축기록.md` (입력 해시, 규칙, 검증값, 한계)
