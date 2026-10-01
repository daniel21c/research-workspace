from pathlib import Path
import json,shutil,os,sys,datetime
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';R=Path('D:/Research/00_박사논문_연구체계');O=R/'06_접근성분석/접근성분석_패키지';Z=Q/'문서/검증_v33_20260929'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P
def write(p,s):p.write_text(s,encoding='utf8')
def read(p):return json.loads(p.read_text(encoding='utf8'))
v=read(Z/'verification_summary.json');ex=read(S/'execution.json');assert v['counts']['FAIL']==0
for p in S.iterdir():
 if p.is_file() and p.suffix in ['.py','.json','.log','.txt']:shutil.copy2(p,Z/p.name)
# Preserve historical evidence, update only active definition before its change-history section.
p=Q/'문서/지표정의_확정.md';s=p.read_text(encoding='utf8');body,hist=s.split('## 6. 변경 이력',1)
body=body.replace('K = 8','K = 7').replace('카테고리 8개','카테고리 7개').replace('시설 28종','시설 27종').replace('33종 시설','32종 시설').replace('본 계산 (28종)','본 계산 (27종)').replace('8개 평균','7개 평균').replace('차(8개 모두','차(7개 모두').replace('마을단위 5개','마을단위 4개').replace('A의 부분집합 11종','A의 부분집합 6종').replace('카테고리 5개','카테고리 4개')
body='\n'.join(l for l in body.split('\n') if not l.startswith('| 체육 |'))
body=body.replace('| 카테고리 | 8개 | 4개: 교육+보육·복지 / 의료 / 체육+문화 / 소매+생활서비스+행정·안전 |','| 카테고리 | 7개 | 4개: 교육+보육·복지 / 의료 / 문화 / 소매+생활서비스+행정·안전 |')
body=body.replace('(2025 동 14개, 2020 동 24개)','(두 경계의 유효 범주가 서로 다른 경우; 현행 동 수는 재생성 표 참조)')
body=body.replace('(인허가 이중 등록 등; 2020 1,343행·2025 1,574행 제외, 대부분 음식점·식료품·일상소매·체육시설업)','(인허가 이중 등록 등; 현행 제외 수는 실행 메타의 supply_dedup 참조)')
body=body.replace('(연도별 40행)','(현행 연도별 수는 실행 메타 참조)')
lines=body.splitlines()
for i,l in enumerate(lines):
 if l.startswith('- **시점 간 변화'):
  lines[i]='- **시점 간 변화(2020→2025)를 주장할 때는 망 고정 sens_net2025와 스냅거리 sens_snap을 함께 보고한다.** 이번 7범주판의 수치·순위상관은 재생성 `데이터/결과/summary_sensitivity.md`를 따른다. OSM 수록 변화와 실제 망 변화는 분리되지 않는다. A4·B의 snap 결합은 미실행이다.'
body='\n'.join(lines)
intro='> 현행 access-engine-v3.3 / facility-v1.4, 2026-09-29: 체육시설업을 두 시점 모두 제외한다. A 7범주/27종 + 통제5종, A4의 문화는 문화만, B 4기능/6시설유형, 2SFCA 34항목. 제외 이유는 현재상태 필터의 과거 후보 선택 문제이며 결과 유불리에 따른 선택이 아니다. 별도 공공체육 자료는 대체 투입하지 않았다. 이전 8범주 정의·코드·메타는 검증_v33_20260929/이전_v32에 보존한다.\n\n'
write(p,body.split('\n',1)[0]+'\n\n'+intro+body.split('\n',1)[1]+'\n\n## 6. 변경 이력'+hist+'\n- 2026-09-29 v3.3: 사용자·시설 생산자 v1.4 결정에 따라 체육시설업 21,300행 제외, 7범주/27종·B4·2SFCA34로 재계산. 산식은 유지하고 범주 집합 및 종합 분모를 변경. 상세 검증_v33_20260929.\n')
src=Q/'문서/출처_전처리_연결표_20260929.md';s=src.read_text(encoding='utf8');s=s.replace('v3.2 / facility-v1.3','v3.3 / facility-v1.4').replace('서울 33종 시설, facility-v1.3','서울 32종 시설, facility-v1.4').replace('1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47, 606,066행/25열','c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb, 584,766행/25열')
lines=s.splitlines()
for i,l in enumerate(lines):
 if l.startswith('- **입력 구성 문제'):
  lines[i]='- 체육시설업의 현재상태 필터 문제는 facility-v1.4에서 두 시점 해당 유형 전체를 제외하는 선택으로 처리했다. 현행 7범주 결과에는 해당 유형이 없으므로 구8범주 결과의 체육 관련 HOLD를 적용하지 않는다. 이 제외가 나머지 자료의 정확한 과거 운영을 증명하지는 않는다. 소매 원배포본 요청 중/미입수, 공공시설의 인접 기준일 대리 및 의료 종료일 근사 조건은 유지한다.'
