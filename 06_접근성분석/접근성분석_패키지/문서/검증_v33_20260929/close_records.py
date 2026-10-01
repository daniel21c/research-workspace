from pathlib import Path
import json,shutil,datetime
S=Path(__file__).resolve().parent;R=Path('D:/Research/00_박사논문_연구체계');P=R/'06_접근성분석/접근성분석_패키지';Z=P/'문서/검증_v33_20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
receipt=read(S/'private_stage_delete_receipt.json');assert receipt['status']=='deleted' and not Path(receipt['target']).exists()
c=read(Z/'cleanup_ledger.json');c.update(status='current_release_cleanup_complete_prior_denied_targets_retained',private_stage_cleanup='deleted after complete duplicate hash, resolved containment and reparse checks',private_stage_deleted_files=receipt['file_count'],private_stage_deleted_bytes=receipt['bytes'],private_stage_deletion_receipt='private_stage_delete_receipt.json',additional_canonical_obsolete_files_deleted=0)
write(Z/'cleanup_ledger.json',c)
for name in ['private_stage_delete_preflight.json','private_stage_delete_receipt.json','delete_private_stage.ps1','finish_records.py','close_records.py','finalize.py']:
 shutil.copy2(S/name,Z/name)
p=P/'문서/지표정의_확정.md';s=p.read_text(encoding='utf8').replace('시설_격자_경계연결_구축기록.md','시설경계연결_구축기록.md');p.write_text(s,encoding='utf8')
p=P/'문서/공동연구자_시작_20260929.md';s=p.read_text(encoding='utf8')
old='패키지는 입력격자·망·TTM을 포함한다. 저장소 내부 원천 시설/선택규칙과 코어 경계도 상대 위치로 제공해야 전체 재실행된다. 메타 확인과 hash 확인만은 `python 코드/a10_verify.py --metadata-only`, `python 코드/a10_verify.py --check-only`. 재계산은 `a02_facility_boundary.py` → `run_engine.bat` → `a06d_temporal_sensitivity.py` → `a06b_summary.py` → `a07_study3_outputs.py` → `a08_ku_compare.py`; 이번 정확한22명령은 `검증_v33_20260929/execution.json`, 검증은 같은 폴더 verify.py를 참조한다. 외부 scratch에서 재현할 때만 ACCESS_REPOSITORY_ROOT를 연구저장소 루트로 지정한다. 코드/입력이 달라지면 metadata-only가 stale을 검출한다.'
new='''패키지는 입력격자·망·TTM을 포함한다. 저장소 내부 원천 시설/선택규칙과 코어 경계도 상대 위치로 제공해야 전체 재실행된다. 패키지 루트에서 현재 파일 확인은 `python -B -X utf8 코드/a10_verify.py --check-only`, 현재 메타/출력/코드/원천 지문 확인은 `python -B -X utf8 코드/a10_verify.py --metadata-only`다. 메타 검사는 시설 원천과 선택규칙의 저장소 참조도 필요하다. 외부 작업 사본에서는 ACCESS_REPOSITORY_ROOT를 연구저장소 루트로 지정한다.

재생성은 작업 사본에서 `코드/run_engine.bat facility`를 실행한다. a02 시설연결 → 22설정 → 공통4 → 요약 → 연구3표/그림 → 구비교 → a10 검증까지 포함하므로 하위 요약 명령을 다시 이어 실행할 필요는 없다. 현재35시험을 별도로 실행하려면 `python -B -X utf8 코드/tests/test_engine.py`, `test_release.py`, `test_geometry.py`를 같은 tests 경로로 실행한다. 기존 수치에 대한 현행 검사·독립 대조·민감도 보고 재생성은 `python -B -X utf8 코드/a10_verify.py --skip-rerun`이다. 마지막 명령은 검증보고서/검증결과/manifest를 갱신하므로 작업 사본에서 사용한다.

이번 실제 실행 명령과 환경은 `검증_v33_20260929/execution.json` 및 release_provenance.json에 있다. execution.json의 개인 Python/stage 절대경로는 당시 기록이다. 현재 재현 시 Python 실행파일과 패키지 경로를 자신의 환경으로 바꾸고 나머지 옵션을 유지한다. `검증_v33_20260929/verify.py`는 삭제 전 구 v3.2와 당시 stage를 비교한 역사 실행 스크립트로 보존한 것이며 현재 재현 진입점이 아니다. 그 전후 비교는 보존된 `verification_summary.json`, 로그, `facility_comparison.json`, `baseline.json` 및 replacement ledger로 확인한다. 구 비교 입력 삭제 후 비교를 새로 수행했다고 주장하지 않는다. 코드/입력이 달라지면 metadata-only가 stale을 검출한다.'''
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8')
(Z/'README.md').write_text('''# v3.3 검증 증거 읽기

현재 최종 상태: final_verification.json, cleanup_ledger.json. 수치 검증: verification_summary.json, verification_final.log, execution.json 및 tests 로그. 원천과 비체육 항목 불변 비교: facility_comparison.json, output_comparison.json(파일명은 실제 목록 참조), grid_comparison.json 및 보존된 로그.

이 폴더의 verify.py, prepare.py, run_all.py 등은 당시 실행된 스크립트/작업 사본의 기록이다. 기록 안의 개인 stage 절대경로와 구 v3.2 정본은 현재 재실행 입력으로 제공하지 않는다. 현재 검사는 패키지 코드/a10_verify.py의 --check-only, --metadata-only, --skip-rerun을 사용하며, 전체 재생성은 코드/run_engine.bat facility를 작업 사본에서 실행한다. 구판과의 전행 비교는 이미 실행된 역사 증거이며 삭제 후 다시 관측한 것으로 해석하지 않는다.

이전_v32는 이전 코드·메타·출처·검증 이력이며 활성 수치 정본이 아니다. 이번 개인 stage는 duplicate hash 검사 후 제거했고 로그와 실행 스크립트는 보존했다. 과거 자동정책이 거부한 v3.2 stage/캐시는 삭제/이동 재시도 없이 그대로 두었으며 공유 대상에서 제외한다.
''',encoding='utf8')
p=P/'문서/작업기록.md';s=p.read_text(encoding='utf8');s+='\n최종 완료: 시설 producer의 구 v1.3 생성5파일/76,782,692 bytes 삭제 및 삭제 후130원천 재생성 PASS를 출처에 연결. 접근성 정본135파일 교체·103파일 추가(초기 promotion ledger 기준), 이번 개인 stage1,422파일/639,022,034 bytes는 정본과 동일 SHA·경계·reparse 검증 후 삭제. 이후 문서/출처/최종검증 추가·정정은 final manifest에 기록. 과거 거부된 v3.2 stage와6캐시는 미접촉. 역사 비교 스크립트와 현재 재현 명령을 분리했고 모든 원자료·증거·로그는 보존. 최종 수치 반복 없이 현재22메타·입력/코드지문·manifest 점검으로 확정.\n';p.write_text(s,encoding='utf8')
print('records closed; private stage deleted:',receipt['file_count'],receipt['bytes'])
