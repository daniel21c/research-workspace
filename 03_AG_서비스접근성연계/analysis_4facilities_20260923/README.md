# 서울 4종 시설·공식 생활권/Leiden 접근성 분석

이 폴더는 원천 시설·인구·경계·OSM 자료를 읽어 **실제 보행망 계산을 새로 수행한 독립 분석 패키지**다. 기존 논문 정본과 기존 접근성 표는 덮어쓰지 않는다. 결과는 시설 스냅샷과 고정 인구·고정 네트워크를 결합한 조건부 시나리오이며, 실제 2020/2025 인구·보행망 변화를 복원한 결과가 아니다.

**연도 해석에 주의:** 표의2020/2025와 CSV의`year`는 제공 파일의 연도 표기다.2020 소매 ZIP은2026-09-23 공식 포털의 현행 다운로드와 byte 수·SHA256이 정확히 같음을 별도 확인했다. 다만2019 표시 보존 ZIP 내부의 대구 ZIP에 서울 CSV가 있고,2022/2024 문자열을 포함한 ID가 다수 존재한다. ID를 개업연도로 단정할 수는 없지만 역사내용의 기준시점은 여전히 의심·미확정이다. **공식 현행파일 동일성 PASS와 역사시점 유효성 미확정**을 구분한다.

- [결과 보고서](ANALYSIS_REPORT.md): 수치·해석·검증·한계.
- [방법 및 변수 정의](METHODS.md): 입력, 모집단, 분모, 그래프, 경계, 지표.
- [분석 코드](run_analysis.py), [시설 원천 감사](facility_audit.py), [명시적 설정](config.py), [검증 코드](test_analysis.py).
- `results/city_metrics.csv`: 도시 가중 결과. `LZ_original`과 `LD`가 주비교이며 `LZ_dong_sensitivity`는 동 재구성 공식경계 민감도.
- `results/zone_metrics.csv`: 구획별 가중 결과. 미배정 출발지는 별도 행에 보존.
- `results/origin_metrics.parquet`: 모든 출발점×연도×시설×경계×10/15분×100/200m 연결상한 결과.
- `results/temporal_changes.csv`: 동일 인구·네트워크의 2025−2020 시나리오 차이.
- `results/common_mapped_city_metrics.csv`: 원점이 LZ·해당연도 LD에 모두 배정되고 연결된 동일 원점 교집합 민감도. 줄어든 분모를 명시하며 도시 전체표를 대신하지 않는다.
- `results/library_2025_paired_by_LZ.csv`:2025 표기 도서관을 원본 LZ별 동일 출발점 집단에서 비교한 LZ/LD 내부 Coverage. LZ와 LD의 구획명을 대응시키지 않는다.
- `results/facility_provenance.csv`, `facility_lineage.parquet`, `facility_counts.csv`: 원천행 대조·시설 분류 및 원본 수.
- `results/boundary_diagnostics.csv`, `denominator_diagnostics.csv`, `network_snap_diagnostics.csv`, `network_inventory.json`: 배정·분모·연결·네트워크 근거.
- `results/input_manifest.json`, `output_manifest.json`, `runtime.json`, `qa_checks.json`: SHA256·환경·자동검증 근거.

CSV 비율 필드(`covered`, `internal_covered`, `nir_*`, `*_available`)는0~1이며 보고서에서100을 곱해%로 표시한다. `coverage_penalty` 및 연도 차이도 원표에서는 비율 차이다. `opportunities`와`internal_opportunities`는 인구가중 시설개수, `population`과`*_eligible_population`은 명, `*_conditional_mean_minutes`는 해당 유한경로 인구에서의 조건부 분이다. 출발점 원표의`nearest_m`/`internal_nearest_m`은 m이며 경로 미확인은 무한대로 보존한다. `facility_lineage.parquet`의`analysis_included`가 공공학교 필터를 적용한 최종 포함 여부다.

PowerShell 재현 명령(기존 설치환경, 추가 설치 불필요):

```powershell
Set-Location 'D:\Research\00_박사논문_연구체계\03_AG_서비스접근성연계\analysis_4facilities_20260923'
& 'C:\Users\cyion\AppData\Local\Programs\Python\Python312\python.exe' -B run_analysis.py
```

이 명령은11개 단위검증부터 원천감사·망검증·경로계산·보고서·manifest까지 실행한다. 경로계산 없이 단위검증만 하려면 같은 폴더에서 `& 'C:\Users\cyion\AppData\Local\Programs\Python\Python312\python.exe' -B -m unittest -v test_analysis`를 실행한다.

시설 원천 감사만 수행하려면 마지막 명령에 `--audit-only`를 붙인다. 원본 builder, 지오코딩, API, OSRM 서버, 서비스, Docker를 실행하지 않는다. 출력은 이 폴더의 `results`에만 쓴다. 재실행은 이 패키지의 이전 결과를 갱신하므로 보관본이 필요하면 **새 패키지 복사본에서** 실행한다. 경로 변경은 `config.py`에서 명시한다. 재현 실행의 경로계산 상한은60분이며 이를 초과하면 부분결과를 저장하고 예외로 중단한다. 부분결과를 완료 결과로 사용하지 않는다. 최초 실행은30분 상한으로 시작했으며 실행 중 상수를 바꾸어 시간을 연장한 것이 아니다.

공공학교는 원천 학교명부의 **국립·공립만** 분석한다(2020 960개, 2025 963개). 원본 `SCHOOL_BASIC` 1,308/1,310개를 전부 공공학교라고 부르지 않는다. 기존 시설 ID는 원자료 추적용이며, 학교·도서관의 연도별 순번 ID로 생존율을 계산하지 않는다.

소스코드·설명과 대용량 로컬 산출물을 분리했다. 원천 데이터와 행별 로컬 결과의 외부 전송 권한을 이 패키지 생성만으로 확대하지 않는다. 입력 파일이 없는 다른 컴퓨터에서는 경로만으로 재현되지 않으며 manifest와 일치하는 로컬 입력이 필요하다.
