# 02. JTG 커뮤니티 구획 검증 (제1연구 / 박사 4.2절)

이 디렉토리는 Journal of Transport Geography (JTG) 게재 논문(2026년 출판)의 **게재본 확정 결과(Golden Copy)**와 방법론 재현 스크립트를 보관합니다.

---

## 1. 논문 개요
* **논문명:** Quantitative evaluation of urban living-zone boundaries using mobility community detection (Journal of Transport Geography, 2026)
* **목적:** 서울시 생활이동 빅데이터(2020년 1월, 비통근·비통학 주간 통행)를 활용하여 네트워크 커뮤니티 구획(Leiden/Louvain)을 도출하고, 서울시 공식 116개 지역생활권 계획과의 정합성(IoU, Modularity, IFR)을 평가.
* **핵심 방법론:**
  * 각 자치구별 목표 커뮤니티 수(116개 타겟)를 만족하는 해상도(Resolution)를 탐색.
  * **3,000회 반복 실행(3,000 runs) 중 가장 빈번하게 등장한 최빈 파티션(Modal Partition)**을 대표 해로 선정하여 확률적 편향(Stochastic bias)을 최소화함.
  * 구획은 무방향 대칭화 네트워크($w_{ij} + w_{ji}$)로 수행하고, IFR 평가는 원래의 방향성 OD($w_{ij}$)를 사용하여 출발지 기준(Origin-based) 내부통행비율을 산출함.

---

## 2. 정본 결과 파일 (`output/`)

* **`custom_community_mapping.csv`**:
  * JTG 게재본에 채택된 2020년 Leiden 116개 커뮤니티 매핑 확정 테이블.
* **`livingzone_community_mapping.csv`**:
  * 서울시 공식 116개 생활권 매핑 테이블.
* **`iou_results.csv`**:
  * 공식 생활권 vs Leiden 커뮤니티 간의 자치구별 교집합/합집합 비율(IoU) 결과표.
  * Jung-gu, Gangbuk-gu, Seocho-gu 등은 IoU=1.0으로 공식 경계와 이동구조가 완벽 일치한 반면, Songpa-gu(0.70), Gangdong-gu(0.72), Gwangjin-gu(0.67) 등은 상당한 불일치를 보임.
* **`Internal_Ratio_community_summary.xlsx` / `Internal_Ratio_livingzone_summary.xlsx`**:
  * 자치구별 Leiden 및 공식 생활권의 IFR(내부통행비율) 산출 결과.
* **`combined_community_map.shp`**:
  * JTG 게재본 Figure 6/7 등에 사용된 서울시 전체 커뮤니티 통합 지도 Shapefile.
* **`leiden_resolution_results.csv`**:
  * 각 자치구별 최적 해상도 파라미터 값 목록.
