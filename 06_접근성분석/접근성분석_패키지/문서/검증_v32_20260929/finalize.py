from pathlib import Path
import sys,os,json,datetime,shutil
A=Path(__file__).resolve().parent;R=Path('D:/Research/00_박사논문_연구체계');O=R/'06_접근성분석/접근성분석_패키지';D=O/'문서/검증_v32_20260929'
os.environ.pop('ACCESS_REPOSITORY_ROOT',None);sys.path.insert(0,str(O/'코드'))
import a11_provenance as P
import a10_verify as V
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=1),encoding='utf8')
plan=load(A/'cleanup_plan.json')
plan.update(status='blocked_by_automatic_policy_review',deleted_stage_files=0,deleted_bytecode_files=0,
 policy_reason='Tool rejected the compound PowerShell inventory + Remove-Item command: rejected: blocked by policy. No detailed reason was supplied.',
 denied_action='Remove-Item -LiteralPath $auditStage -Recurse -Force for exact stage_root, followed by six obsolete .pyc deletions. Command was rejected before execution.',
 readonly_recheck='After rejection, exact stage absolute containment, 1365 file hashes/sizes and absence of reparse points verified read-only. No delete or move retry.',
 stage_still_exists=Path(plan['stage_root']).exists(),
 manual_cleanup_targets=[plan['stage_root']]+[x['path'] for x in plan['obsolete_bytecode']],
 canonical_replacement_status='Completed before denied cleanup: 120 existing files replaced, 90 new files added; old numerical values at canonical paths replaced after validation.')
save(D/'cleanup_ledger.json',plan);save(A/'cleanup_result.json',plan)
note='''
## 정리 상태 — 자동 정책 차단

정본 120파일 교체·90파일 추가는 완료했다. 대체된 구 수치 파일은 같은 정본 경로에서 새 값으로 교체됐다. 이후 **작업용 stage 1,365파일(650,953,936바이트)과 구 Python 캐시 6개 삭제는 실행되지 않았다.** 복합 PowerShell 삭제 명령이 자동 정책 검토에서 `blocked by policy`로 거부됐으며 상세 사유는 제공되지 않았다. 삭제/이동 우회는 하지 않았다. 거부 후 읽기 전용 검사에서 경로 경계·전 파일 해시·reparse point 없음만 확인했다.

따라서 공유 대상은 **`06_접근성분석/접근성분석_패키지/`**이며 그 형제인 `_release_stage_v32_20260929_01`은 제외한다. 정확한 절대 삭제 후보 경로와 캐시 6개 목록은 [cleanup_ledger.json](검증_v32_20260929/cleanup_ledger.json)의 `manual_cleanup_targets`이다. 출처/원자료/증거/타 연구는 삭제 대상이 아니다. 로그·스크립트는 정본 검증 폴더와 개인 scratch `C:/Users/cyion/.codex/tmp/access-v32-release-20260929-01a0ea59`에 보존했다.
'''
for name in ['배포검증_v32_20260929.md','공동연구자_시작_20260929.md']:
 p=O/'문서'/name;p.write_text(p.read_text(encoding='utf8')+note,encoding='utf8')
p=O/'문서/작업기록.md';p.write_text(p.read_text(encoding='utf8')+'\n최종 정리 상태: 정본 교체 완료. 임시 stage1,365파일/구캐시6개 삭제 명령은 자동 정책 거부로 미실행, 재시도·이동 우회 없음. 공유는 정본 패키지만. 정확한 후보·보존·거부 기록 cleanup_ledger.json.\n',encoding='utf8')
p=O/'README.md';p.write_text(p.read_text(encoding='utf8')+'\n**공유 범위:** 이 `접근성분석_패키지` 폴더가 현행 정본이다. 형제 `_release_stage_v32_20260929_01`은 작업용 복제본이며 자동 삭제 정책 차단으로 남아 있어 공유에서 제외한다. [정리 상태](문서/검증_v32_20260929/cleanup_ledger.json).\n',encoding='utf8')
p=R/'공유_안내.md';p.write_text(p.read_text(encoding='utf8').replace('작업용 stage는 정리하며 실제 외부 공유는 수행하지 않았다.','작업용 `_release_stage_v32_20260929_01`은 자동 삭제 정책 차단으로 남아 있어 공유에서 제외하고 `접근성분석_패키지`만 공유 대상으로 삼는다. 실제 외부 공유는 수행하지 않았다.'),encoding='utf8')
shutil.copy2(A/'finalize.py',D/'finalize.py')
prov=load(O/'데이터/release_provenance.json');problems={}
for key,root in [('code',O),('package_inputs',O),('upstream_inputs',R),('source_evidence',R)]:problems[key]=P.check_inventory(prov[key],root)
assert not any(problems.values()),problems
metas=[]
for path in sorted((O/'데이터/결과').glob('*/run_meta*.json')):
 m=load(path);fails,unknown=P.metadata_issues(m,path)
 assert m['engine']=='access-engine-v3.2',(path,m.get('engine'))
 assert m['provenance']['upstream_inputs']['files'][0]['sha256']=='1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47'
 metas.append({'file':path.relative_to(O).as_posix(),'failures':fails,'unverified':unknown})
assert len(metas)==22 and not any(x['failures'] or x['unverified'] for x in metas)
checks=load(O/'데이터/검증결과.json');cr=[r for k,rows in checks.items() if isinstance(rows,list) and not k.startswith('_') for r in rows]
summary={'release':P.RELEASE,'checked_at':datetime.datetime.now().astimezone().isoformat(),'calculation_verdict':'PASS','scientific_fitness':'HOLD: historical sports selection filter unresolved','tests_passed':32,'engine_runs_succeeded':22,
 'metadata':{'fully_recorded':22,'historical_or_incomplete':0,'failed':0,'runs':metas},'provenance_inventory_issues':problems,
 'source_sha256':P.sha256(R/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet'),
 'recorded_checks':{'PASS':sum(x['결과']=='PASS' for x in cr),'WARN':sum(x['결과']=='WARN' for x in cr),'FAIL':sum(x['결과']=='FAIL' for x in cr)},
 'canonical_replaced_files':120,'canonical_new_files_before_final_evidence':90,'canonical_changed_since_initial_snapshot_before_promotion':0,
 'cleanup_status':plan['status'],'deleted_stage_files':0,'stage_files_pending':1365,'obsolete_bytecode_pending':6,'stage_excluded_from_share':True,
 'source_evidence_files':len(prov['source_evidence']['files']),'package_input_files':len(prov['package_inputs']['files'])}
save(D/'final_verification.json',summary)
n,b=V.write_manifest();n2,bad=V.manifest_errors(O,O/'데이터/manifest_sha256.csv');assert not bad
summary.update(manifest_files=n2,manifest_issues=0,manifest_bytes=b)
save(D/'final_verification.json',summary)
n,b=V.write_manifest();assert V.check_only()==0
save(A/'final_verification.json',summary)
print(json.dumps({k:summary[k] for k in ['release','tests_passed','engine_runs_succeeded','recorded_checks','manifest_files','manifest_issues','cleanup_status','source_sha256']},ensure_ascii=False))
