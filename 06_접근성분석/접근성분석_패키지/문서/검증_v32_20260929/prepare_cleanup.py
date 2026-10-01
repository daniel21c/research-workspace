from pathlib import Path
import hashlib,json,shutil,datetime
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';O=S.parent/'접근성분석_패키지';D=O/'문서/검증_v32_20260929'
A=Path('C:/Users/cyion/.codex/tmp/access-v32-release-20260929-01a0ea59');assert not A.exists();A.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}
base=json.loads((S/'baseline.json').read_text(encoding='utf8'))
# All package copies must match the published canonical content before deleting stage.
for p in Q.rglob('*'):
 if p.is_file():assert sha(p)==sha(O/p.relative_to(Q)),p
for p in S.iterdir():
 if p.is_file():shutil.copy2(p,A/p.name);assert sha(p)==sha(A/p.name)
for name in ['stage_publish_check.json','promotion_result.json','promote.log','prepare_cleanup.py']:
 shutil.copy2(S/name,D/name)
files=[row(p) for p in sorted(S.rglob('*')) if p.is_file()]
cache=[]
for p in O.rglob('*.pyc'):
 rel=p.relative_to(O).as_posix();assert rel in base and sha(p)==base[rel]['sha256'],p
 cache.append(row(p))
ledger={'schema':'cleanup-ledger/1','created_at':datetime.datetime.now().astimezone().isoformat(),'status':'authorized_plan',
 'authority':'User requested replacing/deleting superseded accessibility outputs after validation; task-created entire stage approved',
 'stage_root':str(S.resolve()),'owner_root':str(S.parent.resolve()),'forensic_archive':str(A),
 'ownership':'Stage created exclusively by this task; package copies verified byte-identical to canonical; all root logs/scripts copied and hash-verified to forensic archive; tmp only task verification scratch',
 'stage_files':files,'stage_count':len(files),'stage_bytes':sum(x['bytes'] for x in files),'obsolete_bytecode':cache,
 'preserved':'Canonical raw/source references, all unique upstream files, producer v1.2 archive, historical provenance, 01/03/04 and KPA ZIP/PDF/writing untouched',
 'replacement_ledger':'replacement_ledger.json','replacement_verification':'stage manifest 1309 files, 0 issues; 22 actual runs, 32 tests, fingerprints and independent SFCA checks passed'}
for p in [A/'cleanup_plan.json',D/'cleanup_ledger.json']:p.write_text(json.dumps(ledger,ensure_ascii=False,indent=1),encoding='utf8')
print('CLEANUP PLAN',len(files),'stage files',len(cache),'old bytecode',sum(x['bytes'] for x in files),'bytes',A)
