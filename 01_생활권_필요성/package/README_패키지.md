# 연구1 공동연구자 패키지 (2026-10-02, Cities 확정본) — 받는 분 안내

## 1. 푸는 위치
공유받은 허브 폴더 `00_박사논문_연구체계/`의 **루트에 그대로 푼다.** ZIP 안 경로가 허브 루트 기준이라 파일이 제자리에 들어간다.
- 같은 이름의 연구1 파일은 이 판으로 덮어써진다. 이전 판(설계 4판 검토본 등)은 Git 이력과 작성자 PC의 허브 밖 보관 폴더에 있다.
- 다른 연구 폴더(02~07), 접근성 패키지, 시설 v1.4, 경계 자료는 **들어 있지 않고 바꾸지도 않는다.**
- 허브 문서 사본(`README.md`, `박사논문_연구설계.md`, `데이터_배포목록.md`, `공유_안내.md`)은 작성자 PC의 현재본이다. 받은 분의 허브에 더 새 판이 있으면 그쪽을 둔다.

## 2. 먼저 볼 것
1. `01_생활권_필요성/보고_20261002/Cities_교수님보고_20261002.pdf`: 4쪽 요약(질문, 분석의 틀, 핵심 결과, 원고, 차별점, 검증 상태).
2. `01_생활권_필요성/보고_20261002/Cities_한국어_원고.pdf`: 한국어 전문.
3. `01_생활권_필요성/manuscript/Cities_manuscript_anonymised.docx`: 영문 익명 투고본(PDF는 `보고_20261002/`).
4. `01_생활권_필요성/Cities_투고서식_체크리스트_20261002.md`: Cities 규정 대조.

의견은 `01_생활권_필요성/` 옆에 `공동연구자_검토의견_YYYYMMDD.md`로 남기거나 편한 방식으로 보내 주시면 된다.

## 3. 들어 있는 것
| 경로 | 내용 |
|---|---|
| `01_생활권_필요성/*.md` | README, 연구설계(4판), 작업기록, 검수의견 대응표, 구성변경 대조표, Cities 투고서식 체크리스트 |
| `01_생활권_필요성/manuscript/` | 투고 docx 6개(익명 원고, 제목면, 하이라이트, 진술문, 투고 서한, 한국어 원고), `figures/`(Fig1~6 png·pdf, Figure_1~6 tif, 그래픽 초록), `word_count.json` |
| `01_생활권_필요성/보고_20261002/` | 교수님 보고 메모 docx·pdf, Teams 보고글, 한·영 원고 PDF, 그래픽 초록 |
| `01_생활권_필요성/code/` | 실험 코드 전부(공통 `r1lib.py`, `bundlelib.py`), 원고 원문 `manuscript_src/`(영문·한국어 md, 표), 그림·원고 생성 코드 |
| `01_생활권_필요성/results/` | 결과 표 `표4.1-*`, 결과총람(분석항목 25개), 그림, 입지 JSON, 실행 로그 `_logs/` |
| `01_생활권_필요성/검수기록/` | 외부 검토 원문·검증 파일, 선행연구 대조(`문헌대조/`: 원문대조표, Cities 문헌 A·B·C) |
| `01_생활권_필요성/package/` | 이 안내, `make_package.py`, `package_selfcheck.json` |
| `시설데이터 구축/시설데이터_패키지/부가층_v1.5후보_20261001/` | 공원·공공체육·지역아동센터 부가 층 |
| `패키지_목록.csv` | ZIP 안 모든 파일의 크기·SHA-256 |

넣지 않은 것: 선행연구 PDF(서지·DOI는 `검수기록/문헌대조/`), 가상 통제실험의 세계별 원자료.

## 4. 원고를 다시 만들려면
```
cd 01_생활권_필요성/code
python fig_manuscript.py          # 그림 Fig1~6(600 dpi png + pdf), 표 Table1~4 (입력 자료 필요)
python fig_graphical_abstract.py  # 그래픽 초록 (입력 자료 필요)
python cities_docx.py             # 투고 docx 6개, Figure_1~6.tif, word_count.json (원문 md만으로 실행)
python cities_docx.py memo        # 교수님 보고 메모 docx
powershell -File export_pdf.ps1 -Docx <docx> -Pdf <pdf>   # Word로 PDF 변환
```

## 5. 분석을 다시 돌리려면
입력은 공유 허브에 있다: `06_접근성분석/접근성분석_패키지/데이터/`(격자, 보행 TTM, 시설 v1.4), `00_공통_코어엔진/`(경계, `exploration/xcommon.py`), 부가 층(이 ZIP). 환경: Python 3.12, numpy, pandas, pyarrow, scipy 1.9 이상(`scipy.optimize.milp`), matplotlib, geopandas, python-docx, Pillow.

```
python exp13_bundle_defs.py 2020            # 묶음 정의별 완결 (표4.1-16), 2025도
python exp14_bundle_place.py seoul 2020     # 묶음 배치 (표4.1-18)
python exp16_bundle_milp.py seoul 2025 3600 # 묶음 최대화 정수계획 (표4.1-19)
python exp16_low20.py                       # 정확해의 하위 20%
python exp19_holdout_sens.py                # 민감도 (표4.1-22)
python exp20_bundle_floor.py 2025 공식LZ 0.05 14400   # 권역별 묶음 최저선 (표4.1-23)
python run_exp20.py 5 5400                  # exp20 일괄
```
결과는 `results/`에 덮어쓴다. 앞 단계 실험(표4.1-1~13)의 명령은 `results/_logs/run0930/queues.sh`에 있다.
