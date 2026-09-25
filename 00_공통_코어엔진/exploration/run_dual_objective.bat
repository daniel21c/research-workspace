@echo off
REM Dual-objective proposal boundary (mobility self-containment + population floor).
REM Design: exploration\ dual objective design .md. Canonical folders are read only; results go to output\proposal\.
REM Step 1 is a small check (2 ku, few restarts) that writes to the same files; step 2 overwrites them with the full run.
REM Time on 8 cores: check 1 min / x14 full 5-15 min / x11 seconds / x12 5-10 min / x13 2-3 min.
chcp 65001 >nul
cd /d %~dp0

echo [check] x14 on 2 ku, 3 restarts
python x14_dual_objective.py --ku 11020 11240 --restarts 3 --steps 2000 || goto :err
echo [x14] full run: P_min 20000 / 30000 / 50000, 40 restarts
python x14_dual_objective.py --restarts 40 --steps 8000 --workers 8 || goto :err
echo [x11] merge P5 partitions
python x11_scenario_partitions.py || goto :err
echo [x12] scorecard
python x12_scorecard.py || goto :err
echo [x13] changes, adoption, proposal gpkg, maps
python x13_changes_and_maps.py || goto :err
echo Done. Open output\proposal\p5_cost_of_balance.md, p5_adoption.md, scorecard.md, maps\
goto :eof

:err
echo Stopped on error. See the message above, fix it, then rerun from the failed step.
exit /b 1
