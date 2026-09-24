# scripts/_legacy_20260922 — 이전 스크립트 보관 (실행하지 않음)

2026-09-21~22 Antigravity 대화(Living Zone Code Review)에서 만든 공통 코어엔진 1판. 2026-09-23 경계 생성 대화가 새 스크립트(`../s01`~`s05`)로 대체하고 여기로 옮겼다.

| 파일 | 역할이었던 것 | 새 판에서의 대응 | 남긴 이유 |
|---|---|---|---|
| `config.py` | 경로 상수 (`D:\Research` 절대경로, 423 파일명) | `../config.py` (상대경로, 424) | 참고 |
| `preprocess_dong_boundaries.py` | 동 423 dissolve, 공식 생활권 매핑 | `../s01_build_dong_boundaries.py` | 개포3동 오류의 원인 위치(`ADM_CD // 10`) |
| `common_flow_loader.py` | 3.7GB pkl 로드·필터 | `../s02_build_od_tables.py` (원자료 CSV → OD 집계표) | 필터 정의 대조 |
| `leiden_community_detection.py` | 251022 스크립트 재구현 (200회, 자기 루프 제외, 미완주) | `../s03_leiden_consensus.py` | 차이 대조 |
| `boundary_metrics_engine.py` | IFR(동·생활권·구)·IoU·Q 계산 라이브러리 | **아직 없음** — 연구2·4의 정의 확정 후 `od_daily`+424 입력으로 다시 작성 | 재작성 시 참고 |
| `run_common_engine.py` | 위 라이브러리로 5종 엑셀 생성 | 아직 없음 | 재작성 시 참고 |

원조 방법 코드(2025-10 실행): `D:\Research\1_OUTPUT\999. python package\DISTRICT_age\251022_Leiden_25_scan_병렬_중복해결.py`
JTG 게재 당시 코드(2024-12): 같은 폴더 `기존CUPUM자료\1-2. leiden_district_local_241221.py`
