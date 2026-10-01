from pathlib import Path
import json, hashlib, datetime
S=Path(__file__).resolve().parent; Q=S/'접근성분석_패키지'
R=Path('D:/Research/00_박사논문_연구체계'); P=R/'06_접근성분석/접근성분석_패키지'; Z=P/'문서/검증_v33_20260929'
F=R/'시설데이터 구축/시설데이터_패키지'; T=F/'구축코드/14_체육제외'; H=T/'cleanup_20260929'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
stamp=datetime.datetime.now().astimezone().isoformat()
assert sha(F/'데이터/서울시설_2020_2025_분석용.parquet')=='c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb'
assert sha(F/'구축코드/시설_선택규칙.json')=='c3705db3174dbb907cbdd90d5fbe57c47a3c64b0b0179ca7b5c5ea2324fec7b7'
receipt=read(H/'deletion_receipt.json'); done=read(H/'completion_summary.json'); verify=read(T/'final_verification.json')
assert done['PASS'] and verify['PASS'] and verify['adopted_input_files_verified']==130
assert done['history_sha256']==sha(H/'historical_evidence.json') and done['receipt_sha256']==sha(H/'deletion_receipt.json')
assert receipt['deleted_file_count']==5 and receipt['deleted_bytes']==76782692
for f in receipt['files']:
 assert not Path(f['archive']).exists()
 assert sha(F/f['relative_path'])==f['replacement_sha256']
# Before further document changes, every task-created stage byte has its canonical copy.
stage=[]
for p in sorted(Q.rglob('*')):
 assert not p.is_symlink(),str(p)
 if p.is_file():
  rel=p.relative_to(Q).as_posix();dest=P/rel
  assert dest.is_file() and sha(p)==sha(dest),rel
  stage.append({'path':str(p.resolve()),'relative_path':rel,'bytes':p.stat().st_size,'sha256':sha(p),'preserved_path':str(dest.resolve())})
inventory={'status':'verified_duplicate_candidates','stage_root':str(Q.resolve()),'scratch_root':str(S.resolve()),'created_by':'this task prepare.py copytree; original baseline and scripts retained outside stage','verified_at':stamp,'files':stage,'file_count':len(stage),'bytes':sum(x['bytes'] for x in stage),'all_files_canonical_hash_equal':True,'prior_denied_targets_in_scope':False,'evidence_preserved':'S root logs, scripts and phase1 history; canonical verification records; only this Q duplicate is a deletion candidate'}
write(S/'private_stage_inventory.json',inventory);write(Z/'private_stage_inventory.json',inventory)
ledger=read(Z/'replacement_ledger.json')
for f in ledger['files']: assert sha(P/f['file'])==f['new_sha256'],f['file']
ledger['status']='promoted_and_verified';ledger['promotion_verified_at']=stamp
ledger['post_promotion_document_finalization']='Current documentation, release provenance and manifest finalized separately after facility producer cleanup; original promotion hashes retain the actual earlier snapshot.'
write(Z/'replacement_ledger.json',ledger)
c=read(Z/'cleanup_ledger.json');c.update(status='canonical_replacement_and_facility_cleanup_complete_private_stage_pending',private_stage=str(Q.resolve()),private_stage_cleanup='hash-verified duplicate; pending native PowerShell deletion',private_stage_files=len(stage),private_stage_bytes=inventory['bytes'],facility_cleanup='completed by facility producer; verified old paths absent and all five replacement hashes',facility_cleanup_receipt=str((H/'deletion_receipt.json').relative_to(R)),facility_cleanup_receipt_sha256=sha(H/'deletion_receipt.json'),facility_cleanup_completion=str((H/'completion_summary.json').relative_to(R)),facility_current_verification=str((T/'final_verification.json').relative_to(R)),facility_cleanup_files=receipt['files'])
write(Z/'cleanup_ledger.json',c)
p=P/'문서/출처_전처리_연결표_20260929.md';s=p.read_text(encoding='utf8').replace('33종별 실제 기관','유형별 실제 기관')
s=s.replace('구시설5파일 정리는 producer verify의 역사비교 의존성을 분리한 뒤에만 가능하며 처리 상태는 cleanup_ledger.json을 따른다.','시설 생산자는 역사 비교 증거와 현재 130원천 재생성 검증을 분리한 뒤 구 v1.3 생성물 5파일(76,782,692 bytes)을 삭제했다. `구축코드/14_체육제외/cleanup_20260929/historical_evidence.json`, `deletion_receipt.json`, `completion_summary.json` 및 14의 `final_verification.json`이 연결 근거다. 삭제 후 현재 v1.4 재생성 해시는 일치했고, 과거 v1.3 전행 비교는 보존된 실행 증거이며 삭제 후 새로 수행했다고 주장하지 않는다. 접근성 정리 상태는 `검증_v33_20260929/cleanup_ledger.json`을 따른다.')
p.write_text(s,encoding='utf8')
p=P/'문서/배포검증_v33_20260929.md';s=p.read_text(encoding='utf8')
s=s.replace('정확한 비교 셀 수·최대상대오차는 verification.log의 실제 출력 및 검증보고서 참조.','615,360개 격자값 대조, 최대 상대오차 5.94e-8. `검증_v33_20260929/verification_phase1.log`, `verification_final.log` 참조.')
s=s.replace('중단 전 기록은 execution_pre_version_fix.json, 최신 성공은 execution.json이며 이전 생성증거를 덧칠하지 않았다.','이어 B 종합 표기의 기존 5개 하드코딩을 4기능에 맞게 수정하고, 최종 코드 지문으로 22개를 다시 생성했다. 중단 전 기록은 execution_pre_version_fix.json, 최신 성공은 execution.json이며 이전 생성증거를 덧칠하지 않았다. B 표기 수정 전 독립 2SFCA 대조는 비B 수치 파일 전체 SHA 불변을 independent_reuse_guard.json으로 확인하여 재사용했다.')
s+='\n시설 생산자 후속 정리: 구 v1.3 생성물 5파일/76,782,692 bytes 삭제 및 삭제 후 원천130개 재생성 PASS. 역사 비교·삭제 영수증은 시설 `구축코드/14_체육제외/cleanup_20260929/`에 보존하고 현재 출처 해시에 연결했다. 접근성 이전 정본은 동일 경로에서 검증 후 교체했으며 별도 활성 구판 결과를 추가하지 않았다. 이번 개인 stage 정리 및 과거 거부 대상 잔여는 `검증_v33_20260929/cleanup_ledger.json`을 따른다.\n'
p.write_text(s,encoding='utf8')
p=P/'문서/지표정의_확정.md';s=p.read_text(encoding='utf8')
s=s.replace('시설 점 자체의 동과 격자 중심의 동이 다른 시설은 동 4.7%·생활권 1.7%·구 0.5%.','시설 점 자체의 동과 격자 중심의 동이 다를 수 있다. 현행 시설 배정 진단은 `시설_격자_경계연결_구축기록.md`를 따른다.')
s=s.replace('(격자 중심이 서울 밖인 가장자리 셀, 100 m 연도별 40행)','(격자 중심이 서울 밖인 가장자리 셀 등)')
p.write_text(s,encoding='utf8')
print(json.dumps({'facility_cleanup_verified':5,'private_stage_files':len(stage),'private_stage_bytes':inventory['bytes'],'promotion_files_verified':len(ledger['files'])},ensure_ascii=False))