s='\n'.join(lines).replace('## v1.3 좌표 보정 연결 (이번 갱신)','## v1.3 좌표 보정 연결 (유지한 전처리 이력)')
s+='''

## v1.4 시설 선택 → v3.3 접근성 (현행)

시설 `구축코드/시설_선택규칙.json` → `구축코드/14_체육제외/README.md`, `release_v14.py`, `stage_verification.json`, `promotion_manifest.json`, `final_verification.json` → 현행 분석용 파일 → a02의 선택규칙 SHA 및 원천 SHA → a06의 매실행 `provenance.upstream_inputs`와 `analysis_scope`로 연결한다. 2020 10,293행/2025 11,007행, 총21,300행의 시설값 `체육시설업`만 제외했다. 584,766행(2020 285,339/2025 299,427), 분석가능581,888행, 32유형=27분석+5통제다. 이번 직접 전행 비교에서 남은 행의 값·순서·자료형·좌표는 v1.3와 정확히 같았다. 접근성상 변화는 기능 구성 변경이며 좌표 갱신 효과가 아니다.

현재 파일은 원자료130개를 수정하지 않은 생산자의 선택 결과다. 별도 공공체육 핵심종목 자료는 주분석에 투입하지 않았다. 체육을 0 또는 결측 범주로 남기지 않고 A/B/2SFCA 항목 집합에서 제거했다. 공공시설의 근접 기준일 자료 사용은 연구가정이며 몇 개월간 운영불변을 입증한 사실로 기술하지 않는다. 소매 원본은 요청 중/미입수로 기록하고, 일상소매 제외 민감도는 인허가 식료품·대규모점포를 그대로 남긴다.

기계 판독 source_evidence에는 실제 읽은 기록의 경로·해시를 남긴다. 과거 v3.2 출처표/메타는 검증_v33_20260929/이전_v32에 보존한다. 구시설5파일 정리는 producer verify의 역사비교 의존성을 분리한 뒤에만 가능하며 처리 상태는 cleanup_ledger.json을 따른다.
''';write(src,s+'\n')
guide='''# 공동연구자 시작 — 접근성 v3.3 / 시설 v1.4

**계산 검증 PASS. 출처의 시점 대리·소매 원본 미확보 조건을 명시하고 연구에 사용한다.** 체육시설업은 두 연도 전체 제외했으므로 이 유형의 과거 현재상태 필터 문제에 따른 구8범주판 HOLD는 현행7범주판에 적용하지 않는다. 공공시설의 운영불변을 검증했다는 뜻은 아니다.

## 무엇을 읽는가

- 본 결과: `데이터/결과/main/unit_access_2020_100.csv`, `unit_access_2025_100.csv`. A 7범주/27분석유형이며 종합 COV 분모는7, MAI 범위1~7이다.
- 2SFCA: 같은 폴더 `sfca_unit_*`, 공급34항목(7범주+27유형), 단위는 인구1만명당 시설수, 종합값 없음. 정원·면적·서비스 용량이 아니다.
- 국가기준 보조: `natstd_B/nat_standard_coverage_*`, 교육·돌봄·의료·편의 4기능/6유형만. 체육 충족률은 이 패키지의 적용 범위 밖이다.
- `summary_sensitivity.md`, `데이터/결과/tables/T5_category_delta_LD_LZ.csv`, `데이터/결과/figures/F3*`는 이번 결과에서 재생성됐다. A4는 교육·복지/의료/문화/소매·서비스·행정이며 MAI상한4다.
- `temporal_common4`는 기본 두경계 공통범주 차분과 별도인 시점 민감도다. moving_ld_moving_net, moving_ld_net2025, fixed_ld2020_net2025, fixed_ld2025_net2025, moving_ld_snap 다섯 설정의 실제 입력은 verification.json을 따른다.

## 해석·분모·경계

COV는 전체인구 분모, MAI/PWATT는 해당 범주 도달인구 분모다. 미도달 MAI를0으로 바꾸지 않는다. ΔMAI는 두 경계에서 모두 유효한 범주별 차의 평균이며 종합 MAI를 바로 빼지 않는다(`a06c_delta.py`). 시점 변화의 공통4는 두 시점×두 경계 모두 유효한 동일 범주 교집합이다.

경계 제한은 출발·도착 격자 중심의 소속을 비교한다. 경로 전체가 그 경계 안에 갇히는 계산은 아니다. 본 분석은4km/h·15분, 100m격자; 10분은 약667m이며800m와 같지 않다. 서울 밖 목적지는 없고 OSM 수록 변화는 실제 망 변화와 분리되지 않는다. 망고정·스냅거리 민감도를 함께 읽는다.

## 출처·재현·공유

[출처와 전처리 연결표](출처_전처리_연결표_20260929.md), [정의](지표정의_확정.md), [이번 배포 검증](배포검증_v33_20260929.md)을 먼저 읽는다. 원자료는 새로 복제하지 않고 저장소 내부 경로·버전·해시로 연결한다. facility-v1.4 SHA는 `c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb`. 보존된130원천·선택규칙·실제 기준일은 시설 생산 기록에 있다. 실행 환경·코드/입력/출력 SHA는 매실행 run_meta와 release_provenance.json에 있다.

패키지는 입력격자·망·TTM을 포함한다. 저장소 내부 원천 시설/선택규칙과 코어 경계도 상대 위치로 제공해야 전체 재실행된다. 메타 확인과 hash 확인만은 `python 코드/a10_verify.py --metadata-only`, `python 코드/a10_verify.py --check-only`. 재계산은 `a02_facility_boundary.py` → `run_engine.bat` → `a06d_temporal_sensitivity.py` → `a06b_summary.py` → `a07_study3_outputs.py` → `a08_ku_compare.py`; 이번 정확한22명령은 `검증_v33_20260929/execution.json`, 검증은 같은 폴더 verify.py를 참조한다. 외부 scratch에서 재현할 때만 ACCESS_REPOSITORY_ROOT를 연구저장소 루트로 지정한다. 코드/입력이 달라지면 metadata-only가 stale을 검출한다.

공유 권장 범위는 이 `접근성분석_패키지`와 필요한 원천 기록이다. 상위 `_release_stage_v32_20260929_01` 및 캐시는 공유에서 제외한다(이전 정책 차단 이력으로 보존 중). 키·secrets·다운로드 캐시·원자료 권한은 포함하지 않는다. 기존8범주 연구 입력/원고/ZIP과 새7범주 값을 섞지 않는다. 후속 연구 담당자가 새 입력으로 재검토해야 하며 이번에는 타 연구를 수정하지 않았다.
''';write(Q/'문서/공동연구자_시작_20260929.md',guide)
write(Q/'README.md',f'''# 접근성분석 공유 정본

현행 **{P.RELEASE}**, 시설 **facility-v1.4**. 체육시설업 제외: A7범주/27종+통제5종, B4기능, 2SFCA34항목. 원 자료·출처·전처리·검증이력은 보존했다.

[공동연구자 시작](문서/공동연구자_시작_20260929.md) · [지표 정의](문서/지표정의_확정.md) · [출처·전처리](문서/출처_전처리_연결표_20260929.md) · [현재 검증](문서/배포검증_v33_20260929.md)

22개 설정과 표·그림 재생성, 35시험 통과. 계산 검증과 출처 시점 적합성을 구분한다. 현재7범주판은 기록된 시점 대리·소매 불확실성 아래 조건부 사용 가능하다. 체육 포함8범주 역사판의 HOLD를 현재판에 적용하지 않는다. 이전 판은 문서 내 검증 이력이며 현행 수치로 혼용하지 않는다.

무계산 검증: `python 코드/a10_verify.py --check-only` 및 `--metadata-only`. 전체 명령·환경·입력 해시: `문서/검증_v33_20260929/execution.json`, `데이터/release_provenance.json`. 기본결과는 `데이터/결과/main`, 민감도·교차연도LD는 같은 결과폴더의 각 tag이다. 기본15분=4km/h, 10분≈667m. COV전체인구, MAI/PWATT도달인구, 2SFCA시설수/1만명이다.
''')
table='| 연도 | 범위 | 지표 | 변경 동 | 변경 행 | 최대 절대차 |\n|---|---|---|---:|---:|---:|\n'+''.join(f"|{x['year']}|{x['scope']}|{x['metric']}|{x['changed_dongs']}|{x['changed_rows']}|{x['max_abs']:.6f}|\n" for x in v['main'])
write(Q/'문서/배포검증_v33_20260929.md',f'''# 체육시설업 제외 재계산·검증 — v3.3 (2026-09-29)

**계산 PASS / 출처의 연구가정 아래 조건부 사용.** facility-v1.4는 체육시설업21,300행만 제외했다. 남은584,766행/25열(분석가능581,888),32유형의 값·좌표는 v1.3와 정확히 같다. 2020제외10,293/2025제외11,007. 원천 선택의 역사비교 문제를 두 시점 동일 유형 제외로 처리했으며 결과 유불리에 따른 선택이 아니다. 별도 공공체육 자료는 넣지 않았다.

## 검증 범위

- a02 재생성, 22/22 엔진 성공. main·B·A4·10분·3.6km/h·250m·일상소매 제외·union·snap·망고정·xb 포함. main2SFCA 격자도 재생성. 22메타의 현재 source+selection rule/code/output SHA와 필수 불변조건 통과.
- 엔진17+배포14+기하4=**35/35** 시험. 7분모, B4기능, 체육범주 제거가 reach/time을 보존하면서 MAI를 바꾸는 손계산을 추가했다.
- 생존 2SFCA **{v['sfca_unchanged_rows']:,} 집계행**, 비체육 개별 COV/PWATT와 B **{v['category_B_invariant_rows']:,}행** 불변. A4의 문화 묶음은 예전 체육·문화와 내용이 달라 이 불변기대에서 제외했다. 인구분모 {v['population_unchanged_rows']:,}행 불변.
- main 격자와 B **{v['grid_compared_rows']:,}행**의 비교 대상 도달·시간·생존2SFCA 정확히 일치. MAI상한7 및 종합COV7분모(A4는4) 확인. xb3실행 기존경계값은 대응main/망고정과 동일.
- 독립 pandas 2SFCA: 두 연도 × 공공도서관·어린이집·주민센터·문화·의료 × 경계없음/공식생활권. 정확한 비교 셀 수·최대상대오차는 verification.log의 실제 출력 및 검증보고서 참조. 모든 설정의 전체격자를 별도 구현했다는 뜻은 아니다.
- 격자/경계/망/TTM/스냅 **1,033 입력 SHA 불변**. TTM도착격자는 시설 여부와 무관하므로 재사용했다.
- 공통4 다섯 설정, a06b요약, a07연구3표/그림, a08구비교, 데이터/검증결과.json 및 검증보고서를 현행 결과에서 재생성했다.

실행 {sum(x['seconds'] for x in ex if x['name'].startswith('engine_')):.1f}초(엔진합계). 최초 실행 중 엔진 표시버전 상수의 잔존을 발견해 중단하고 수정한 뒤22개를 모두 새 코드로 완료했다. 중단 전 기록은 execution_pre_version_fix.json, 최신 성공은 execution.json이며 이전 생성증거를 덧칠하지 않았다. 비교 기준은 CSV 소수6자리, 격자 저장정밀도; 독립 검증 허용오차1e-5다.

## v3.2 → v3.3 전후

동424×5경계 기준. 기능 구성 변경에 따른 차이며 이번에 남은 시설 좌표 변화는0이다. COV비율, PWATT초, 2SFCA시설수/1만명. 종합과 개별을 구분했다.

{table}
MAI는 어떤 비체육 시설 자체가 변하지 않아도 같은 격자의 동시입지 범주 수가 줄어 변한다. 개별 COV/PWATT와 생존2SFCA 불변은 이를 뒷받침한다. 구8범주 종합COV와 신7범주 종합COV의 차를 물리적 접근성의 시계열 변화로 해석하지 않는다.

## 한계·이력·정리

체육 입력문제의 HOLD는 체육 포함8범주 역사 결과에 한정한다. 현재7범주도 공공시설 인접 기준일 대리, 소매2019원본 요청 중/미입수, 의료 종료일 근사, OSM수록변화, 서울밖 시설 부재 및 시설수 공급 한계를 공개해야 한다. 면적비배정·추가 결합민감도는 실행하지 않았다.

타 연구 입력/원고/ZIP은 갱신하지 않았다. `후속소비_영향_v33_20260929.md`에 범주 변경과 허브설계 정정 권고를 기록했다. canonical교체 전후 SHA는 replacement_ledger.json, 삭제/보류는 cleanup_ledger.json, 최종 hash/metadata검사는 final_verification.json을 따른다. 이전 거부된 v3.2 stage와6캐시는 재시도하지 않는다. 출처·전처리·원자료·역사검증은 보존한다.
''')
write(Q/'문서/후속소비_영향_v33_20260929.md','''# v3.3 7범주 소비 영향

06만 재계산했다. 01/03/04 코드·모델·원고·공유ZIP/PDF는 수정하지 않았다. 이전8범주와 현재7범주 값을 혼용하지 않는다. 체육 제외와 좌표 수정은 별도 변경이다(v3.2→v3.3 좌표변경0).

| 소비자 | 갱신 시 주의 |
|---|---|
| 01 생활권 필요성 | 시설 연결표 및 시설 선택/cache 지문 재검토. 체육을 선택한 실험은 새 범위와 일치시켜야 함. grid/TTM은 불변 |
| 03 AG | main/xb/snap 서비스변수·c17격자·c18/c19/c20시설연결과 연계 산출물 새 입력으로 재평가. 종합COV7분모·MAI<=7, ΔMAI공통범주 및 시점 공통4 민감도. 기존 S1의 체육 HOLD는 구8범주 자료에 해당하며 원고담당자가 새 입력 적합성/수치를 함께 검토 |
| 04 KPA | k15→b5 접근성 및 k16→b6시설 입력과 후속표·모델·집필본 검토. 본문COV도 새7분모이므로 자동 불변을 주장하지 않음. 기존 r2 ZIP/PDF는 당시 스냅샷으로 보존 |

허브 `박사논문_연구설계.md` 4.3·4.5·7·9의33종/8범주/28종/B5 및 시설 구버전 문구는32종/7범주/27종/B4(6시설유형)/2SFCA34 및facility-v1.4로 정정 권고한다. A4 체육·문화는 문화만. 이 문서는 권고이며 허브설계 본문을 임의 수정하지 않았다.
''')
for filename in ['문서/배포검증_v32_20260929.md','문서/배포검증_20260929.md']:
 p=Q/filename;s=p.read_text(encoding='utf8');write(p,'> 역사판 기록. 현재7범주 정본과 해석 조건은 [v3.3 검증](배포검증_v33_20260929.md)을 따른다. 아래 당시 수치와 판정은 보존한다.\n\n'+s)
p=Q/'문서/작업기록.md';write(p,p.read_text(encoding='utf8')+'\n## 2026-09-29 v3.3 / facility-v1.4 체육시설업 제외\n\n사용자 및 시설 생산자 선택 완료 후 재계산. a02·22설정·공통4 다섯 설정·요약/표/그림을 생성,35시험 통과. 비체육 개별도달/시간·2SFCA 불변, 종합7분모/MAI7상한 검증. 원천21300행 제외 이외 값·좌표변경0. 구8범주 HOLD는 역사기록으로 분리, 현7범주는 출처 가정 아래 조건부 연구 사용. 타 연구/허브설계/원자료 수정 없음. Git쓰기·외부공유 없음. 실행·교체·정리·최종확인: 검증_v33_20260929.\n')
rp=Q/'문서/검증보고서.md';write(rp,rp.read_text(encoding='utf8').replace('코드·문서·데이터 0개 파일, 0.0 MB의 SHA-256.','현행 파일 수·용량·SHA-256은 manifest에 기록.'))
print('Docs written')
