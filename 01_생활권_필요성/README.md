# 연구1 — 격자는 사람을 채우지만 지역을 채우지 못한다: 서울 보행 생활서비스로 본 생활권의 필요성 실증 (Cities 확정본)

- 논문 위치: 박사논문 4장 1절 (Cities 투고). 영문 제목: *Grids fill people, not places: Testing the necessity of living zones for walkable public services in Seoul*. 질문: "접근성은 격자로 재고 시설도 격자에 놓으면 되는데 왜 생활권인가"(9/21 논문지도). 시작 프롬프트: [_prompts/01_생활권_필요성.md](../_prompts/01_생활권_필요성.md), 기준 문서: [박사논문_연구설계.md](../박사논문_연구설계.md)
- **확정 설계**: [연구설계.md](연구설계.md) (2026-10-02 4판; 주제 "생활권의 필요성 실증" 고정)
- **답(한 줄)**: 격자로는 사람을 채울 수 있지만 지역을 채울 수는 없다. 격자 묶음 최대화·취약 우선 배치 모두 0명 생활권을 14~21개 남기고, 생활권 최저선만 그런 생활권을 없애거나 크게 줄인다(시설 7종 중 6종 0개; 6분야 묶음 0명 생활권 14 → 2; 비용 약 2%p). 자치구 최저선은 거의 바꾸지 못하고 행정동 최저선은 늘어난 시설로 채울 수 없다. 공식 생활권 경계는 같은 수의 무작위 구획보다 걸어서 쓰는 시설을 덜 자른다(p ≤ 0.04).
- **원고**: `manuscript/Cities_manuscript_anonymised.docx`(익명 본문) · `Cities_title_page.docx` · `Cities_highlights.docx` · `Cities_declarations.docx` · `Cities_cover_letter.docx` · 한국어 전문 `Cities_한국어_원고.docx` · 그림 `manuscript/figures/`(Fig1~6 png·pdf, Figure_1~6 tif, 그래픽 초록) · 분량 `manuscript/word_count.json`. 원문은 `code/manuscript_src/`(영문·한국어 md, 표, 보고 메모), 생성은 `code/cities_docx.py`.
- **공동연구자 패키지**: `package/01_생활권_필요성_Cities확정본_공동연구자패키지_20261002.zip` (안내 `package/README_패키지.md`, 새 폴더에 풀어 실행한 자체 점검 `package/package_selfcheck.json`). 재생성: 허브 루트에서 `python 01_생활권_필요성/package/make_package.py`.
- **외부 검수 대응**: [검수의견_대응표_20261002.md](검수의견_대응표_20261002.md). 검토 원문·검증 파일·선행연구 대조(`문헌대조/`: 원문대조표, Cities 문헌 A·B·C)는 `검수기록/`.
- **최종 보고**: `보고_20261002/` (교수님 보고 메모 docx·pdf, Teams 보고글, 한·영 원고 PDF, 패키지 zip 사본, 그래픽 초록 — 팀즈 첨부는 여기서). 서식 대조: [Cities_투고서식_체크리스트_20261002.md](Cities_투고서식_체크리스트_20261002.md), 구성 대조: [구성변경_대조표_20261002.md](구성변경_대조표_20261002.md)
- 코드: `code/` — 공통 `r1lib.py`·`bundlelib.py`; 묶음 실험 exp13 → exp14 → exp16(`exp16_low20.py`) → exp17 → exp18 → exp19 → exp20(`run_exp20.py`); 앞 단계 exp1~10. 원고 그림 `fig_manuscript.py`, 그래픽 초록 `fig_graphical_abstract.py`, 원고·보고 docx `cities_docx.py`, PDF `export_pdf.ps1`. 실행 명령은 `package/README_패키지.md`.
- 결과: `results/` — 결과총람 `결과총람_20261002.md`(분석항목 25개), 표 `표4.1-*`, 그림, 배치·정수계획 입지 JSON, 실행 로그 `_logs/run0930/`·`_logs/run1002/`. Git 제외.
- 폴더 구성(2026-10-02 정리 후, AG와 같음): 문서 6개(README·연구설계·작업기록·대응표·대조표·체크리스트) + `code/` `results/` `manuscript/` `package/` `검수기록/` `보고_20261002/`. 그 밖의 옛 판·중간 산출은 허브 밖 `D:\Research\_archive\연구1_*`(이번 정리분은 `연구1_archive_docs_20261002\정리_Cities확정_20261002\`, 이동 후 목록·해시 `inventory_after_move.json`).
- 입력(읽기 전용): `06_접근성분석/접근성분석_패키지/데이터/`(격자·보행 TTM·시설 v1.4), `00_공통_코어엔진/`(경계·OD·`exploration/xcommon.py`), `시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001/`(공원·공공체육·지역아동센터). 엔진·다른 연구는 바꾸지 않는다.
- 검증: 격자 정수계획 4건 갭 0, 저장 입지 독립 재평가 일치; 정확 탐욕 검정 196개 일치(`검수기록/verification_2차.json`); 원고 수치는 결과 표와 대조(작업기록 13차); 참고문헌 85편 Crossref·URL 확인; 패키지 자체 점검(`package/package_selfcheck.json`).
- `manuscript/`에는 최종본만 둔다: 투고 docx 6개, `figures/`, `word_count.json`. PDF는 `보고_20261002/`와 패키지 zip 안에만 있다.

이 폴더 밖의 파일은 수정하지 않는다. 규칙은 [저장소 README](../README.md)를 따른다.
