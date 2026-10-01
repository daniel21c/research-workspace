from pathlib import Path
import os,sys,json,shutil,datetime
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';R=Path('D:/Research/00_박사논문_연구체계');O=R/'06_접근성분석/접근성분석_패키지';Z=Q/'문서/검증_v33_20260929'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P,a10_verify as V
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
v=read(Z/'verification_summary.json');assert v['counts']['FAIL']==0
base=read(S/'baseline.json');baseline={x['file']:x for x in base['files']}
for rel,r in baseline.items():assert P.sha256(O/rel)==r['sha256'],f'concurrent change: {rel}'
metas=list((Q/'데이터/결과').glob('*/run_meta*.json'));assert len(metas)==22
for f in metas:
 m=read(f);assert m['engine']=='access-engine-v3.3';assert P.metadata_issues(m,f)==([],[])
changes=[]
for f in Q.rglob('*'):
 if not f.is_file() or '__pycache__' in f.parts:continue
 rel=f.relative_to(Q).as_posix();old=baseline.get(rel);new=P.sha256(f)
 if old is None or old['sha256']!=new:changes.append({'file':rel,'old_sha256':old['sha256'] if old else None,'new_sha256':new,'bytes':f.stat().st_size,'reason':'facility-v1.4 sports exclusion; validated current scope/results or preserved evidence'})
write(Z/'replacement_ledger.json',{'status':'validated_for_promotion','replaced_existing':sum(x['old_sha256'] is not None for x in changes),'added':sum(x['old_sha256'] is None for x in changes),'files':changes,'verification':'verification_summary.json; 22 current run metadata','historical_evidence':'이전_v32; baseline.json; phase1 logs retained in private scratch'})
write(Z/'cleanup_ledger.json',{'status':'canonical_replacement_complete_facility_cleanup_deferred','canonical_superseded_files_replaced':sum(x['old_sha256'] is not None for x in changes),'old_result_paths':'same filenames; replaced bytes are not kept as a second active release','obsolete_extra_canonical_result_files':[],'private_stage':str(S),'private_stage_cleanup':'pending final producer checkpoint','facility_files':5,'facility_bytes':76782692,'facility_cleanup':'deferred: current release_v14.verify still reads old archive as historical comparison inputs; producer will split replayable source rebuild from retained historical evidence','previous_denied_targets':'Never retried. See ../검증_v32_20260929/cleanup_ledger.json (1365-file stage plus 6 cache targets).','raw_source_provenance_and_history':'preserved'})
# Copy only changed/new owned files after the snapshot guard; do not mirror or remove unknown files.
for f in Q.rglob('*'):
 if not f.is_file() or '__pycache__' in f.parts:continue
 dest=O/f.relative_to(Q)
 if not dest.exists() or P.sha256(dest)!=P.sha256(f):dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
