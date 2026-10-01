# 연구3 — 통행을 따라 고쳐도 시설은 남는다: 서울 생활권계획 경계 동의 통행 기준 재배정과 생활권 안 보행 시설 포착 (AG 확정본)

- 논문 위치: 박사논문 4장 3절 (Applied Geography 투고). 영문 제목: *Following trips, keeping services: Mobility-guided reassignment of boundary dongs in Seoul’s living-zone plan and within-zone walkable service coverage*
- 상태(2026-10-02): 원고 확정(커밋 49fe254), 교수님 보고 완료(2026-09-30 팀즈) → 교수님 승인·공저자 확인 뒤 투고.
- **설계**: [연구설계.md](연구설계.md) — 질문과 답, 분석의 틀, 원고 구성·쓰기 규칙, 본문 밖 분석과 한계, 재현 순서, 변경 이력
- **원고**: `manuscript/` — `AG_manuscript_anonymised.docx`(익명 본문, 7,892단어) · `AG_title_page.docx` · `AG_highlights.docx` · `AG_supplementary_appendix.docx` · `AG_cover_letter.docx` · 한국어 전문 `AG_한국어_원고.docx` · 그림 `figures/` · 채운 값 `values_used.json` · 단어 수 `word_count.json`. PDF는 `보고_20260930/`와 패키지 zip 안에 있다.
- **공동연구자 패키지**: `package/AG_확정본_공동연구자패키지_20260930.zip` (안내 `package/README_패키지.md`, 새 폴더 자체 점검 `package/package_selfcheck.json`)
- **교수님 보고 세트**: `보고_20260930/` (보고 메모 docx·pdf, 실제 발송한 Teams 글, 한·영 원고·부록 PDF, 패키지 zip 사본, 그래픽 초록)
- **외부 검수와 개정 대응**: [검수의견_대응표_20260930.md](검수의견_대응표_20260930.md) — 반영한 것과 반영하지 않은 것의 이유(1~9절 외부 검수, 10절 문체 개정, 11절 쉬운 어휘·AG 서식 개정)
- **투고 서식**: [AG_투고서식_체크리스트_20260930.md](AG_투고서식_체크리스트_20260930.md) — 공식 Guide for Authors와 AG 게재 논문 10편 대조
- 작업 기록: [작업기록.md](작업기록.md)
- 코드: `code/` (a01 → a02(연도당 시드 2개) → a03 → a04 → a05 → a06 → a07 → a08 → a09, 설명은 연구설계 5절). 결과: `results/{2020,2025,appendix}`, 실행 로그 `results/_logs/`, 검증 `results/claims_check.json`·`_check_a01_vs_previous.json`·`a02_reproduction_check.json`
- 검증: 원고 수치 자동 대조 136/136(저장 결과표에서 56개 값 재계산 + 원고 반영·자리표시 80개), 앙상블 2000장과 통행·무작위 경로가 이전 독립 실행과 동일
- 입력(읽기 전용): `00_공통_코어엔진/data`, `06_접근성분석/접근성분석_패키지/데이터/입력`, `시설데이터 구축/시설데이터_패키지`
- 폴더 구성(2026-10-02 정리 후): 문서 5개(README·연구설계·작업기록·대응표·서식 체크리스트) + `code/` `results/` `manuscript/` `package/` `보고_20260930/`. 최종본이 아닌 것은 모두 `D:\Research\_archive\03_AG_확정전_정리_20260930\`에 있다(삭제 없음, 해시 확인):
  - `final_cleanup_20261002/` — 외부 검수 종결 기록(`검수기록/`), 9/30 구조 변경 대조표, 부록 보조 계산의 옛 코드, 실행 캐시
  - `superseded_20260930_문체개정전/` — 문체 개정 전 패키지·PDF·보고 메모
  - `current/`, `explore/`, `review_revision_20260929/`, `english_review_20260929/` 등 — 확정 전 설계·코드·원고

이 폴더 밖의 파일은 수정하지 않는다. 규칙은 [저장소 README](../README.md)를 따른다.
