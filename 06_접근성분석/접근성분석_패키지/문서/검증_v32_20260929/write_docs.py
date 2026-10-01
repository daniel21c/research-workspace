from pathlib import Path
import sys,os,json,shutil,datetime,re
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';O=S.parent/'접근성분석_패키지';R=S.parent.parent;D=Q/'문서/검증_v32_20260929'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,s):p.write_text(s,encoding='utf8')
v=read(D/'verification_summary.json');sup=read(D/'supplementary_checks.json');execution=read(S/'execution.json')
assert v['failed']==0 and all(x['exit_code']==0 for x in execution)
for p in S.iterdir():
 if p.is_file() and (p.suffix in ['.log','.py','.json']):shutil.copy2(p,D/p.name)
temporal=read(Q/'데이터/결과/temporal_common4/verification.json')['cases']
tbl='| 연도 | 지표 | 바뀐 동 | 바뀐 행 | 최대 절대차 |\n|---|---|---:|---:|---:|\n'
for row in v['main']:tbl+=f"| {row['year']} | {row['metric']} | {row['changed_dongs']} | {row['changed_rows']} | {row['max_abs']:.6f} |\n"
comp='| 연도 | 지표 | 종합값 변경 동(5경계 합집합) | 종합 최대 절대차 |\n|---|---|---:|---:|\n'
for row in sup['main_scope_breakdown']:
 if row['category_scope']=='종합' and row['b']=='all' and row['metric'] in ['COV','MAI']:comp+=f"| {row['year']} | {row['metric']} | {row['changed_dongs']} | {row['max_abs']:.6f} |\n"
