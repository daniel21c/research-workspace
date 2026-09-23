# GUIDELINE_03 — AG 서비스 접근성 연계 [투고 예정]

> **투고 예정지:** Applied Geography (또는 유사 저널)  
> **박사논문 위치:** 4.3절  
> **핵심 질문:** "이동 커뮤니티 경계가 생활 서비스 접근성 불평등을 설명하는가?"

---

## 논문 핵심 주장

커뮤니티 경계(Leiden 구획)와 공식 생활권 경계의 **불일치 갭**이  
서비스 접근성(MAI, Coverage) 격차를 예측하는지 OLS로 검증.

---

## 교수님 지침

- **"이상한 거 자꾸 늘리지 말고 분석 심플하게 가요."**
- OLS 3개 모델로 마무리 (Model 1: LZ, Model 2: LD, Model 3: Gap)
- AI가 제안하는 공간회귀, GWR, 머신러닝 등 추가 분석 절대 금지
- 기술통계 + OLS 결과 테이블로 충분

---

## 확정된 분석 구조

| 모델 | 종속변수 | 독립변수 |
|------|---------|---------|
| Model 1 (LZ) | MAI_LZ | Coverage_LZ + IFR_LZ |
| Model 2 (LD) | MAI_LD | Coverage_LD + IFR_LD |
| Model 3 (Gap)| MAI_Gap| Coverage_Gap + IFR_Gap |

> 현재 실행 결과: M1 R²=0.0864, M2 R²=0.1702, M3 R²=0.0302

---

## 금지사항

- [ ] GWR, 공간회귀 등 고급 공간분석 추가 금지
- [ ] 시설 유형을 세분화하여 모델 수 증가 금지
- [ ] IFR 외에 새로운 경계 지표 추가 금지

---

## 폴더 구조

```
03_AG_서비스접근성연계/
├── scripts/
│   └── 02_simplified_ols_regression.py  ← 메인 실행 스크립트
├── output/
│   ├── ag_simplified_ols_regression_results.xlsx
│   └── correct_boundary_v4_2025/
│       ├── LD_merged_v3.csv
│       └── LZ_merged_v3.csv
└── GUIDELINE_03_AG.md  ← 이 파일
```

---

## 데이터 의존성

```
02_JTG_커뮤니티구획/output/*.gpkg    (정본 커뮤니티 경계)
00_공통_코어엔진/data/               (423동, 116생활권 정본)
  └─▶ boundary_metrics_engine.py     (IFR/IoU 산출)
       └─▶ 02_simplified_ols_regression.py
            └─▶ output/*.xlsx
```

---

## 현재 상태

- [x] `02_simplified_ols_regression.py` 실행 성공
- [x] OLS 결과 xlsx 산출 완료
- [ ] 논문 Tables/Figures 작성 (OLS 계수 테이블)
- [ ] 투고 준비
