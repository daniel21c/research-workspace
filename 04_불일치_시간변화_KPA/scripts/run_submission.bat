@echo off
rem 연구4 KPA 확정본 전체 재생성·검증. 원자료 검증 k21은 원자료가 있는 PC에서만 의미가 있다.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
python tests/test_examples.py || exit /b 1
python tests/test_benchmark.py || exit /b 1
python k21_raw_integrity.py
python k01_compute.py || exit /b 1
python k13_benchmark.py || exit /b 1
python k14_reassign.py || exit /b 1
python k25_change_story.py || exit /b 1
python k18_v2_results.py || exit /b 1
python k19_kpa_v2.py || exit /b 1
python tests/test_text_claims.py || exit /b 1
python k08_hwp_pages.py
python k22_hwp_kpa.py both || exit /b 1
python k11_independent_check.py || exit /b 1
python k23_repro_check.py || exit /b 1
python k20_package_v2.py || exit /b 1
echo 완료
