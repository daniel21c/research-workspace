@echo off
REM 연구4 KPA 전체 실행 (Windows). 코어엔진 배포본이 확정된 뒤에 실행한다.
cd /d %~dp0
python tests\test_examples.py || exit /b 1
python k01_compute.py     || exit /b 1
python k02_select.py      || exit /b 1
python k03_figures.py     || exit /b 1
python k04_manuscript.py  || exit /b 1
python k05_package.py     || exit /b 1
echo 완료. 결과: ..\output\
