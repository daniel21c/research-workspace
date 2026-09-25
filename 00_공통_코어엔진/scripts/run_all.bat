@echo off
REM 00_common_core_engine: boundary pipeline, steps 1-5 (Windows). Run this file from the scripts\ folder.
REM To run one step at a time, type the matching python line below.
REM Time on 4 cores: s01 1 min / s02 5-10 min per year / s03 1-2 h per year / s04, s05 1 min each.
REM This file is ASCII with CRLF line endings on purpose: Korean text or LF endings make cmd misread lines.
chcp 65001 >nul
cd /d %~dp0

echo [1/5] s01 dong boundaries 424 + official living zones 116 + dong-to-zone mapping
python s01_build_dong_boundaries.py || goto :err

echo [2/5] s02 raw CSV to OD tables (2020, 2025)
python s02_build_od_tables.py --years 2020 2025 || goto :err

echo [3/5] s03 Leiden consensus (250 resolutions x 3,000 runs, 25 ku, 2 years)
python s03_leiden_consensus.py --years 2020 2025 --workers 4 || goto :err

echo [4/5] s04 checks, then promote to data\ + manifest.json
python s04_promote_canonical.py --years 2020 2025 || goto :err

echo [5/5] s05 independent cross-check (output\validation_report_*.md)
python s05_validate.py || goto :err

echo Done. Check output\validation_report_*.md and data\manifest.json, then register the hashes in the data release list (data_release_list .md at repo root)
goto :eof

:err
echo Stopped on error (see the message above). Fix it, then rerun from the failed step.
exit /b 1
