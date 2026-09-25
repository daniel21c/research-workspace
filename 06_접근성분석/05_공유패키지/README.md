# 06 접근성 엔진 공유 패키지 (교수님·공동연구자용)

- 만든 날: 2026-09-25 · 만든 코드: `2_코드/a09_share_package.py` · 원본 폴더: `00_박사논문_연구체계/06_접근성분석/`
- 내용: 서울 시설 접근성(Coverage·MAI·도달시간) 2020·2025, 경계 조건 5종(없음·동 424·공식 생활권 116·Leiden 116·구 25)의 **지표 정의, 코드, 결과 CSV, 해시**.
- 모든 파일은 원본의 복사본이며 내용을 바꾸지 않았다. 파일마다 SHA-256을 `파일목록_SHA256.csv`에 적었고, 복사 직후 원본과 같은지 확인했다(82개 모두 일치).
- 숫자를 인용할 때는 `3_결과/`의 CSV를 기준으로 한다. 요약 md의 값도 그 CSV에서 코드로 만든 것이다.

## 읽는 순서

1. `1_정의/지표정의_확정.md` — 세 지표의 식, 33종 시설 → 기능 카테고리 8개, 경계 조건, 민감도 목록. 정의는 이 문서만 따른다.
2. `4_기록/접근성엔진_구축기록.md` — 구현 규칙, 입력 해시, 검증(단위시험 11개·독립 구현 대조·불변조건), 한계, 7절 네트워크 고정 민감도.
3. `3_결과/main/summary_main.md` — 본 분석 요약(서울 종합값, 카테고리별 값, 동별 Δ(Leiden − 공식), 2020→2025 변화).
4. `3_결과/summary_sensitivity.md` — 민감도 비교(10분, 3.6 km/h, 250m, 카테고리 4개, 일상소매 제외, 합집합, 국가 최저기준, 네트워크 고정)와 2020→2025 변화의 네트워크 몫 분해.
5. 연구3 표·그림: `3_결과/tables/T5_category_delta_LD_LZ.md`(T5), `3_결과/figures/F3_dong_dCOV_dMAI_2025.png`(F3, 지도 자료 `tables/F3_dong_delta_2025.csv`), 부록 `figures/F3s_dong_delta_by_category_2025.png`.
6. `3_결과/tables/ku_compare_seunghoon.md` — 경계 조건을 끈 구별 COV·MAI와 김승훈 외(2026 국토학회 춘계) 원고 값의 차이·원인 기록(일치를 요구하지 않음).
7. 코드: `2_코드/a00_config.py`(경로·상수) → `a06_engine.py`(계산) → `tests/test_engine.py`(검증) → `a06b_summary.py`·`a07_study3_outputs.py`·`a08_ku_compare.py`(표·그림). 실행 순서는 `run_engine.bat`.
8. `파일목록_SHA256.csv`로 받은 파일이 같은지 확인한다(PowerShell `Get-FileHash <파일> -Algorithm SHA256`, 또는 `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <파일>`).

## 결과 CSV 열 (unit_access_{연도}_{격자}.csv)

`year, grid_m, T_sec, speed_kmh, catset, retail, unit_level(dong424·lz116·ld·ku·seoul), unit_id, b(none·dong424·lz116·ld·ku), cat(8개+종합), pop_total, pop_reach, COV, MAI, PWATT_sec, n_cat_mai` (+ sens_union은 UNI, UNI_allpop). 상위 단위는 모두 격자 값의 분자합/분모합이다. 묶음 B(국가 최저기준)는 `natstd_B/nat_standard_coverage_*.csv`.

## 폴더

| 폴더 | 내용 | 파일 수 |
|---|---|---|
| `1_정의/` | 지표 정의·자료 가공 설계 | 2 |
| `2_코드/` | 전체 코드·배치·단위시험 | 19 |
| `3_결과/` | 실행 세트별 결과 CSV·요약, 연구3 표·그림, 구별 비교 | 54 |
| `4_기록/` | 구축기록, 해시 목록, 비교용 원고 인쇄값 | 7 |

## 들어 있지 않은 것

- 입력 자료(`01_data/`: 100m·250m 격자 마스터, 경계 붙은 시설 33종, OSM 보행망, 격자→격자 소요시간표, 경계 사본; 약 600 MB)와 격자 단위 결과(`grid_access_*.parquet`). 해시는 `4_기록/manifest_sha256.csv`에 있다. 다시 계산하려면 이 입력이 필요하므로 요청하면 따로 전달한다.
- `4_기록/manifest_sha256.csv`는 패키지를 만들기 직전 판이다(이 README와 파일목록 자체의 해시는 원본 폴더 manifest에 추가됨).

## 필수 문구

MAI는 경계 안에서 해당 카테고리 시설에 도달한 인구만을 대상으로 한 조건부·상한 지표이며, 실제 통행사슬을 재현하지 않는다. 도달하지 못한 인구의 값은 0이 아니라 정의되지 않으며, 그 사정은 Coverage가 보여 준다.
