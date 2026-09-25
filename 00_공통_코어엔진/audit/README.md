# audit — 경계 생성 전수 검증 (2026-09-25)

s01~s06 과 **다른 코드**로 원자료부터 정본까지 다시 계산해 대조한다. 정본(`data/`, `output/leiden/`)은 읽기만 한다.
결과는 `output/audit_20260925/`, 요약과 판정은 `../결정기록.md` §17.

| 파일 | 무엇을 | 시간(PC) |
|---|---|---|
| `a1_raw_recount.py {연도}` | 원자료 CSV 24개를 pyarrow 로 모두 문자열로 읽어 서울 내부 OD 를 다시 집계. `*`·그 밖의 비숫자·음수·코드 자릿수·파일별 도착시간 점검 | 연도당 약 4분 |
| `a4_compare_od.py` | a1 결과 ↔ s02 의 `od_full`·`od_daily`·`od_summary` 칸 단위 대조, `od_daily` 는 필터(도착 9~20시, HW·WH 제외)를 따로 적용해 파생 | 1분 |
| `a2_boundaries.py` | 원 SHP 를 따로 dissolve → 424동·코드표 일치, 정본 gpkg 기하 차이, 공식 생활권(EPSG:5174) 좌표 변환 점검, 교차면적 최대 배정 재계산, 통합 gpkg 레이어 | 1~2분 |
| `a5_compare_gpkg.py 기준 비교` | GeoPackage 두 개의 레이어·속성·기하 비교. gpkg 는 파일 안에 작성 시각을 저장해 해시로는 재현 여부를 볼 수 없다. `s04 --out-dir` 로 다시 만든 통합 gpkg 를 정본과 대조할 때 | 1분 |
| `a3_leiden.py [태그]` | 구마다: 저장 시드로 확정 해상도 3,000회 재실행 → 원시 라벨 일치, co-association·τ 연결요소 재계산, Q(networkx)·IFR(자체), 선정 규칙, 격자 250개, 시드 구간, 안정성, 공간 연속성, 매핑 사본 일치. 태그 실행(`_tau0.4` 등)은 run_info 의 τ·선정 규칙으로 검사 | 태그당 1~2분 |

```powershell
cd D:\Research\00_박사논문_연구체계\00_공통_코어엔진\audit
python a1_raw_recount.py 2020; python a1_raw_recount.py 2025; python a4_compare_od.py
python a2_boundaries.py
python a3_leiden.py; foreach ($t in "_tau0.4","_tau0.6","_ifr","_kmob_lo","_kmob_hi","_qmax") { python a3_leiden.py $t }
```

- a3 의 재실행 부분만 s03 의 `consensus_once` 를 쓴다(같은 시드로 같은 결과가 나오는지 보는 것이 목적). 나머지 계산은 모두 자체 코드다.
- a1 의 재집계 parquet(약 257MB)는 `output/audit_20260925/recount/`에 다시 만들어진다. 파일별 점검 통계(json)는 그 폴더에 남겨 두었다.
