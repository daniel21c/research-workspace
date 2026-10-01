# 연구3 — 통행을 따르며 시설을 지키다: 서울 생활권계획 경계 동의 통행 기준 재배정과 생활권 안 보행 시설 포착 (AG 확정본)

- 논문 위치: 박사논문 4장 3절 (Applied Geography 투고). 영문 제목: *Following trips, keeping services: Mobility-guided reassignment of boundary dongs in Seoul’s living-zone plan and within-zone walkable service coverage*
- 상태(2026-10-02): 원고 확정. 2026-09-30 교수님 팀즈 보고 → 2026-10-02 데이터 사용 정합 감사(S1 0건·S2 1건·S3 8건) 반영 완료. 팀즈 게시글 수정본과 "9/30 보고판 대비 바뀐 점"은 `보고_20260930/`에 있고 아직 보내지 않았다. 교수님 승인·공저자 확인 뒤 투고.
- **핵심 결과**: 통행 기준 재배정은 자족성을 높이면서 생활권 안 보행 시설 누락의 **총량**을 줄였고(무작위는 예외 없이 늘림), 그 감소는 문화·행정·안전에서 나왔다(나머지 다섯 범주는 늘었지만 무작위보다 덜). 공식 생활권은 대안 지도 거의 전부보다 낫다. 통행–시설 위치 관계는 의료·소매·생활서비스에서 강하지만 감소를 설명하지 않는다.
- **설계**: [연구설계.md](연구설계.md) — 질문과 답, 분석의 틀, 원고 구성·쓰기 규칙, 본문 밖 분석과 한계, 재현 순서, 변경 이력
- **원고**: `manuscript/` — `AG_manuscript_anonymised.docx`(익명 본문, 7,887단어) · `AG_title_page.docx` · `AG_highlights.docx` · `AG_supplementary_appendix.docx`(Table A.1~A.6) · `AG_cover_letter.docx` · 한국어 전문 `AG_한국어_원고.docx` · 그림 `figures/` · 채운 값 `values_used.json` · 단어 수 `word_count.json`. PDF는 `보고_20260930/`와 패키지 zip 안에 있다.
- **공동연구자 패키지**: `package/AG_확정본_공동연구자패키지_20260930.zip` (안내 `package/README_패키지.md`, 새 폴더 자체 점검 `package/package_selfcheck.json`)
- **교수님 보고 세트**: `보고_20260930/` (보고 메모 docx·pdf, 팀즈 게시글 수정본, 9/30 보고판 대비 변경점, 한·영 원고·부록 PDF, 패키지 zip 사본, 그래픽 초록)
- **검수·감사 대응**: [검수의견_대응표_20260930.md](검수의견_대응표_20260930.md) — 1~9절 외부 검수, 10절 문체 개정, 11절 쉬운 어휘·AG 서식, 12절 데이터 사용 정합 감사(반영·미반영 이유)
- **투고 서식**: [AG_투고서식_체크리스트_20260930.md](AG_투고서식_체크리스트_20260930.md) — 공식 Guide for Authors와 AG 게재 논문 10편 대조
- 작업 기록: [작업기록.md](작업기록.md) (맨 위에 현재 상태)
- 코드: `code/` (a01 → a02(연도당 시드 2개) → a03 → a04 → a10 → a05 → a06 → a07 → a08 → a09, 설명은 연구설계 5절), 부록 보조 산출 재생성 `code/appendix/`(README 참고). 결과: `results/{2020,2025,appendix}`, 실행 로그 `results/_logs/`, 검증 `results/claims_check.json`·`_check_a01_vs_previous.json`·`a02_reproduction_check.json`·`appendix/regeneration_check.json`
- 검증: 원고 수치 자동 대조 216/216(저장 결과표에서 값 재계산 + 원고 반영·자리표시 검사, a10 범주·시점 민감도와 a11 OD 비공개 포함), a10은 a01의 전 상태를 재현함을 assert, 앙상블 2000장과 통행·무작위 경로가 이전 독립 실행과 동일, 부록 보조 산출 재생성 대조
- 입력(읽기 전용): `00_공통_코어엔진/data`, `06_접근성분석/접근성분석_패키지/데이터/입력`, `시설데이터 구축/시설데이터_패키지`
- 폴더 구성(2026-10-02 정리 후): 문서 5개(README·연구설계·작업기록·대응표·서식 체크리스트) + `code/`(+`appendix/`) `results/` `manuscript/` `package/` `보고_20260930/`. 최종본이 아닌 것은 모두 `D:\Research\_archive\03_AG_확정전_정리_20260930\`에 있다(삭제 없음, 해시 확인):
  - `final_cleanup_20261002/` — 외부 검수 종결 기록(`검수기록/`), 9/30 구조 변경 대조표, 부록 보조 계산의 옛 원본 코드, 실행 캐시, 이전 보고 zip 사본들
  - `superseded_20260930_문체개정전/` — 문체 개정 전 패키지·PDF·보고 메모
  - `current/`, `explore/`, `review_revision_20260929/`, `english_review_20260929/` 등 — 확정 전 설계·코드·원고

이 폴더 밖의 파일은 수정하지 않는다. 규칙은 [저장소 README](../README.md)를 따른다.
