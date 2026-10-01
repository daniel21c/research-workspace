"""Update only facility-owned documents and the facility rows of the registry."""
import json,re,sys,hashlib
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent;PKG=HERE.parent.parent;ROOT=PKG.parent.parent
sys.stdout.reconfigure(encoding='utf-8')
v=json.loads((HERE/'stage_verification.json').read_text(encoding='utf-8'));h=v['sha256'];oldhash=v['baseline_sha256']
a=pd.read_parquet(PKG/'데이터/서울시설_2020_2025_분석용.parquet')
def edit(rel,text):
 p=PKG/rel
 if p.exists():
  snap=HERE/'이전문서'/rel;snap.parent.mkdir(parents=True,exist_ok=True)
  if not snap.exists():snap.write_bytes(p.read_bytes())
 p.write_text(text,encoding='utf-8')
p=PKG/'README.md';text=p.read_text(encoding='utf-8')
text=text.replace('(facility-v1.2)','(facility-v1.3)',1).replace(oldhash,h).replace('(배포목록 `facility-v1.2`)','(배포목록 `facility-v1.3`)')
text=text.replace('99.49% (서울 안 좌표 + 검증)','603,066행 / 99.5050% (서울 안 좌표 + 검증), 미좌표 2,941행')
text=text.replace('PASS (33종 두 시점, 기본값 좌표 0, 시설·시점·자치구 분석가능 85% 미만 0, 빌드 재실행 해시 일치)','PASS (33종 두 시점·행/키/스키마 보존, 87행 보완·4행 교정·2행 좌표 제외; 상세 `구축코드/13_좌표보완/`)')
text=text.replace('**다른 연구 코드는 이 패키지의 `데이터/`만 참조한다.**','**현재 시설 배포본은 v1.3이다. 다른 연구 코드는 이 패키지의 `데이터/`만 참조한다.**\n\n06의 기존 access-engine-v3.1 결과는 v1.2 입력으로 계산되었다. v1.3 시설을 반영한 결과가 아니며, 06 담당자가 연결표·입력 버전 검사·출처 지문·결과를 갱신해야 한다. 이번 작업에서는 06을 수정하거나 재계산하지 않았다.')
for fac,g in a.groupby('시설'):
 vals={int(y):float(z['분석가능'].mean()*100) for y,z in g.groupby('year')}
 pattern=r'(^\| '+re.escape(fac)+r' \| [^\n]*? \| [^\n]*? \| )[^\n]*?( \|$)'
 text=re.sub(pattern,lambda m:m.group(1)+f'{vals[2020]:.1f} / {vals[2025]:.1f}'+m.group(2),text,flags=re.M)
