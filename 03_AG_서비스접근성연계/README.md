# 03. Applied Geography (AG) 서비스 접근성 연계 (제2연구 / 박사 4.3절)

이 디렉토리는 Applied Geography 투고 및 박사학위논문 제4장 제3절에 해당하는 **공식 생활권 vs 이동기반 커뮤니티의 불일치와 생활서비스 접근성(Coverage, MAI) 간의 연계 실증 모형**을 다룹니다.

---

## 1. 연구 개요 및 지도 원칙
* **연구 질문:** 공식 생활권과 이동기반 커뮤니티 간의 경계 불일치가 실제 시민들의 일상 생활서비스 접근성 및 이동 내부화(IFR)와 어떻게 연계되는가?
* **교수님 지도 핵심 사항 (26.09.21 반영):**
  1. **분석 단순화:** 핵심 지표는 **Coverage**, **MAI**, **IFR** 3가지로 단순하게 유지.
  2. **통제변수 처리:** 면적(Area)과 Compactness는 Control variable로만 취급하고 핵심 메시지로 내세우지 말 것.
  3. **조건부 지표 해석:** MAI가 도달 가능한 대상을 기준으로 계산된 조건부 지표임을 명확히 서술.
  4. **공간모형:** OLS의 공간의존성 왜곡 여부를 확인하는 검증용으로만 활용.

---

## 2. 스크립트 구성 (`scripts/`)

* **`02_simplified_ols_regression.py`**:
  * 2025년 단면 자치구 단위(N=25) 단순 OLS 회귀분석 실행 스크립트.
  * Model 1 (LZ): $\text{LZ\_IFR} \sim \text{LZ\_MAI} + \text{LZ\_Coverage}$
  * Model 2 (LD): $\text{LD\_IFR} \sim \text{LD\_MAI} + \text{LD\_Coverage}$
  * Model 3 (Gap - 핵심): $\Delta\text{IFR} \sim \Delta\text{MAI} + \Delta\text{Coverage}$

---

## 3. 주요 산출물 (`output/`)

* **`ag_simplified_ols_regression_results.xlsx`**:
  * 단순화된 OLS 3개 모델의 회귀계수, 표준오차, t값, p값, $R^2$, 수정 $R^2$ 요약 결과표.
* **`correct_boundary_v4_2025/`**:
  * 6대 시설(상업, 교육, 녹지, 의료, 여가, 공공서비스)별 세부 접근성 및 집계 데이터.
