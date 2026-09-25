@echo off
REM k exploration x1-x9 (Windows). Run from this exploration folder.
REM Reads canonical data only; all results go to output\exploration\
REM x5 (SBM, needs graph-tool) was run in the cloud; its results are already in output\exploration\x5\
REM Time on 8 cores: x1,x3 seconds / x2 10-20 min / x4 5-15 min / x6 1 min / x7 1-3 min / x8 10-20 min / x9 seconds
chcp 65001 >nul
cd /d %~dp0

echo [x1] A1 frontier equivalent k + C3 knee
python x1_frontier_knee.py || goto :err
echo [x2] A2 size-corrected IFR (500 random contiguous partitions)
python x2_size_corrected_ifr.py --n 500 || goto :err
echo [x3] B1 Q band + B4 plateau
python x3_q_band_plateau.py || goto :err
echo [x4] B3 null-model Q z-score
python x4_null_model_q.py --workers 8 --nulls 30 --n-iter 20 || goto :err
echo [x6] C1 TTWA self-containment
python x6_ttwa_selfcontainment.py || goto :err
echo [x7] C2 max-p-regions
python x7_maxp_regions.py --workers 8 --restarts 500 || goto :err
echo [x8] D citywide 424-dong Leiden
python x8_citywide_leiden.py --workers 8 --n-iter 100 || goto :err
echo [x9] summary
python x9_summary.py || goto :err
echo Done. Open the summary .md file in output\exploration\
goto :eof

:err
echo Stopped on error. See the message above, fix it, then rerun from the failed step.
exit /b 1