tt='| 설정 | 변경 동 / 부호반전 |\n|---|---:|\n'+''.join(f"| {x['case']} | {x['changed']} / {x['sign_changes']} |\n" for x in temporal)
report=f'''# 시설 v1.3 반영·배포 검증 — access-engine-v3.2 (2026-09-29)

**계산·배포 검증 PASS. 체육을 포함한 역사비교의 확정 해석은 HOLD.** 현재 시설 자료를 사용한 재계산은 완료했지만, 현재 취소·말소 상태로 과거 운영 후보를 제외한 입력 구성 문제는 좌표 보정판 v1.3에서 해결되지 않았다. 이는 일반적인 방법론 한계와 구분한다. 원천 시설 선택을 정정한 새 판과 영향 재평가가 필요하다. 이번에는 시설 생산 규칙·타 연구 결과를 수정하지 않았다.

## 실행 및 검증

- 입력 SHA-256: `1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47`. 실제 606,066행/25열, 분석가능 603,066행. v1.2와 키·행·비좌표 속성 동일, 좌표·공간배정·분석가능·coord_method 93행 변경(87 보완, 4 교정, 2 제외).
- 시설–경계 연결을 a02로 다시 생성하고 **22/22 엔진 CLI**를 성공적으로 실행했다. 2SFCA, 국가기준 B, xb 3실행, snap 두 연도 포함. 모든 22개 메타의 현재 코드·입력·출력 지문과 필수 불변조건 일치; 역사/불완전 메타 0개. 이전 메타는 `검증_v32_20260929/이전_v31`에 보존.
- **32/32 시험**: 엔진17 + 기하4 + 배포11. 배포 schema2는 패키지 이동 후 입력 검증과 원천 변경 감지를 포함한다. 실행 코드 a00/a06/a11 지문은 실행 후 변경하지 않았다.
- 2SFCA 별도 pandas 구현: 2020 430,514 + 2025 430,990 = **861,504개 격자값**, 최대 상대오차 **5.94e-8**. 공공도서관·어린이집·체육시설업·주민센터·문화·의료·체육 × 경계 없음/공식 생활권. 전체 민감도 모든 셀의 독립 재구현 검증을 뜻하지 않는다.
- 전체 엔진 직접 산출물 **{sup['direct_count']}파일**, v1.2 대비 SHA 변경 **{sup['changed_direct_count']}파일**. A/2SFCA CSV 35파일 및 B CSV 2파일의 키·스키마·전체인구 분모 불변. 시설/범주 공급이 불변인 2SFCA **913,880행 변경 0**. xb 기존 다섯 경계는 대응 main/망고정 결과와 동일(3실행).
- 격자·경계·보행망·TTM·snap 입력 **1,033파일 SHA 불변**. a05는 모든 도착 격자의 중심을 계산하므로 시설 변화와 무관하다. 인구·망을 다시 수집하거나 TTM을 다시 만들지 않았다.
- a06b_summary, a07_study3_outputs, a08_ku_compare와 공통4 다섯 설정을 현행 결과에서 재생성했다. 그림 PNG 표기·범례·424동 지도 확인. 기존 `데이터/검증결과.json`, `문서/검증보고서.md`도 이번 결과로 재생성했다.

명령·시간·종료코드: [execution.json](검증_v32_20260929/execution.json). 전체 엔진 실행시간 합계 {sum(x['seconds'] for x in execution if x['name'].startswith('engine_')):.1f}초. 새 지문의 시간은 실제 이번 생성시각이다. 과거 생성증거를 사후 보충하지 않았다. 보조 비교 스크립트의 MultiIndex 호출 오타 1건은 수정했고, 먼저 성공한 독립 계산은 보존 로그에서 이어받아 반복하지 않았다(`verification_phase1.log`, `verification_resume.log`).

## main 전후 영향

아래는 **동424×다섯 경계×전체 카테고리/시설 항목** 범위다. 한 동에 여러 변경 행이 있다. COV는 0–1 비율, PWATT는 초, 2SFCA는 인구 1만 명당 시설수다. 최대차를 서울 전체 종합값 차이로 해석하지 않는다.

{tbl}
{comp}
문화·생활서비스의 COV/MAI 변화가 중심이며 상세 변경 항목, 경계별 최대값·동 코드, Δ(LD−LZ)의 변화는 [numerical_changes.json](검증_v32_20260929/numerical_changes.json), [supplementary_checks.json](검증_v32_20260929/supplementary_checks.json)에 있다. 공급이 불변인 시설 종의 2SFCA는 그대로이며 MAI는 동시입지 범주의 변화에도 반응할 수 있다.

## 시점 차분·강건성

동424 전체, 네 조건(두 연도×LD/LZ)에서 모두 유효한 범주 교집합의 평균을 사용한 추가 민감도다. 연도별 두 경계 공통범주 차분을 기본으로 유지했다. 변경 기준 |공통4−기본|>1e-12, 부호반전은 곱<0이며 시설판 변경 동 수와 다른 비교다.

{tt}
설정별 실제 입력·경계 이름·해시는 `데이터/결과/temporal_common4/verification.json`에 기록했다. 이동LD·망2025 고정과 고정LD20·망2025는 서로 다른 설정이다. 민감도 최소 순위상관은 수준 COV/MAI 0.437, Δ 0.417, 공공시설 2SFCA 0.885. 250m·10분 민감도에 주의한다.

## 입력 적합성·소비자·정리

체육 선택 문제 근거는 AG S1.6(2026-09-29)과 시설 `13_좌표보완` 증거에 연결했다. 원 종료일이 기준일 뒤인 제외 기록 2020 1,480행/2025 167행, 추가 2020 최종수정일 대체 14행은 물리적 시설 수나 실제 결과 영향 수가 아니다. 이 조건을 원천에서 수정하기 전 체육 포함 역사비교를 확정하지 않는다. 소매 시점·의료 종료일 근사·OSM 수록변화 등 별도 불확실성도 출처 연결표에 남겼다.

01 현재 reanalysis 입력 투영, 03 AG 서비스 지표/시점 비교, 04 KPA b5 접근성·b6 유인시설 및 이들의 표·원고·공유본은 별도 갱신 검토 대상이다. [후속 소비 영향](후속소비_영향_v32_20260929.md) 참조. 이번에 타 연구·KPA ZIP/PDF·집필본을 덮어쓰지 않았다.

정본은 기존 파일명으로 교체한다. 교체 전후 SHA와 이유는 `검증_v32_20260929/replacement_ledger.json`, 임시 stage 전체 정리는 `cleanup_ledger.json`에 남긴다. 원자료·출처·전처리 기록·기존 감사는 보존한다. 현행 manifest와 metadata-only 최종 검사는 `final_verification.json`에 기록한다.
'''
write(Q/'문서/배포검증_v32_20260929.md',report)
oldrep=Q/'문서/배포검증_20260929.md';s=oldrep.read_text(encoding='utf8');write(oldrep,'> 역사 기록: 이 문서는 facility-v1.2 / access-engine-v3.1 당시 판정이다. 현행판은 [v3.2 검증](배포검증_v32_20260929.md)이며 입력 적합성 보류를 별도로 따른다.\n\n'+s)
guide=Q/'문서/공동연구자_시작_20260929.md';s=guide.read_text(encoding='utf8')
s=s.replace('access-engine-v3.1-20260929',P.RELEASE)
s=s.replace(s.split('\n\n')[1], '2026-09-29 시설 v1.3 재계산판. 22개 설정과 표·그림을 모두 새로 만들었다. **계산 검증은 PASS지만, 체육 현재상태 필터의 과거 후보 제외 문제로 체육 포함 역사비교 확정 해석은 HOLD**다. 좌표 보정과 시설 선택 적합성을 구분한다. 상세 [현재 배포 검증](배포검증_v32_20260929.md)을 먼저 확인한다.')
s=s.replace('[현재 검증 기록](배포검증_20260929.md)','[현재 검증 기록](배포검증_v32_20260929.md)')
s=s.replace('`문서/검증보고서.md`와 `데이터/검증결과.json`은 2026-09-26의 역사 검증 기록이며 최신 범위의 대용으로 쓰지 않는다.','`문서/검증보고서.md`와 `데이터/검증결과.json`은 이번 v3.2 결과에서 재생성한 검사 기록이다. v3.1 당시 기록은 `문서/검증_v32_20260929/이전_v31/`에 보존했다.')
s=s.replace('과거 실행에 없던 지문은 사후 생성하지 않아 WARN으로 남는다. 이번 독립 재실행 증거는 `데이터/release_provenance.json` 및 `문서/검증_20260929/`에서 별도로 확인한다.','이번에 전부 실제 재실행하여 22개 메타가 모두 현재 코드·입력 지문을 갖는다. v3.1의 16개 역사 지문 부재 기록은 이전판 이력으로 보존했다. 이번 증거는 `데이터/release_provenance.json` 및 `문서/검증_v32_20260929/`에서 확인한다.')
s=s.replace('본 분석 파일의 기존 경로·값·정의는 바꾸지 않았다.','본 분석 경로·정의는 유지하고 값은 시설 v1.3으로 갱신했다.')
s+='\n## 재계산 연결과 입력 상태\n\n시설을 바꾸면 `a02_facility_boundary.py` → `run_engine.bat` 전체 22설정 → `a06d_temporal_sensitivity.py` → `a06b_summary.py` → `a07_study3_outputs.py` → `a08_ku_compare.py` → `a10_verify.py` 순으로 갱신한다. 기존 격자·망이 같으면 TTM은 재사용한다. `ACCESS_REPOSITORY_ROOT`는 임시 패키지 사본이 저장소 원천을 읽을 때만 설정하며 통상 정본에서는 설정하지 않는다. schema2 메타는 패키지 입력을 상대경로로 기록한다.\n\n체육 포함 역사비교 확정 해석의 보류는 계산 오류가 아닌 현재 입력 구성 문제다. 원천 선택 규칙 정정 후 새 시설판으로 재계산하고 타 연구 소비자가 영향 검토를 해야 한다. 현행 파일을 사용했다는 이유로 기존 AG/KPA 원고·공유본이 자동 갱신된 것은 아니다.\n'
write(guide,s)
src=Q/'문서/출처_전처리_연결표_20260929.md';s=src.read_text(encoding='utf8').replace('2026-09-29 정비판','2026-09-29 v3.2 / facility-v1.3').replace('facility-v1.2','facility-v1.3').replace('b87ed1cc198bec94d21808b2eb8d0314b6b4b45662782db019a96f3804aef39f','1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47')
s=s.replace('- 체육 인허가 상태·폐업일 보완 규칙과 현재 명부 사용은 선택 영향을 줄 수 있다. 체육 규칙별, 시설 경계 면적배정, 서울 밖 시설 보완 민감도는 미실행이다.','- **입력 구성 문제 / 확정 해석 HOLD:** 현재 취소·말소 상태 필터가 과거 기준일 뒤 종료된 체육 후보를 제외한다. v1.3의 93행 좌표 보정은 이 선택 규칙을 바꾸지 않았다. 체육 포함 역사비교를 확정하기 전 원천 선택 정정과 재평가가 필요하다. 단순 한계 문구로 해소되는 문제가 아니다. 체육 규칙별·시설 경계 면적배정·서울 밖 시설 보완 민감도는 미실행이다.')
s+='''
## v1.3 좌표 보정 연결 (이번 갱신)

시설 `구축코드/13_좌표보완/README.md` → `입력/accepted_baseline_hashes.json` → 보완후보 `patch_manifest.json` 및 `verification.json`, 13의 `근거/repairs.json`, `근거/targeted_repairs.json`, `release_v13.py` → `stage_verification.json`, `promotion_manifest.json`, `build_hashes.json`, `final_verification.json` → 현행 분석용 parquet. 원문·판정·제외 사유는 생산자 증거를 그대로 참조한다. 직접 전체 행 대조에서 87 결측 좌표 보완, 4 좌표 교정, 2 분석 제외로 좌표/공간배정/분석가능/coord_method 93행만 달라졌다. 분석가능 603,066행. 획득일·기준일·시설명·기관·원천 설명은 새로 추정하거나 바꾸지 않았다.

이전 시설 파일은 생산자가 `D:/Research/_archive/facility-v1.2_superseded_20260929/데이터/`로 보관했다. SHA b87ed1cc198bec94d21808b2eb8d0314b6b4b45662782db019a96f3804aef39f. 이번 접근성 작업은 해당 보관본이나 원자료를 삭제하지 않았다. 이 패키지에는 raw를 복제하지 않았으며 저장소 상대 참조와 해시로 연결한다.

선택 필터 확인은 `03_불일치_접근성_AG/explore/v3/manuscript/AG_v3_자료보완판_20260929/S1_자료_출처와_전처리.md` S1.6 및 `explore/v3/입력확인_내부기록_20260929/final_verification.json`(held)이다. 기준일 이후 원 종료일이 있는 제외 기록은 2020 1,480/2025 167행, 최종수정일 대체 체육 2020 14행도 제외됐다. 기록 수와 물리적 시설·실제 영향 수를 혼동하지 않는다. 같은 근거에서 남아 있는 의원/병원 종료일 근사 2020 504/2025 149행도 실제 폐업일 행별 입증이 없다는 별도 불확실성이다. v1.3의 형식·해시·좌표 검증 PASS는 이 과거 선정 적합성을 보증하지 않는다.
'''
write(src,s)
rd=Q/'README.md';s=rd.read_text(encoding='utf8').replace('access-engine-v3.1-20260929',P.RELEASE).replace('facility-v1.2','facility-v1.3').replace('b87ed1cc…f39f','1a097e95…7a47')
s=s.replace('기존 검증보고서는 당시 이력이다. 실행 지문은 새 6실행에서 실제 기록했으며 나머지16 역사 메타의 지문 부재를 소급 조작하지 않았다.','22실행·표·그림·검증보고서를 시설 v1.3으로 재생성했다. 22개 실행 메타 모두 실제 이번 코드/입력 지문을 가진다. **체육 포함 역사비교 확정 해석은 현재 시설 선택 문제로 HOLD**다. 이전 v3.1 검증은 이력 폴더에 보존했다.').replace('(문서/배포검증_20260929.md)','(문서/배포검증_v32_20260929.md)')
write(rd,s)
write(Q/'문서/후속소비_영향_v32_20260929.md','''# 현행 시설 v1.3에 따른 후속 소비 영향 (읽기 전용 추적)

06 정본만 갱신했다. 아래 연구 코드·원고·공유본은 수정/재실행/삭제하지 않았다. 이전 시설판과 새 접근성판을 혼합하지 말고 연구 담당자가 자기 입력 지문과 표·모델을 재평가해야 한다. 체육 포함 역사비교 확정 해석은 원천 선택 정정 전 보류한다.

| 소비자 | 확인된 코드/입력 | 권고 범위 |
|---|---|---|
| 연구1 | `01_생활권_필요성/code/reanalysis_v2/prepare.py:43,52`의 연결표와 격자; `code/r1lib.py`의06참조 | 7시설 선택의 입력 투영·facility_counts/cache 지문 재생성 및 해당 결과 영향 확인. 인구/TTM 자체는 동일 |
| AG | `03_불일치_접근성_AG` 서비스 접근성·시점 비교(main/xb/snap), c17 격자 접근성, c18/c19/c20 시설 연결 | 현재 S1의 입력 부적합 보류 상태를 유지. 원천 선택을 먼저 정정하고 새 service 결과·시점 민감도·원고 수치를 함께 검토 |
| KPA | `04_불일치_시간변화_KPA/scripts/k15_access_link.py:19,72` main/10분 unit_access → b5; `scripts/k16_attractors.py` 시설 연결 → b6 | 이번에는 COV도 변했으므로 이전 MAI 정정 때의 '본문 COV 불변' 결론을 재사용하지 않음. b5/b6 및 k18/k19 소비와 현행 `writing/KPA_v2_집필작업본_20260929` 참조 입력·표를 재평가. 기존 교수검토 r2 ZIP/PDF는 당시 스냅샷으로 보존 |

이 기록은 현재 소비 경로를 확인한 영향 목록이며 타 연구의 통계 결론을 다시 검증한 보고가 아니다. 과거 KPA ZIP 처리 선택은 미응답으로 이번에도 보존했다. 실제 외부 공유는 하지 않았다.
''')
log=Q/'문서/작업기록.md';s=log.read_text(encoding='utf8');s+='''
## 2026-09-29 시설 v1.3 반영 (access-engine-v3.2)

사용자 최신 시설로 재계산·이전 산출물 대체/삭제 승인. 93행 좌표 관련 변경을 직접 확인하고 a02 재구축, 22개 엔진 CLI와 공통4 5설정/요약/표/그림 재생성. 엔진17+기하4+배포11=32시험 통과, 22메타 모두 현재 지문, 861,504개 2SFCA 독립 비교 최대 상대오차5.94e-8. 격자/경계/망/TTM1,033파일 불변. schema2는 임시 사본→정본 이동 후 상대 입력 지문 검증을 지원한다. 원천 시설 현재상태 선택 문제는 미해결이므로 체육 포함 역사비교 확정 해석 HOLD를 별도 기록. 타 연구·KPA 공유본·원자료·코어는 수정하지 않음. Git 쓰기/외부 전송 없음. 정본 교체/삭제/최종검증 상세는 `배포검증_v32_20260929.md`, `검증_v32_20260929`.
''';write(log,s)
# Current generated report should not advertise its temporary pre-manifest count.
rp=Q/'문서/검증보고서.md';s=rp.read_text(encoding='utf8');s=s.replace('코드·문서·데이터 0개 파일, 0.0 MB의 SHA-256.','현행 코드·문서·데이터의 SHA-256·파일 수·용량은 manifest 자체에 기록.');s=s.replace('## 5. 패키지 해시','## 6. 패키지 해시');write(rp,s)
# Release provenance: no self, manifest or output-recursive hash cycles.
prev=read(D/'이전_v31/release_provenance.json') if (D/'이전_v31/release_provenance.json').exists() else read(Q/'데이터/release_provenance.json')
evidence=[r['file'] for r in prev['source_evidence']['files']]
prefix='시설데이터 구축/시설데이터_패키지/구축코드/13_좌표보완/'
evidence += [prefix+x for x in ['README.md','final_verification.json','promotion_manifest.json','build_hashes.json','stage_verification.json','archive_result.json','입력/accepted_baseline_hashes.json','근거/repairs.json','근거/targeted_repairs.json','release_v13.py']]
evidence += ['03_불일치_접근성_AG/explore/v3/manuscript/AG_v3_자료보완판_20260929/S1_자료_출처와_전처리.md','03_불일치_접근성_AG/explore/v3/입력확인_내부기록_20260929/final_verification.json']
rows=[];missing=[]
for rel in sorted(set(evidence)):
 p=R/rel
 if p.is_relative_to(O):p=Q/p.relative_to(O)
 if p.is_file():rows.append({'file':rel,'bytes':p.stat().st_size,'sha256':P.sha256(p)})
 else:missing.append(rel)
