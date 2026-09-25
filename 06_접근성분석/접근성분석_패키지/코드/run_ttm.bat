@echo off
REM run_ttm.bat - build walking networks (a04) and grid-to-grid walking travel-time matrices (a05)
REM for Seoul, years 2020 and 2025, grids 100 m and 250 m. Run from any folder; paths are relative to this file.
REM Usage:  run_ttm.bat [WORKERS]      (default WORKERS = number of logical CPUs minus 1, at least 1)
REM Requirements: Python 3.10+ with packages in requirements.txt  (pip install -r requirements.txt)
REM   a04 needs the pyosmium package ("osmium") and downloads the Geofabrik pbf (~112 MB / ~234 MB)
REM   into %TEMP%\osm_pbf unless OSM_PBF_DIR points to a folder that already holds the files.
REM Outputs go to the package input-data folder (a00_config.DATA) ; a05 resumes from existing chunk files.
setlocal
cd /d "%~dp0"

set WORKERS=%1
if "%WORKERS%"=="" (
  set /a WORKERS=%NUMBER_OF_PROCESSORS%-1
)
if %WORKERS% LSS 1 set WORKERS=1
echo [run_ttm] workers = %WORKERS%

where python >nul 2>nul
if errorlevel 1 (
  echo [run_ttm] python not found on PATH. Install Python 3.10+ and run: pip install -r requirements.txt
  exit /b 1
)

REM ---- P3 walking networks (skipped when the summary json already exists)
for %%Y in (2020 2025) do (
  python -c "import sys, a00_config as C; sys.exit(0 if (C.DATA / 'network' / 'walk_%%Y_summary.json').exists() else 1)"
  if errorlevel 1 (
    echo [run_ttm] building network %%Y
    python a04_network.py --year %%Y
    if errorlevel 1 goto :fail
  ) else (
    echo [run_ttm] network %%Y exists, skipping
  )
)

REM ---- P4 travel-time matrices: years x grids, all Seoul origins (pop>0 or biz>0)
for %%Y in (2020 2025) do (
  for %%G in (100 250) do (
    echo [run_ttm] ttm year %%Y grid %%G
    python a05_ttm.py --year %%Y --grid %%G --workers %WORKERS% --validate 300
    if errorlevel 1 goto :fail
  )
)

REM ---- write the build record from the summary json files
python a05b_record.py

echo [run_ttm] all done
endlocal
exit /b 0

:fail
echo [run_ttm] FAILED (errorlevel %errorlevel%). Re-run this file to resume; finished chunks are kept.
endlocal
exit /b 1
