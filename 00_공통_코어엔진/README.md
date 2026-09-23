# 00. 공통 데이터 및 모듈 (Common Core Engine)

이 디렉토리는 박사학위논문 및 세부 연구 4편(JTG, AG, KPA, 신규 시뮬레이션)에서 공통으로 참조하는 **정본 공간데이터**, **Leiden 커뮤니티 구획 엔진**, **다위계 평가 엔진(IFR·IoU·Modularity)**을 중앙 집중 관리합니다.

모든 스크립트와 데이터는 [`GUIDELINE_00_공통코어.md`](./GUIDELINE_00_공통코어.md)의 원칙을 엄격히 준수합니다.

---

## 1. 정본 공간 데이터 (`data/`)

* **`seoul_dong_423_dissolved.gpkg`**: 서울시 423개 유니크 행정동 경계 (`epsg5179`, `epsg4326` 레이어 포함, 3개 분할동 통합 완료).
* **`seoul_official_livingzone_116.gpkg`**: 서울시 2030 생활권계획의 116개 공식 지역생활권 경계.
* **`seoul_boundaries_all.gpkg`**: 공식 116개, 레이든 2020 116개, 레이든 2025 116개 경계를 하나로 통합한 GPKG.
* **`dong_to_official_livingzone_mapping_423.xlsx` (및 `.csv`)**: 423개 동 ↔ 공식 116개 생활권 1:1 확정 매핑.
* **`dong_to_leiden_2020_mapping_423.xlsx` (및 `.csv`)**: 423개 동 ↔ 2020 레이든 116개 커뮤니티 1:1 확정 매핑.
* **`dong_to_leiden_2025_mapping_423.xlsx` (및 `.csv`)**: 423개 동 ↔ 2025 레이든 116개 커뮤니티 1:1 확정 매핑.

---

## 2. 표준 스크립트 (`scripts/`)

* **`config.py`**: 전체 연구 체계의 경로(RAW, 정본, 논문별 output) 중앙 집중 관리 모듈.
* **`leiden_community_detection.py`**:
  * Co-association Matrix 기반 합의 클러스터링(Consensus) 엔진.
  * 라벨 스위칭 방어 ($ARI=1.0000$) 및 NumPy 브로드캐스팅 벡터화 적용.
* **`boundary_metrics_engine.py`**:
  * 다위계 IFR (동별·생활권별·구별), IoU (EPSG:5179 면적 기반 1:1 매칭), Modularity Q 산출 함수 통합 라이브러리.
* **`common_flow_loader.py`**:
  * 09~21시 비통근 일상통행 필터링 및 구별/동별 통행 신속 로더.
* **`run_common_engine.py`**:
  * 전체 정본 공간데이터와 1억 6천만 건의 이동 빅데이터를 로드하여 5대 결과 엑셀 보고서를 일괄 생성하는 통합 실행 파이프라인.

---

## 3. 표준 산출물 (`output/`)

* **`comprehensive_boundary_metrics_summary.xlsx`**: 시 전체 및 구별 4대 지표 총괄 요약표.
* **`ifr_gu_level_comparison_2020_2025.xlsx`**: 25개 자치구별 IFR 비교표 (분자합/분모합 정석 집계).
* **`ifr_zone_level_comparison_2020_2025.xlsx`**: 116개 생활권별 IFR 비교표.
* **`ifr_dong_level_within_zone_2020_2025.xlsx`**: 423개 행정동별 미시 생활권내 IFR 및 미스매치 상위 20개 동.
* **`iou_comparison_official_vs_leiden.xlsx`**: 자치구별 및 서울 전체 공간 정합성(IoU) 상세 비교표.
