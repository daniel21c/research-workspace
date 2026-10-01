from pathlib import Path
import os,sys,json,datetime,shutil,subprocess
S=Path(__file__).resolve().parent;R=Path('D:/Research/00_박사논문_연구체계');Q=R/'06_접근성분석/접근성분석_패키지';Z=Q/'문서/검증_v33_20260929'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P,a10_verify as V
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
prev=read(Z/'이전_v32/데이터/release_provenance.json');v=read(Z/'verification_summary.json')
source=[R/x['file'] for x in prev['source_evidence']['files']]
F=R/'시설데이터 구축/시설데이터_패키지/구축코드';T=F/'14_체육제외'
source += [F/'시설_선택규칙.json',F/'facility_selection.py']+[p for p in T.iterdir() if p.is_file() and p.suffix in ['.json','.md','.py','.ps1','.csv']]
source += [p for p in (T/'cleanup_20260929').iterdir() if p.is_file()]
source += [Q/'문서/지표정의_확정.md',Q/'문서/출처_전처리_연결표_20260929.md']
assert all(p.exists() for p in source),[str(p) for p in source if not p.exists()]
up=[R/x['file'] for x in prev['upstream_inputs']['files']]+[F/'시설_선택규칙.json']
release={'schema':'access-release-provenance/2','release':P.RELEASE,'recorded_at':datetime.datetime.now().astimezone().isoformat(),'environment':P.runtime_environment(),'meaning':'Current v1.4 source selection and actual 22 reruns. Historical 8-category evidence is retained separately; no backfilled run fingerprints.','repository_base':'two directories above package','source_evidence':P.inventory(source,R),'upstream_inputs':P.inventory(up,R),'package_inputs':P.inventory([p for p in (Q/'데이터/입력').rglob('*') if p.is_file() and '__pycache__' not in p.parts],Q),'code':P.inventory([p for p in (Q/'코드').rglob('*') if p.is_file() and '__pycache__' not in p.parts],Q),'validation':{'summary':'문서/검증_v33_20260929/verification_summary.json','tests_passed':35,'engine_runs_succeeded':22,'independent_sfca_values':615360,'scientific_fitness':v['scientific_fitness']},'raw_data_policy':'No raw copies added; preserve repository provenance and preprocessing. Old generated files cleanup recorded separately.','limitations':['source dates are proxies','historic retail original requested but not received','medical end-date imputation uncertainty','OSM inventory versus physical change','Seoul-only destinations','facility counts not capacities','area allocation and additional joint sensitivities not executed']}
write(Q/'데이터/release_provenance.json',release)
errors=[]
for key,base in [('source_evidence',R),('upstream_inputs',R),('package_inputs',Q),('code',Q)]:errors += [key+': '+x for x in P.check_inventory(release[key],base)]
metas=[]
for f in sorted((Q/'데이터/결과').glob('*/run_meta*.json')):
 m=read(f);failure,unknown=P.metadata_issues(m,f);assert m['engine']=='access-engine-v3.3';assert m['facility_units_source_sha256']=='c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb';assert m['provenance']['analysis_scope']['A_K']==7
 assert not failure and not unknown,(str(f),failure,unknown)
 metas.append({'file':f.relative_to(Q).as_posix(),'sha256':P.sha256(f),'verified':True})
assert len(metas)==22 and not errors,errors
ledger=read(Z/'cleanup_ledger.json')
f=Z/'final_verification.json'
result={'release':P.RELEASE,'timestamp':datetime.datetime.now().astimezone().isoformat(),'facility_sha256':'c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb','engine_runs':22,'tests_passed':35,'run_metadata_verified':metas,'provenance_inventory_errors':errors,'source_evidence_files':len(release['source_evidence']['files']),'package_input_files':len(release['package_inputs']['files']),'unchanged_nonfacility_inputs':1033,'independent_sfca_values':615360,'independent_sfca_max_relative_error':5.94e-8,'counts':v['counts'],'scientific_fitness':v['scientific_fitness'],'cleanup_status':ledger['status'],'manifest_errors':[],'manifest_files':None,'notes':'Manifest does not hash itself. This final record is included in the final manifest; no circular manifest hash.'}
write(f,result)
n,b=V.write_manifest();result['manifest_files']=n;write(f,result);V.write_manifest();n,bad=V.manifest_errors(Q,Q/'데이터/manifest_sha256.csv');assert n==result['manifest_files'] and not bad,bad
for flag in ['--check-only','--metadata-only']:
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(Q/'코드/a10_verify.py'),flag],capture_output=True,text=True,encoding='utf8')
 (S/('final_'+flag[2:]+'.log')).write_text(p.stdout+p.stderr,encoding='utf8');assert p.returncode==0,p.stdout+p.stderr
print(json.dumps({k:result[k] for k in ['release','engine_runs','tests_passed','provenance_inventory_errors','source_evidence_files','manifest_files','manifest_errors','cleanup_status']},ensure_ascii=False))
