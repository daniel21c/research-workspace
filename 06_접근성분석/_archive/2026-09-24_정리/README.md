# 2026-09-24 정리 (작업 24)

삭제하지 않고 옮겨 둔 파일. 필요 없으면 사용자가 직접 지운다.

| 옮긴 것 | 원래 위치 | 이유 |
|---|---|---|
| `01_data/grid/_tmp/` | `01_data/grid/_tmp/` | a01 격자 마스터의 중간 체크포인트(약 40 MB). 최종 산출은 `grid100_master.*`·`grid250_master.*`. a01을 다시 돌리면 새로 만든다 |
| `caches/root_.pytest_cache`, `caches/02_scripts/.pytest_cache` | 폴더 루트, `02_scripts/` | pytest 실행 캐시 |
| `caches/02_scripts/__pycache__`, `caches/02_scripts/tests/__pycache__` | `02_scripts/`, `02_scripts/tests/` | 파이썬 바이트코드 캐시 |

남겨 둔 것: `01_data/ttm/*_ku11010.*`(종로구 시험 계산 기록, `a05b_record.py`가 구축기록에 사용), `01_data/ttm/ttm*/_stats/`(a05 재개용), `01_data/facility/facility_2020_2025_units.csv`(parquet를 못 여는 공동연구자용 사본).
| `데이터_배포목록_작업24이전.md` | `../데이터_배포목록.md` 사본 | 작업 24에서 5개 행을 확정으로 고치기 전 상태(원본은 수정됨) |
| `자료가공설계_작업24이전.md` | `00_설계/자료가공설계.md` 사본 | P5 완료 상태로 갱신하기 전 판 |
