# GUIDELINE_02 — JTG 커뮤니티 구획 검증 [게재 논문]

> **게재지:** Journal of Transport Geography (게재 완료)  
> **박사논문 위치:** 4.2절 (기 게재 논문 요약 편입)  
> **핵심 질문:** "이동 빅데이터 기반 커뮤니티 구획이 공식 생활권 경계와 정합하는가?"

---

## 논문 핵심 방법론 (게재본 확정 — 변경 금지)

### 커뮤니티 구획 알고리즘
```
3,000회 Leiden/Louvain 반복
  → 최빈 파티션(Modal Partition) 채택  ← JTG 게재본 방식
```

> ⚠️ **주의:** 현재 AG/KPA 코드는 200회 Co-association Matrix 방식.  
> JTG 폴더는 **게재본 정본** 그대로 보존. 절대 수정 금지.

### 검증 지표
| 지표 | 정의 |
|------|------|
| **IFR** | 내부통행비율 (JTG Eq.2a/2b) |
| **Modularity** | python-louvain, weight='weight' |
| **IoU** | 구별 1:1 매칭, Σintersection/Σunion |

---

## 교수님 지침

- 이 논문은 **이미 게재 완료** → 방법론 수정 없이 박사논문에 편입
- 박사논문 4.2절에서 요약 서술 후 "본 연구에서 개발한 방법론을 이후 4.3~4.4절에 적용" 연결
- 15분 도시 개념과 직접 연결 금지 ("15분 도시는 내 집 기준 15분 → 생활권과 다름")

---

## 폴더 구조

```
02_JTG_커뮤니티구획/
├── scripts/        ← 신규 분석 필요시에만 추가
├── output/         ← JTG 게재본 정본 파일 보존 (10개 파일)
│   ├── combined_community_map_2020.gpkg
│   ├── combined_community_map_2025.gpkg
│   └── (기타 게재본 산출물)
└── GUIDELINE_02_JTG.md  ← 이 파일
```

---

## 금지사항

- [ ] `output/` 폴더 정본 파일 수정·삭제 절대 금지
- [ ] 3,000회 최빈 파티션 방식을 Co-association 방식으로 교체 금지
- [ ] 게재본 수치와 다른 IFR·IoU 값을 논문에 기재 금지

---

## 데이터 의존성

```
D:\Research\0_RAW\이동데이터\2020, 2025
  └─▶ JTG 게재본 스크립트 (1_OUTPUT/999. python package/)
       └─▶ output/*.gpkg  (정본 — 읽기 전용)
```

---

## 현재 상태

- [x] 게재본 정본 output 파일 10개 복사 완료
- [x] README.md 작성 (3,000회 최빈 파티션 방법론 명시)
- [ ] 박사논문 4.2절 본문 서술
