@echo off
REM run_engine.bat - P5 access engine (a06) for all runs, summaries (a06b) and unit tests.
REM Run from any folder; paths are relative to this file. Needs Python 3.10+ with numpy, pandas, pyarrow.
REM Usage:  run_engine.bat          (all runs, about 6 minutes; then summaries, tables, figures)
REM         run_engine.bat test     (one district test only: Jongno-gu 11010, 2025, 100 m)
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [run_engine] python not found on PATH.
  exit /b 1
)
if /i "%1"=="test" (
  python a06_engine.py --year 2025 --grid 100 --ku 11010 --tag test_ku11010
  exit /b %errorlevel%
)
python tests\test_engine.py
if errorlevel 1 goto :fail
for %%Y in (2020 2025) do (
  echo [run_engine] year %%Y
  python a06_engine.py --year %%Y --grid 100 --tag main
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --T 600 --tag sens_T600
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --speed 3.6 --tag sens_speed36
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 250 --tag sens_grid250
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --catset A4 --tag sens_A4
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --retail without --tag sens_retail_without
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --union --tag sens_union
  if errorlevel 1 goto :fail
  python a06_engine.py --year %%Y --grid 100 --catset B --tag natstd_B
  if errorlevel 1 goto :fail
)
REM network-fixed sensitivity: 2020 facilities/population on the 2025 walk network
python a05c_ttm_supplement.py --net 2025 --for-year 2020 --grid 100 --check 40
if errorlevel 1 goto :fail
python a06_engine.py --year 2020 --grid 100 --net-year 2025 --tag sens_net2025
if errorlevel 1 goto :fail
python a06b_summary.py
if errorlevel 1 goto :fail
REM study 3 tables/figures (T5, F3) and district comparison table
python a07_study3_outputs.py
if errorlevel 1 goto :fail
python a08_ku_compare.py
if errorlevel 1 goto :fail
echo [run_engine] all done
endlocal
exit /b 0
:fail
echo [run_engine] FAILED (errorlevel %errorlevel%)
endlocal
exit /b 1