for x in changes:assert P.sha256(O/x['file'])==x['new_sha256']
# Only accessibility rows/paragraphs of shared hub documents.
hub=[]
for name in ['README.md','공유_안내.md','데이터_배포목록.md']:
 f=R/name;before=f.read_text(encoding='utf8');lines=before.splitlines();out=[]
 for line in lines:
  if name=='README.md' and line.startswith('| `06_접근성분석/`'):
   line='| `06_접근성분석/` | 공통 접근성 정본 `접근성분석_패키지/`: facility-v1.4 32종(분석27+통제5), A7범주/B4기능/2SFCA34항목, access-engine-v3.3. 22설정·35시험 검증. 출처 시점 대리·소매 미확보 조건 아래 사용. 시작 `문서/공동연구자_시작_20260929.md`, 검증 `문서/배포검증_v33_20260929.md`. 타 연구는 새7범주 값을 별도 반영해야 함 | 접근성 대화 |'
  elif name=='공유_안내.md' and line.startswith('| `06_접근성분석/접근성분석_패키지/`'):
   line='| `06_접근성분석/접근성분석_패키지/` | **접근성**: 32종 입력(분석27+통제5), A7범주/B4기능/2SFCA34항목. 22설정·표·그림·현재검증. 출처의 연구가정 아래 조건부 사용 | access-engine-v3.3 (facility-v1.4) |'
  elif name=='공유_안내.md' and line.startswith('- 접근성 전체('):
   line='- 접근성 전체(facility-v1.4, 7범주): `06_접근성분석/접근성분석_패키지/코드/run_engine.bat facility` (기존 파일을 덮어쓰므로 필요하면 별도 작업 사본에서 실행). 정확한 이번22명령은 `문서/검증_v33_20260929/execution.json`.'
  elif name=='공유_안내.md' and line.startswith('06은 access-engine-v3.2'):
   line='06은 **access-engine-v3.3-facility-v1.4-20260929** 정본을 사용한다. [공동연구자 안내](06_접근성분석/접근성분석_패키지/문서/공동연구자_시작_20260929.md)와 [현재 검증](06_접근성분석/접근성분석_패키지/문서/배포검증_v33_20260929.md) 참조. 체육시설업만 제외한7범주로22실행·표·그림 재생성,35시험 통과. 구8범주판의 체육 HOLD는 역사판에 적용하고 현7범주는 시점대리·소매원본 미확보 조건 아래 사용한다. 01/03/04 결과·원고·KPA ZIP은 자동갱신하지 않았다. 정책차단으로 남은 `_release_stage_v32_20260929_01`과 캐시는 공유에서 제외하고 `접근성분석_패키지`만 공유한다. 실제 외부공유 없음.'
  elif name=='데이터_배포목록.md' and line.startswith('| access-engine-v3.2-facility-v1.3-20260929 |'):
   line=line.replace('현 계산·공유 정본.','**대체됨** (→ access-engine-v3.3-facility-v1.4-20260929). 아래는 당시8범주판 검증 이력.')
  out.append(line)
 if name=='데이터_배포목록.md':
  pos=next(i for i,l in enumerate(out) if l.startswith('| access-engine-v3.2-facility-v1.3-20260929 |'))+1
  out.insert(pos,'| access-engine-v3.3-facility-v1.4-20260929 | 체육시설업21,300행 제외. A7범주/27분석종+통제5, B4기능, 2SFCA34항목. 22설정/공통4다섯설정/표·그림 재생성 | `06_접근성분석/접근성분석_패키지/`; 시작 `문서/공동연구자_시작_20260929.md`, 검증 `문서/배포검증_v33_20260929.md` | 2026-09-29 | 입력 SHA c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb; 전체 `데이터/manifest_sha256.csv`, `데이터/release_provenance.json` | 접근성 대화 / 06 | **현행**. 22/22실행·35/35시험. 비체육 개별COV/PWATT·2SFCA 불변, 종합7분모/MAI7상한 확인. 계산PASS·출처 시점대리/소매원본 미확보 조건 아래 사용. 구8범주와 혼용금지. 교체·정리 이력 보존, 타연구 미수정 |')
 after='\n'.join(out)+'\n';assert f.read_text(encoding='utf8')==before
 if after!=before:hub.append({'file':name,'old_sha256':P.sha256(f)});f.write_text(after,encoding='utf8');hub[-1]['new_sha256']=P.sha256(f)
f=O.parent/'README.md';s=f.read_text(encoding='utf8');s=s.replace('이 폴더에는 **`접근성분석_패키지/`** 하나만 있다.','현행 공유 정본은 **`접근성분석_패키지/`**다. 이전 정책차단 stage `_release_stage_v32_20260929_01`은 보존 중이며 공유 대상에서 제외한다.');s+='\n현행 access-engine-v3.3 / facility-v1.4: 체육시설업 제외, A7범주/B4기능, 22설정·35시험. 상세 현재 시작 문서를 따른다.\n';f.write_text(s,encoding='utf8')
write(O/'문서/검증_v33_20260929/hub_changes.json',hub)
print('PROMOTED',len(changes),'files; source-provenance and final manifest pending producer checkpoint')
