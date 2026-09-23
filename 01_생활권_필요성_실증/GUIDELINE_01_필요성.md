# GUIDELINE_01 — 생활권 필요성 실증 [신규 논문]

> **박사논문 위치:** 4.1절 (혹은 별도 신규 논문)  
> **핵심 질문:** "왜 격자나 행정동이 아닌 생활권이 분석 단위여야 하는가?"

---

## 논문 목표

이동 빅데이터 기반으로 4가지 공간 단위(격자 / 행정동 / 생활권 / 구)를 비교하여  
생활권 단위가 **효율성(IFR)과 형평성(Gini)** 균형에서 최적임을 실증한다.

---

## 교수님 지침

- **"심플하게 가요."** — 지표를 과도하게 늘리지 말 것
- 4가지 공간 단위 비교 자체가 기여점 → 너무 많은 분석 방법 추가 금지
- 시각화는 꼭 필요한 그래프만 (scatter plot: IFR vs Gini 1개면 충분)

---

## 분석 내용 (확정)

| 공간 단위 | 비고 |
|-----------|------|
| 격자 (500m) | 서울 전역 균등 분할 |
| 행정동 (423개) | 정본 dissolve 동 사용 |
| 생활권 (116개) | 공식 서울시 생활권 |
| 자치구 (25개) | 기초자치단체 |

비교 지표: **IFR (내부통행비율)** vs **지니계수 (면적 형평성)**

---

## 금지사항

- [ ] 격자 크기 500m 외 다른 해상도 추가 금지 (복잡도 증가)
- [ ] 새로운 지표 추가 금지 (IFR + Gini 두 개로 충분)
- [ ] 공간 단위를 5개 이상으로 늘리지 말 것

---

## 폴더 구조

```
01_생활권_필요성_실증/
├── scripts/
│   └── simulate_spatial_units_equity.py  ← 메인 실행 스크립트
├── output/
│   └── equity_efficiency_comparison.xlsx ← 최종 결과
└── GUIDELINE_01_필요성.md               ← 이 파일
```

---

## 데이터 의존성

```
D:\Research\0_RAW\이동데이터\        (읽기 전용)
  └─▶ common_flow_loader.py 로 09~21시 비통근 필터
       └─▶ simulate_spatial_units_equity.py 에서 공간단위별 IFR/Gini 계산
            └─▶ output/equity_efficiency_comparison.xlsx
```

---

## 현재 상태

- [x] `simulate_spatial_units_equity.py` 실행 성공
- [x] `equity_efficiency_comparison.xlsx` 산출 완료
- [ ] 논문 본문 Figure 작성 (scatter plot IFR vs Gini)
