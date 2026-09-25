@echo off
REM k sensitivity: rerun the canonical pipeline (s03) with mobility-based k per ku, same seed as canonical.
REM Canonical output\leiden\2020, 2025 are read only. Results go to output\leiden\{year}_kmob_lo, {year}_kmob_hi
REM and the comparison report to output\sensitivity\. Run from this exploration folder.
REM kmob_lo: 4-method median, .5 rounded toward official k  (sum 120 / 125)
REM kmob_hi: 4-method median, .5 rounded away from official k (sum 123 / 133)
REM Time on 8 cores: about 20-30 min per scenario (both years), 40-60 min total.
chcp 65001 >nul
cd /d %~dp0

echo [x10] build target k files
python x10_k_targets.py || goto :err
cd /d %~dp0..\scripts
echo [s03] kmob_lo
python s03_leiden_consensus.py --years 2020 2025 --workers 8 --seed canonical --targets ..\output\exploration\k_targets_kmob_lo.csv --tag _kmob_lo || goto :err
echo [s03] kmob_hi
python s03_leiden_consensus.py --years 2020 2025 --workers 8 --seed canonical --targets ..\output\exploration\k_targets_kmob_hi.csv --tag _kmob_hi || goto :err
echo [s06] compare with canonical
python s06_sensitivity.py --compare _kmob_lo _kmob_hi || goto :err
echo Done. Open the newest sensitivity_compare_*.md in output\sensitivity\
goto :eof

:err
echo Stopped on error. See the message above, fix it, then rerun. Finished ku are resumed from _partial.
exit /b 1
