# v3.3 검증 증거 읽기

현재 최종 상태: final_verification.json, cleanup_ledger.json. 수치 검증: verification_summary.json, verification_final.log, execution.json 및 tests 로그. 원천과 비체육 항목 불변 비교: facility_comparison.json, numerical_changes.json, grid_regression.json, unchanged_inputs.json 및 보존된 로그.

이 폴더의 verify.py, prepare.py, run_all.py 등은 당시 실행된 스크립트/작업 사본의 기록이다. 기록 안의 개인 stage 절대경로와 구 v3.2 정본은 현재 재실행 입력으로 제공하지 않는다. 현재 검사는 패키지 코드/a10_verify.py의 --check-only, --metadata-only, --skip-rerun을 사용하며, 전체 재생성은 코드/run_engine.bat facility를 작업 사본에서 실행한다. 구판과의 전행 비교는 이미 실행된 역사 증거이며 삭제 후 다시 관측한 것으로 해석하지 않는다.

이전_v32는 이전 코드·메타·출처·검증 이력이며 활성 수치 정본이 아니다. 이번 개인 stage는 duplicate hash 검사 후 제거했고 로그와 실행 스크립트는 보존했다. 과거 자동정책이 거부한 v3.2 stage/캐시는 삭제/이동 재시도 없이 그대로 두었으며 공유 대상에서 제외한다.