text=text.replace('일상소매 = 2020이 2025-11 재작성본(수준 약 10% 과소)','일상소매 = 2020이 2025-11 재작성본(2019 원배포본 미확보; 과소 규모·지역별 편향은 확정할 수 없음)')
start=text.index('## 5. 다시 만들기');end=text.index('## 6. 변경 이력')
text=text[:start]+'''## 5. 다시 만들기 (`구축코드/`)

현재 채택본의 통합·분석용 파일을 **별도 검증 폴더**에 다시 만들어 바이트 해시를 비교한다(API·키 읽기 없음).
```powershell
python 구축코드/13_좌표보완/release_v13.py verify
```
v1.2 입력 스냅샷 + 87행 보완 근거 + 6행 파서 정정 근거에서 v1.3을 다시 생성하려면 `python 구축코드/13_좌표보완/release_v13.py stage`를 사용한다. `staging/`에만 생성하며 공식 배포본을 덮어쓰지 않는다. 필요한 환경: Python 3.12, pandas 3.0.2, pyarrow 23.0.1, geopandas, pyproj. 과거 보정 스크립트는 당시 구축 이력이며 현재 배포본 위에 무조건 다시 실행하지 않는다.

원자료·기존 캐시·SGIS·원천 산출물과 `보완후보_20260929/입력/` 스냅샷은 재현에 필요하므로 보존했다. 기존 87행 후보의 생성·검증 기록은 당시 v1.2가 활성 입력이었던 증거이며, 승격 후 재현은 위 v1.3 스크립트를 쓴다. 공원 PBF는 본33종 입력이 아닌 06 네트워크의 별도 원자료 의존성이고, 이번 범위에서 재현하지 않았다.

'''+text[end:]
text += f'\n| facility-v1.3 | 2026-09-29 | 미좌표 87행 추가, 기존 오좌표 4행 정정·2행 분석 제외. 606,066행 유지, 미좌표 2,941행. SHA-256 `{h}` |\n\n이전 v1.2의 교체 대상 55개 생성 파일(556,290,819바이트)은 `D:/Research/_archive/facility-v1.2_superseded_20260929/`로 이동했다. 활성 경로에는 v1.3만 두었으며 영구 삭제는 하지 않았다. 검증·정정 근거·복구 목록: `구축코드/13_좌표보완/README.md`.\n'
edit('README.md',text)
p=PKG/'문서/분석용파일_설명.md';text=p.read_text(encoding='utf-8')
start=text.index('## 기본 사용');text=text[start:]
text=text.replace("`D:\\Research\\00_박사논문_연구체계\\시설데이터 구축\\SGIS_인구경계_2019_2024\\`","`../SGIS_인구경계_2019_2024/`")
text=text.replace('2020 = 2019-12-31, 2025 = 2024-12-31','목표 기준일 2020 = 2019-12-31, 2025 = 2024-12-31. 실제 원천 기준일·예외는 source_reference_date 및 출처 안내 참조')
text=text.replace('일상소매 2020은 상가정보 재작성본(서울 전체 약 −10% 수준 편향)','일상소매 2020은 2025-11 상가정보 재작성본(2019 원배포본 미확보, 과소 규모·지역별 편향 미확정)')
text=text.replace('`../10_신뢰도_상/_중/공공체육_핵심종목/`','`../데이터/민감도용/공공체육_핵심종목/`')
header=f'''# 서울시설_2020_2025_분석용.parquet — facility-v1.3 (2026-09-29)

현재 경로는 `../데이터/서울시설_2020_2025_분석용.parquet`이며 SHA-256은 `{h}`이다. 606,066행·25열, 33종×2시점(2020 295,632 / 2025 310,434)을 유지했다. 분석가능 603,066행(99.5050%), 미좌표 2,941행이다. 규모 변수는 `../데이터/시설별/`에 있다.

v1.2 대비 미좌표 87행을 보완하고, 주소 일부를 잘못 해석한 기존 좌표 4행을 교정했다. 완전주소 근거가 부족한 2행은 행을 유지하면서 좌표·공간키를 비워 분석 제외했다. 비좌표 속성·기타 행·키·순서는 보존했다. 근거와 오프라인 재현: `../구축코드/13_좌표보완/README.md`. 33종 출처·시점·채택 조건: `출처_전처리_안내.md`.

공간 접근성 분석에 조건부 사용할 수 있다. `분석가능=True`를 적용하고 소매 제외 민감도·시점 제한을 보고해야 한다. 보건소의 2025-12-31 원천 선택은 사용자 의도대로 유지했다. 모든 시설의 완전한 과거 전수조사나 인과효과 자료로 해석하지 않는다. 06 기존 결과는 v1.2로 계산되어 별도 갱신이 필요하다.

'''
edit('문서/분석용파일_설명.md',header+text)
p=PKG/'문서/출처_전처리_안내.md';text=p.read_text(encoding='utf-8')
text=text.replace('작성 2026-09-25 · 대상 자료 **facility-v1.2**','갱신 2026-09-29 · 대상 자료 **facility-v1.3**').replace(oldhash,h)
text=text.replace('전체 99.49%','603,066 / 606,066행(99.5050%)')
text=text.replace('2020은 수준 약 10% 과소 → 민감도는 인허가 식료품','2020 원배포본 미확보·2025-11 재작성. 과소 규모·지역 편향 미확정 → 소매 제외·인허가 식료품 민감도')
text=text.replace('일상소매 2020은 재작성본이라 수준이 약 10% 낮다(지역 편중은 없음). 원 배포본(정보공개청구)을 받으면 교체한다.','일상소매 2020은 2025-11 재작성본이며 2019 원배포본을 확보하지 못했다. 기존 약10% 차이 관찰만으로 정확한 과소율이나 지역 편향 부재를 확정할 수 없다. 동별 증감의 단정은 피하고 소매 제외·인허가 식료품 민감도를 함께 제시한다. 원배포본 확보 후 별도 대조가 필요하다.')
text=text.replace('(저장소 최상위, facility-v1.2)','(저장소 최상위, facility-v1.3)')
text=text.replace('도로명+건물번호 또는 지번 번지가 정확히 일치한 결과만','도로명+건물번호 또는 지번 번지 일치를 요구한 결과만')
note='''
## 2026-09-29 v1.3 정정 및 사용 한계

- 미좌표 87행 보완, 잘린 주소에 배정된 기존 좌표 4행 교정·2행 제외. 상세 `구축코드/13_좌표보완/README.md`, 현재 시설별 좌표율은 `데이터/채택목록.csv`가 기준이다. 위 시설별 설명표의 반올림 좌표율은 v1.2 당시 이력값이다.
- 과거 `mb.py`의 정확일치 표시는 파서가 잘라낸 검색문에 대한 일치일 수 있었다. 관련 기존 29,032행을 비교해 1,295행을 추렸고 1,234행은 완전주소 캐시 좌표 일치, 6행은 이번 정정, 55행은 접미 건물명·별도 주소 처리 경로 등으로 유지했다. 유지 55행을 모두 새로운 원자료/API로 재확인한 것은 아니다.
- 현재 시점 주소 지오코딩은 당시 시설의 실제 운영 여부나 이전 이력을 새로 입증하지 않는다. 보건소 원천시점(+12개월), 주유소 현재 휴업 제외·체육시설업 현재 취소/말소 제외는 기존 사용자 채택 규칙을 유지했다.
- 06 접근성 분석의 현재 결과·연결표·출처 지문은 v1.2 입력 기준이다. 이번 v1.3을 반영한 분석값으로 쓰려면 06 담당 재계산과 검증이 필요하다.
'''
edit('문서/출처_전처리_안내.md',text+note)
p=PKG/'문서/무결성_검증.md';text=p.read_text(encoding='utf-8');edit('문서/무결성_검증.md','> 현재 정본은 facility-v1.3(2026-09-29)이다. 이 문서는 v1.1/v1.2 당시 검증 이력이며, 이번 87행 보완·4행 교정·2행 좌표 제외 및 현재 해시는 `../구축코드/13_좌표보완/README.md`와 `../데이터/검증결과.json`을 참조한다.\n\n'+text)
p=PKG/'문서/작업기록.md';text=p.read_text(encoding='utf-8');text+=f'''
## 2026-09-29 — facility-v1.3 공식 교체와 이전 생성 파일 보관 (Codex)

- 사용자 요청 '이걸로 쓴다면 기존꺼 삭제'에 따라 87행 보완 후보에 기존 오좌표 6행 정정(4행 정확주소 캐시 교정·2행 좌표 제외)을 더해 공식 배포본으로 교체했다. 606,066행·25열·33종×2시점 유지, 미좌표 2,941행, 분석가능 603,066행(99.5050%). SHA-256 `{h}`.
- 시설별25개 parquet+CSV와 통합·분석·요약·채택·검증까지 55개를 일관되게 교체했다. 비좌표 속성·비대상행·스키마·키·순서 보존. 새 API 요청0. 과거 원자료·캐시·87행 후보·입력 스냅샷 보존.
- 구55개 생성 파일(556,290,819바이트)은 `D:/Research/_archive/facility-v1.2_superseded_20260929/`로 이동, 이동 전후 SHA256 확인. 영구삭제0. 활성 경로에는 새 판만 남겼다. 상세 `../구축코드/13_좌표보완/archive_result.json`.
- 배포목록은 시설 v1.2 대체 표시와 v1.3 행만 갱신. 다른 대화 편집·Git·06/AG/KPA·허브 README/연구설계는 수정하지 않았다. 허브 문서 v1.2 표기와 06의 v1.2 하드코딩 검사·연결표·출처지문·결과 갱신을 담당자에게 인계한다.
- 조건부 사용: 분석가능 필터, 소매 제외 등 민감도, 원천 시점 한계 명시. 보건소 원천시점과 주유소 제외 규칙은 사용자 의도 유지. 새 검증·재현은 `../구축코드/13_좌표보완/README.md`.
''';edit('문서/작업기록.md',text)
# Only the two facility registry lines are changed. Preserve concurrent unrelated entries.
registry=ROOT/'데이터_배포목록.md';before=registry.read_text(encoding='utf-8');lines=before.splitlines(keepends=True)
index=next(i for i,l in enumerate(lines) if l.startswith('| facility-v1.2 |'))
oldline=lines[index];assert oldhash in oldline and '**확정**' in oldline
cells=oldline.rstrip('\r\n').split('|')
cells[3]=' `../_archive/facility-v1.2_superseded_20260929/데이터/서울시설_2020_2025_분석용.parquet` (이전 정본 보관; 복구 목록 `시설데이터 구축/시설데이터_패키지/구축코드/13_좌표보완/archive_result.json`) '
cells[-2]=' **대체됨** (2026-09-29 → facility-v1.3). 입력 해시는 보존. 기존 access-engine-v3.1 결과는 여전히 이 v1.2 기준이며 v1.3 반영 재계산은 미실행. '
lines[index]='|'.join(cells)+'\n'
newline=f'| facility-v1.3 | 서울 시설33종 2020/2025. v1.2 + 미좌표87행 보완·오좌표4행 교정·근거부족2행 좌표 제외. 분석가능603,066행(99.5050%), 미좌표2,941행 | `시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet` (606,066행·25열); 근거·재현 `구축코드/13_좌표보완/README.md` | 2026-09-29 (원천 시점 규칙·보건소 예외 유지) | {h} | 시설데이터 구축 대화 | **확정** (공간분석 조건부 사용: 분석가능 필터·소매 제외 민감도·시점 한계 명시). 구55개 생성파일 archive 이동·SHA 확인. 06 기존 결과는 v1.2 입력으로, v1.3 연결표/결과/출처지문 갱신 필요. |\n'
lines.insert(index+1,newline);after=''.join(lines)
assert [l for l in before.splitlines() if not l.startswith('| facility-v1.2 |')]==[l for l in after.splitlines() if not l.startswith(('| facility-v1.2 |','| facility-v1.3 |'))]
assert registry.read_text(encoding='utf-8')==before,'registry concurrent change; reread before editing'
snapshot=HERE/'이전문서/데이터_배포목록_施設行.json';snapshot.parent.mkdir(exist_ok=True,parents=True);snapshot.write_text(json.dumps({'previous_v12_line':oldline,'new_v12_line':lines[index],'new_v13_line':newline,'unrelated_lines_preserved':True},ensure_ascii=False,indent=2),encoding='utf-8')
registry.write_text(after,encoding='utf-8')
print(json.dumps({'updated_facility_documents':5,'registry_unrelated_lines_preserved':True,'sha256':h}))
