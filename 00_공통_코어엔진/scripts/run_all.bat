@echo off
REM 00_공통_코어엔진 전체 실행 (Windows). 이 파일이 있는 scripts\ 폴더에서 실행한다.
REM 단계별로 따로 실행하려면 아래 줄을 하나씩 명령창에 입력하면 된다.
REM 예상 시간(4코어 기준): s01 1분 / s02 연도당 5~10분 / s03 연도당 1~2시간 / s04·s05 각 1분
chcp 65001 >nul
cd /d %~dp0

echo [1/5] 동 경계 정본 424 + 공식 생활권 116 + 동-생활권 매핑
python s01_build_dong_boundaries.py || goto :err

echo [2/5] 원자료 CSV -> OD 집계표 (2020, 2025)
python s02_build_od_tables.py --years 2020 2025 || goto :err

echo [3/5] Leiden 합의 구획 (해상도 250개 x 3,000회, 구 25개, 2개 연도)
python s03_leiden_consensus.py --years 2020 2025 --workers 4 || goto :err

echo [4/5] 결과 검사 후 data\ 정본 승격 + manifest.json
python s04_promote_canonical.py --years 2020 2025 || goto :err

echo [5/5] 독립 교차검증 보고서 (output\validation_report_*.md)
python s05_validate.py || goto :err

echo 완료. output\validation_report_*.md 와 data\manifest.json 을 확인한 뒤 데이터_배포목록.md 에 등록한다.
goto :eof

:err
echo 오류로 중단됨 (위 메시지 확인). 고친 뒤 실패한 단계부터 다시 실행한다.
exit /b 1
