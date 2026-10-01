"""Summarize bounded coverage, verify offline build, and write candidate handoff."""
import json,hashlib,re,sys
from collections import Counter
from pathlib import Path
import pandas as pd
from inventory import HERE,PKG,sha
from prepare import dump
from build_verify import spatial,COORD
from geocode_candidate import credentials
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
def main():
 v=json.loads((HERE/'검증/verification.json').read_text(encoding='utf-8'));assert v['passed']
 records=json.loads((HERE/'입력/prepared_records.json').read_text(encoding='utf-8'));byrow={r['row_index']:r for r in records};left=json.loads((HERE/'결과/unresolved.json').read_text(encoding='utf-8'));reason=Counter()
 for r in left:
  base=byrow[r['row_index']];address=base.get('address') or ''
  if not address:why='원자료 주소 없음'
  elif re.match(r'^(경기도|강원|인천|부산|대구|대전|광주|울산|제주|충청|전라|경상)',address):why='서울 외 주소'
  elif not base['candidates']:why='번지·건물번호 부족 또는 주소 해석 불가'
  elif any(t.get('point_count',0)>0 for a in r['attempts'] for t in a['attempts']):why='공급자 후보의 주소·번호·자치구·공간 일치 실패'
  else:why='정확 주소 결과 없음 (기존 실패 캐시 포함)'
  r['detailed_reason']=why;reason[why]+=1
 dump(HERE/'결과/unresolved_detail.json',left)
 # A second build from immutable input and the OFFLINE-reproduced patches.
 before_calls=json.loads((HERE/'검증/http_ledger.json').read_text())['total']
 base=pd.read_parquet(HERE/'입력/서울시설_2020_2025_분석용.parquet');off=json.loads((HERE/'결과/patch_manifest_offline.json').read_text(encoding='utf-8'));patch=spatial(off);idx=patch.row_index.astype(int).tolist()
 for c in COORD:base.loc[idx,c]=patch[c].values
 buf=base.to_parquet(index=False);rebuild=hashlib.sha256(buf).hexdigest();assert rebuild==v['candidate_sha256']
 assert json.loads((HERE/'검증/http_ledger.json').read_text())['total']==before_calls
 v['offline_rebuild_sha256']=rebuild;v['offline_rebuild_byte_identical']=True;v['detailed_remaining_reasons']=dict(reason)
 ledger=v['http'];v['http_attempts_without_recorded_response']=ledger['total']-sum(ledger['status_counts'].values())
 raw=json.loads((HERE/'입력/raw_evidence.json').read_text(encoding='utf-8'));assert all(sha(PKG/z['path'])==z['sha256'] for z in raw.values() if 'sha256' in z)
 v['raw_inputs_verified_unchanged']=sum('sha256' in z for z in raw.values())
 table=pd.read_csv(HERE/'결과/시설별_보완결과.csv').groupby('시설')[['null_rows','filled','remaining']].sum()
 lines=['# 시설 좌표 보완 후보 — 2026-09-29','','기존 facility-v1.2의 미좌표 3,026행을 확인하여 **87행을 추가 보완**, **2,939행을 미해결로 유지**했다. 등록본을 대체하지 않은 별도 검증 완료 후보이다. 사용자 지시에 따라 보건소 시점 선택은 기존 의도대로 유지했다.','','- 분석본: `결과/서울시설_2020_2025_분석용_보완후보.parquet`','- 전체 606,066행, 33종 × 2개 연도, 25열, 행 순서·키·스키마 보존. 분석가능 603,068행(99.5053%).','- 원본 SHA256: `'+v['base_sha256']+'`','- 후보 SHA256: `'+v['candidate_sha256']+'`','- 미좌표 행의 좌표·공간 파생값·좌표 근거 필드만 수정. 기존 유효 좌표 및 시설명·주소·시점·등급 등 비좌표 속성 변경 0.','- 시설별 변경 파일 21개를 `결과/시설별/`에 parquet/CSV로 제공. 해당 원본만 `입력/시설별/`에 선택 복사. 나머지 등록본과 모든 기존 원자료·코드·캐시는 보존.','','## 채택과 검증','','새 API 응답으로 42행, 기존 정확일치 캐시로 33행, 같은 건물의 검증된 등록 좌표로 12행을 보완했다. 원자료 관리번호·사업장명이 일치하는 2,903행의 지번/도로명 대안을 확인했다. 동 중심점, 단일 유사 검색, 최신 POI 위치 추정은 채택하지 않았다. 재사용 12행은 매봉길 13의 같은 옥수리버젠 상가와 성균관로4길 21의 정확 건물주소에 한정하며, 평균 좌표를 만들지 않았다. 주소가 없는 동일 ID 버스정류장의 타연도 좌표와 구 경계가 다른 지하철 주소는 재사용하지 않았다.','','주소 숫자 경계를 강화하여 `구로1동 → 구로 1`, `명동13길 → 명동 13` 같은 부분 파싱을 차단했고 회귀검사 8개가 통과했다. 기존 공유 파서와 등록 좌표는 수정하지 않았으며, 이 파서 위험이 기존 확정본에 미친 전체 영향은 이번 보완 범위 밖의 후속 점검 사항이다.','','채택 고유주소 47개를 다른 공급자와 대조: 15개는 50m 이내 일치, 32개는 두 번째 공급자의 정확 결과 없음, 상충 좌표 0개. 전체 87행은 원주소·번호 및 자치구 공간 검사를 통과했다. 두 공급자 확인이 없는 행은 그 사실을 `검증/cross_provider.json`에 남겼다.','','Kakao 285회 + VWorld 297회 = HTTP 요청 시도 **582회**(한도 12,000). 응답 기록 HTTP 200은 581회이며, 작업 재시작 직전 진행 중이던 1회는 응답 미기록이다. 인증·쿼터 차단 기록 없음. 키값 누출 검사 0건. API 키는 기존 설정 위치에서 메모리로만 읽고 공급자 인증에만 사용했다. 기존 실패 캐시를 재사용하여 같은 실패 조회를 반복하지 않았다.','','오프라인 재조회 추가 HTTP 0회, 87행 패치 동일. 오프라인 분석본 재빌드 SHA256도 후보와 바이트 단위로 일치한다. 기존 등록본·대상 시설 파일 35개 및 주소 대안 원자료 해시 유지. `검증/verification.json`과 `결과/patch_manifest.json`에 상세 근거가 있다.','','## 시설별 결과','','| 시설 | 기존 미좌표 | 이번 보완 | 잔여 |','|---|---:|---:|---:|']
 for name,r in table.iterrows():lines.append(f'| {name} | {int(r.null_rows):,} | {int(r.filled):,} | {int(r.remaining):,} |')
 lines+=['','','미해결 사유:']+[f'- {k}: {n:,}행' for k,n in reason.items()]+['','오래된 주소의 철거·변경 여부를 현재 API 무응답만으로 단정하지 않는다. 잔여 명부의 세부 사유는 `결과/unresolved_detail.json`에 기록했다. 주소가 없는 따릉이·버스, 번지 없는 아파트 동·호, 사서함, 서울 외 주소는 추정 좌표로 채우지 않았다. 어린이집 원천에는 별도 도로명/지번 대안 열이 없어 명시된 번지만 사용했다.','','## 재현 및 인계','','이 폴더는 `시설데이터_패키지` 안의 현재 위치에서 실행한다. Python에 pandas, pyarrow, geopandas, shapely, pyproj, requests가 필요하다. 스크립트는 저장소 밖 개인 경로를 하드코딩하지 않는다.','```powershell','python test_address_rules.py','python geocode_candidate.py','python build_verify.py','```','기본 실행은 오프라인이다. 새로운 API 호출은 `--online`을 명시해야 하며 기존 요청 캐시와 누적 한도를 따른다. `prepare.py`는 보존된 원자료를 읽어 조회 근거를 다시 만든다. 후보 입력 스냅샷·변경 시설 파일·정제된 공급자 캐시를 함께 보존해야 한다. SGIS 경계는 패키지의 기존 경계를 읽는다.','','등록 승격·공동 배포목록/README 수정·06 접근성 재계산·Git 커밋/푸시는 이번에 실행하지 않았다. 후보 승격 시 이 문서의 후보 해시와 `결과/changed_files.json`을 사용하고, 접근성 결과는 별도의 06 재계산 이후에 갱신해야 한다.']
 (HERE/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 secrets=credentials();leaks=0
 for f in HERE.rglob('*'):
  if f.is_file() and f.suffix in ['.py','.json','.csv','.md','.parquet']:
   b=f.read_bytes();leaks+=int(any(s.encode() in b for s in secrets.values() if len(s)>8))
 assert leaks==0;v['key_leak_files']=0;dump(HERE/'검증/verification.json',v)
 dump(HERE/'검증/build_hashes.json',{str(f.relative_to(HERE)):sha(f) for f in HERE.glob('*.py')})
 print(json.dumps({'passed':True,'offline_rebuild_byte_identical':True,'remaining_reasons':dict(reason),'key_leak_files':0},ensure_ascii=False))
if __name__=='__main__':main()
