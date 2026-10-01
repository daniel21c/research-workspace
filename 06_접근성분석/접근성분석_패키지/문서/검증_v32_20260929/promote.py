from pathlib import Path
import os,sys,json,shutil,datetime
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';O=S.parent/'접근성분석_패키지';R=S.parent.parent;D=Q/'문서/검증_v32_20260929'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P
import a10_verify as V
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=1),encoding='utf8')
base=load(S/'baseline.json');actual={p.relative_to(O).as_posix():{'sha256':P.sha256(p),'bytes':p.stat().st_size} for p in O.rglob('*') if p.is_file()}
assert actual==base,'Canonical package changed since baseline; stop'
assert load(D/'verification_summary.json')['failed']==0
prov=load(Q/'데이터/release_provenance.json')
for key,root in [('code',Q),('package_inputs',Q),('upstream_inputs',R)]:assert not P.check_inventory(prov[key],root),(key,'stale')
for row in prov['source_evidence']['files']:
 p=R/row['file'];p=Q/p.relative_to(O) if p.is_relative_to(O) else p
 assert P.sha256(p)==row['sha256'],p
# Re-check shared docs now; mutations only accessibility rows / notes.
hub={}
for name in ['README.md','데이터_배포목록.md','공유_안내.md']:
 before=(S/('hub_before_'+name)).read_bytes();assert (R/name).read_bytes()==before,('hub concurrent change',name)
 text=(R/name).read_text(encoding='utf8')
 if name=='README.md':
  lines=text.splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith('| `06_접근성분석/`'):
    lines[i]=line.replace('facility-v1.2','facility-v1.3').replace('access-engine-v3)','access-engine-v3.2)').replace('연구 코드는 `접근성분석_패키지/데이터/결과/`만 참조.','정본 결과 `접근성분석_패키지/데이터/결과/` 참조. 체육 포함 역사비교 확정 해석은 입력 선택 문제로 보류; 현행 검증 `문서/배포검증_v32_20260929.md`.')
  text=''.join(lines)
 elif name=='데이터_배포목록.md':
  lines=text.splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith('| access-engine-v3 |'):lines[i]=line.replace('**확정** (2026-09-26','**대체됨** (2026-09-29 → v3.2; 당시 2026-09-26')
   if line.startswith('| access-engine-v3.1-20260929 |'):
    lines[i]=line.replace('현 공유 정본.','**대체됨** (2026-09-29 → access-engine-v3.2-facility-v1.3-20260929). 아래 검증은 당시 이력.')
    lines.insert(i+1,'| access-engine-v3.2-facility-v1.3-20260929 | 시설 v1.3 좌표 관련93행 반영, 22실행 전체/공통4 5설정/표·그림 재계산. 네 지표·경계 정의와 경로 유지 | `06_접근성분석/접근성분석_패키지/`; 시작 `문서/공동연구자_시작_20260929.md`, 검증 `문서/배포검증_v32_20260929.md` | 2026-09-29 | 전체 `데이터/manifest_sha256.csv`, 원천 시설 SHA 1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47, 출처/입력/코드 지문 `데이터/release_provenance.json` | 접근성 대화 / 06 | 현 계산·공유 정본. 엔진22/22·시험32/32, 메타22현재지문·오류0, 독립2SFCA861504값 최대상대오차5.94e-8. **체육 포함 역사비교 확정 해석 HOLD**: 현재상태 선택 문제 미해결. 이전06파생값 대체·stage정리 ledger 보존; 타연구·KPA공유본 수정 없음. |\n')
    break
  text=''.join(lines)
 elif name=='공유_안내.md':
  lines=text.splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith('| `06_접근성분석/접근성분석_패키지/`'):lines[i]=line.replace('access-engine-v3 |','access-engine-v3.2 (facility-v1.3) |')
   if line.startswith('06은 access-engine-v3.1-20260929'):
    lines[i]='06은 access-engine-v3.2-facility-v1.3-20260929 현 계산 정본을 사용한다. [공동연구자 안내](06_접근성분석/접근성분석_패키지/문서/공동연구자_시작_20260929.md)와 [현재 검증](06_접근성분석/접근성분석_패키지/문서/배포검증_v32_20260929.md) 참조. 22실행·표·그림 모두 갱신했고 이전 출처/검증은 이력으로 보존했다. 시설 선택 문제 때문에 체육 포함 역사비교의 확정 해석은 HOLD다. 원천 현행판은 배포목록 facility-v1.3 행을 따른다. 01/03/04 소비 결과·KPA r2 ZIP 및 별도 집필본은 자동 갱신되지 않았으므로 후속 영향 안내를 확인한다. 작업용 stage는 정리하며 실제 외부 공유는 수행하지 않았다.\n'
  text=''.join(lines)
 hub[name]=text
# Inventory exact replacement relationship before publication.
rows=[]
for p in sorted(Q.rglob('*')):
 if not p.is_file() or p.name=='manifest_sha256.csv':continue
 rel=p.relative_to(Q).as_posix();old=base.get(rel);new={'sha256':P.sha256(p),'bytes':p.stat().st_size}
 if old is None or old!=new:rows.append({'path':rel,'old':old,'new':new,'reason':'facility-v1.3 regenerated result or release code/document/evidence update','verification':'22 CLI successful; 32 tests; 22 fresh run fingerprints; independent SFCA; numerical and input invariants'})
ledger={'schema':'replacement-ledger/1','release':P.RELEASE,'baseline_files':len(base),'canonical_concurrent_changes':0,'replacements':sum(x['old'] is not None for x in rows),'new_files':sum(x['old'] is None for x in rows),'files':rows,'note':'Old numeric bytes at the same canonical path are replaced after stage validation; source/raw/history preserved. Manifest and this ledger are release administrative files.'}
save(D/'replacement_ledger.json',ledger)
shutil.copy2(S/'promote.py',D/'promote.py')
n,b=V.write_manifest();assert V.check_only()==0
save(S/'stage_publish_check.json',{'manifest_count':n,'manifest_issues':0,'source_evidence':len(prov['source_evidence']['files']),'baseline_files':len(base),'canonical_concurrent_changes':0,'tests_passed':32,'engine_runs':22})
for p in sorted(Q.rglob('*')):
 if p.is_file():
  target=O/p.relative_to(Q)
  if not target.exists() or P.sha256(target)!=P.sha256(p):target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for name,text in hub.items():(R/name).write_text(text,encoding='utf8')
for row in rows:
 assert P.sha256(O/row['path'])==row['new']['sha256'],row['path']
save(S/'promotion_result.json',{'status':'PASS','release':P.RELEASE,'replacements':ledger['replacements'],'new_files':ledger['new_files'],'manifest_count':n,'hub_files':list(hub),'source_sha256':P.sha256(R/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet')})
print('PROMOTED',ledger['replacements'],'replaced',ledger['new_files'],'new',n,'manifest')
