# 부록 보조 산출 재생성 코드 (보관 분석)

원고 부록이 인용하는 보조 산출 세 종류를 AG 폴더 안의 코드로 다시 만든다. 원 산출은 2026-09-28~29 탐색 단계(`explore/v3`, Codex `study.py main()` 실행)에서 만들어졌고, 원고는 그 **원 사본**(`results/appendix/`)을 인용한다. 이 폴더의 코드는 그 원 사본이 현재 입력·코드로 다시 나오는지 확인하기 위한 것이며, 본문 결과(표 2~4, 그림 2~4)는 이 코드에 의존하지 않는다. 2026-10-02 데이터 사용 정합 감사 S3-3("원고 수치의 근거를 허브 밖에 두지 않는다")에 따라 허브 밖 보관 폴더에서 이곳으로 옮겨 다시 썼다.

| 코드 | 다시 만드는 원 사본 | 원고 위치 |
|---|---|---|
| `c1_constrained_paths.py {연도}` | `constrained_paths_summary_{연도}.json`, `constrained_paths_moves_{연도}.csv` | Table A.3 1·2행, 4.2절 끝(인구·모양 제약) |
| `c2_plan_level_association.py` | `plan_level_association.json` | Table A.3 3행 |
| `c3_stagnant_gu_search.py {연도} {시드}` | `e13b_{연도}_SIZE20_{시드}_stagnant_search.csv` 4개 | 3.3절 끝 문장, 부록 Chain diagnostics |
| `check_regen.py` | — | 재생성본(`results/_cache/appendix_regen/`)과 원 사본 대조 → `results/appendix/regeneration_check.json` |

옛 코드와 다른 점: 입력 적재는 `study.load`, 생성 규칙의 제약은 `a02_ensemble.py`의 `Cons`·`pp_csv`(옛 `common_v3` 그대로 옮긴 것), e17의 입력은 AG의 `a03_ensemble_plans.csv`·`a02` 표본 라벨(옛 e15·e13과 같은 값). 계산 순서·시드는 옛 코드 그대로다. 옛 원본 코드는 `D:/Research/_archive/03_AG_확정전_정리_20260930/final_cleanup_20261002/results_appendix_archived_code/`.

## 대조 결과 (2026-10-02, `results/appendix/regeneration_check.json`)

| 원 사본 | 결과 |
|---|---|
| `constrained_paths_moves_{2020,2025}.csv` | SHA-256 동일 |
| `constrained_paths_summary_{2020,2025}.json` | 실행 시간(`seconds`) 한 칸만 다르고 나머지 값 전부 동일 |
| `e13b_*_stagnant_search.csv` 4개 | SHA-256 동일 |
| `plan_level_association.json` | 원고가 쓰는 L 행(ρ·95% 구간)은 같은 값. 원고에 쓰지 않는 2020년 COV 행만 소수 6번째 자리에서 다름 — a03 결과 CSV가 COV를 12자리로 반올림해 저장하면서 순위 동점이 생기기 때문 |

실행 순서(입력은 a01~a04와 같음): `python code/appendix/c1_constrained_paths.py 2020` → `… 2025` → `python code/appendix/c2_plan_level_association.py` → `c3_stagnant_gu_search.py 2025 20261101`, `2025 20261102`, `2020 20261201`, `2020 20261202` → `python code/appendix/check_regen.py`.