assert not missing,missing
release={'schema':'access-release-provenance/2','release':P.RELEASE,'recorded_at':datetime.datetime.now().astimezone().isoformat(),'environment':P.runtime_environment(),
 'meaning':'Current release inventory; all 22 run metadata generated by actual new execution. Old v3.1 evidence retained separately.',
 'repository_base':'two directories above package','source_evidence':{'sha256':P.digest(rows),'files':rows},
 'upstream_inputs':P.inventory([R/x['file'] for x in prev['upstream_inputs']['files']],R),
 'package_inputs':P.inventory([p for p in (Q/'데이터/입력').rglob('*') if p.is_file()],Q),
 'code':P.inventory([p for p in (Q/'코드').rglob('*') if p.is_file() and '__pycache__' not in p.parts],Q),
 'validation':{'summary':'문서/검증_v32_20260929/verification_summary.json','execution':'문서/검증_v32_20260929/execution.json','tests_passed':32,'engine_runs_succeeded':22,'metadata_fully_recorded':22,'metadata_failed':0,'scientific_fitness':'HOLD: unresolved historical sports current-state selection filter','independent_sfca_grid_values':861504},
 'raw_data_policy':'No new raw copies; upstream repository references and source evidence hashes. Producer v1.2 archive retained.',
 'limitations':['sports selection unresolved','source reference dates differ','retail historic snapshot uncertainty','end-date imputation uncertainty','OSM inventory versus physical change inseparable','no outside-Seoul destinations','untested alternate sports/area allocation rules']}
write(Q/'데이터/release_provenance.json',json.dumps(release,ensure_ascii=False,indent=1))
print('DOCS',len(rows),'source evidence',len(release['package_inputs']['files']),'inputs')
