@echo off
REM Optimization verification (design: exploration\optimization design .md, section 5 and 8).
REM Canonical folders are read only. Results go to output\proposal\ and output\leiden\{year}_qmax.
REM Time on 8 cores: x11 seconds / s03 P1 about 25 min (both years) / x12 5-10 min / x13 1-3 min.
chcp 65001 >nul
cd /d %~dp0

echo [x11] collect scenario partitions (P0, P0c, P2, P3, P4) and P1 target k
python x11_scenario_partitions.py || goto :err
cd /d %~dp0..\scripts
echo [s03] P1: Leiden with per-ku Q-max k, canonical seed
python s03_leiden_consensus.py --years 2020 2025 --workers 8 --seed canonical --targets ..\output\proposal\k_targets_qmax.csv --tag _qmax || goto :err
cd /d %~dp0
echo [x12] scorecard
python x12_scorecard.py || goto :err
echo [x13] changes, robust proposals, maps
python x13_changes_and_maps.py || goto :err
echo Done. Open output\proposal\scorecard.md, robust_changes.md, changes_2020.md, changes_2025.md, maps\
goto :eof

:err
echo Stopped on error. See the message above, fix it, then rerun. Finished ku of s03 are resumed from _partial.
exit /b 1
