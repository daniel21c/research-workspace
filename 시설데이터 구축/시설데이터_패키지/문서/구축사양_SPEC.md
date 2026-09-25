# 서울 시설데이터 2020-01 · 2025-01 구축 사양 (v1, 2026-09-24)

## 사용자 결정 (2026-09-24)
- 의원: 지방행정 인허가 이력 역산을 주 원천으로 한다(상가업소 2019.12판은 재작성본).
- 일상소매: 상가업소 기준(편의점·슈퍼 포함)과 인허가 기준(식료품 인허가 + 대규모점포)을 모두 구축한다. 소진공 정보공개청구로 2019.12 원 배포본을 받으면 상가업소 기준을 원본으로 교체해 주분석으로 확정한다.
- 범위: 카탈로그(`D:\Research\00_공통_데이터\facility_clean_2020_2025\facility_catalog_20260923\`)에서 두 시점 확보 가능한 것(S·A·B)을 전부 구축한다. 분석용 카테고리화는 구축 후에 한다.
- 공원: OSM 두 시점(Geofabrik 2020-01-01, 2025-01-01)을 쓰고, 2025는 공식 도시계획시설 폴리곤(2024.11판)과 대조해 누락 정도를 보고한다.
- 격자: 수요와 결합은 SGIS 100m 격자(EPSG:5179, 코드 '다사'+x3자리+y3자리).

## 시점
- T2020: 기준일 2019-12-31(목표 2020-01-01), 허용창 2019-09-01 ~ 2020-05-31
- T2025: 기준일 2024-12-31(목표 2025-01-01), 허용창 2024-09-01 ~ 2025-05-31
- 창 밖 원천을 쓰면 `reference_month_delta`와 사유를 기록한다.

## 등급(행과 유형 모두에 기록)
- A: 기준일 배포본 / C: 연간 공식 명부 / B: 현재 전체 이력으로 역산(인허가일 ≤ D, 종료일(폐업일, 없으면 취소일) 없음 또는 > D. 폐업·취소 상태인데 날짜 없으면 최종수정시점으로 대체하고 `temporal_reason`에 표시. 1900-01-01 등 더미 날짜는 unknown으로 두고 포함하지 않음. 휴업은 시작·종료일이 모두 있을 때만 제외)

## 출력 구조
`시설_2020_2025_v1/<그룹>/<유형>/`
- `raw/`: 원본 파일 + 같은 이름 `.metadata.json`(url, method, params, download UTC, http status, bytes, sha256, 자료 기준일)
- `facilities_<유형>_2020_01.csv/.parquet`, `facilities_<유형>_2025_01.csv/.parquet` (UTF-8-BOM CSV)
- `qa_<유형>.json`: 원천→후보→최종 계수, 좌표 보유율, 공식 집계 대조, 중복, 서울 경계 밖 수
- `build_<유형>.py`: 원본에서 결과를 다시 만드는 코드(Windows에서도 실행 가능하게 상대경로)

## 공통 열
facility_id(원천 고유키 기반, 두 시점에서 같은 시설이면 같은 값), category_group(보건의료/교육보육/문화체육녹지/상업생활편의/복지행정안전/교통), facility_type, facility_subtype, year_snapshot(2020_01|2025_01), name, address, lon, lat(EPSG:4326), x_5179, y_5179, coord_method(source|geocode_kakao_exact|geocode_vworld_exact|unresolved), grade(A|B|C), source_org, source_dataset, source_url, source_file, source_row_id, source_reference_date, reference_month_delta, temporal_reason, inside_seoul, adm_dong_cd(2025 경계 8자리), oa_cd(집계구 2025), grid100_cd, 그리고 규모변수는 `sz_` 접두어(예: sz_beds, sz_area_m2, sz_capacity).
- 좌표가 없는 행도 지우지 말고 coord_method=unresolved로 남긴다.
- 서울 경계·동·집계구는 `시설데이터 구축/SGIS_인구경계_2019_2024/03_행정구역/경계_2025_2Q/`, `02_집계구/경계_2025_2Q/`를 쓴다(EPSG:5179). 서울 = 시도코드 11.

## 지오코딩
- 키: `D:\Research\_secrets\facility_api.env`(세션 경로 `$HOME/mnt/_secrets/facility_api.env`)의 KAKAO_REST_API_KEY, VWORLD_API_KEY. **키 값을 출력·저장·로그하지 않는다.**
- 응답은 `<유형>/raw/geocoding/`에 주소 해시 이름으로 캐시한다(키 제외).
- 도로명+건물번호 또는 지번 번지가 일치한 결과만 채택. 도로·동 중심점 거부.

## 금지
- 다른 폴더(특히 `00_공통_데이터`, `SGIS_인구경계_2019_2024`)를 수정하지 않는다. 파일을 삭제하지 않는다.
- 결과 수치를 손으로 적지 않는다. 문서의 수치는 qa json에서 가져온다.
