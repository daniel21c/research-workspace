"""One-time scoped v1.4 documentation/registry handoff after verified promotion."""
from pathlib import Path
import json
import hashlib
from release_v14 import HERE, BUILD, PKG, DATA, read_json, write_json, sha

ROOT = PKG.parent.parent
result = read_json(HERE / 'final_verification.json')
assert result['PASS'] and result['offline_rebuild_hashes_exact']
digest = result['sha256']
rate = f"{result['analysis_ready_pct']:.4f}"
old_digest = result['baseline_sha256']
archive = read_json(HERE / 'archive_result.json')
archive_root = str(Path(archive['files'][0]['archive']).parent.parent)
changes = {}


def change(path, transform):
    text = path.read_text(encoding='utf-8-sig')
    after = transform(text)
    assert text != after, f'No update: {path}'
    changes[path] = (text, after)


def package_readme(text):
    text = text.replace('(facility-v1.3)', '(facility-v1.4)', 1)
    text = text.replace('서울 33종 시설의 두 시점', '서울 32종 시설의 두 시점', 1)
    text = text.replace('현재 시설 배포본은 v1.3이다.', '현재 시설 배포본은 v1.4이다. 체육시설업 두 시점만 제외했으며 다른 시설 값은 v1.3과 같다.', 1)
    text = text.replace('06의 기존 access-engine-v3.1 결과는 v1.2 입력으로 계산되었다. v1.3 시설을 반영한 결과가 아니며, 06 담당자가 연결표·입력 버전 검사·출처 지문·결과를 갱신해야 한다. 이번 작업에서는 06을 수정하거나 재계산하지 않았다.',
        '06의 현 access-engine-v3.2는 facility-v1.3(33종·8카테고리) 결과다. v1.4는 32종(본분석 27종+통제5종)·7카테고리이며, 06 담당자의 카테고리·연결표·출처 지문·결과 갱신 및 재계산이 필요하다. 이번 작업에서는 06을 수정하거나 실행하지 않았다.')
    text = text.replace('606,066 (2020 295,632 / 2025 310,434), 33종 × 2시점', '584,766 (2020 285,339 / 2025 299,427), 32종 × 2시점')
    text = text.replace(f'`{old_digest}` (배포목록 `facility-v1.3`)', f'`{digest}` (배포목록 `facility-v1.4`)')
    text = text.replace('603,066행 / 99.5050% (서울 안 좌표 + 검증), 미좌표 2,941행', f'581,888행 / {rate}% (서울 안 좌표 + 검증), 미좌표 2,821행')
    text = text.replace('PASS (33종 두 시점·행/키/스키마 보존, 87행 보완·4행 교정·2행 좌표 제외; 상세 `구축코드/13_좌표보완/`)',
        'PASS (v1.3에서 체육시설업만 제외, 나머지 값·키·스키마·순서 완전 일치; 상세 `구축코드/14_체육제외/`)')
    text = text.replace('33종 × 2시점 단일 파일', '32종 × 2시점 단일 파일')
    text = text.replace('시설별 채택본(규모 변수 sz_*, 원천 속성 열 포함) 32종', '활성 31종 + 제외 체육1종 이력 보존(선택규칙으로 분리)')
    text = text.replace('시설별 32종의 공통 20열 통합본', '활성 시설별 31종의 공통 20열 통합본')
    text = text.replace('— 33종 각각의 출처', '— 활성32종 및 제외 체육 이력의 출처')
    text = text.replace('## 3. 33종 ', '## 3. 활성 32종 ')
    text = '\n'.join(line for line in text.split('\n') if not line.startswith('| 체육시설업 |'))
    text = text.replace('조건부: 체육시설업 = 현재 취소·말소 상태 행 제외, 주유소 =', '조건부: 주유소 =')
    text = text.replace('2019 원배포본 미확보; 과소 규모', '2019 원배포본 요청 중·미입수; 과소 규모')
    start = text.index('현재 채택본의 통합·분석용 파일을')
    end = text.index('## 6. 변경 이력')
    text = text[:start] + '''현재 채택본에서 `구축코드/시설_선택규칙.json`에 따라 통합·분석용 파일을 별도 검증 폴더로 재생성한다(API·키 읽기 없음).
```powershell
python 구축코드/14_체육제외/release_v14.py verify
```
검증은 채택 입력130파일 SHA 보존, 보관 v1.3의 정확한 체육 제외값, 재빌드 해시를 확인한다. 필요한 환경: Python 3.12, pandas 3.0.2, pyarrow 23.0.1, numpy. 일반 빌드 `build_통합.py`·`build_분석용.py`도 같은 선택규칙을 사용한다.

`데이터/시설별/체육시설업_조건부/`는 이전 채택의 증거로만 보존한다. 원자료·캐시·SGIS·보정 근거·이전 코드와 입력 스냅샷은 삭제하지 않았다. v1.3 및 그 이전의 검증기는 당시 배포판용이며 현 v1.4 위에서 실행하지 않는다. 공공체육 민감도 자료는 본32종에 추가하지 않았다.

''' + text[end:]
    text += f'''
| facility-v1.4 | 2026-09-29 | 체육시설업2020 10,293행·2025 11,007행 제외 → 584,766행·32종. 나머지 모든 값 불변. SHA-256 `{digest}` |

현재 취소·말소 상태를 과거 기준일에도 적용한 선택 문제 때문에 체육시설업 전체를 제외했다. 기존 필터에서 제외됐던 후보 수는 실제 누락 시설 수나 결과 영향으로 해석하지 않는다. 공공시설의 명부 날짜는 사용자가 수용한 인접시점 대리 가정이며, 정확한 과거 운영 검증이 아니다. 소매 과거 원본은 요청 중이고 미입수이므로 소매는 그대로 유지했다.

v1.3 생성파일5개는 `{archive_root}/`에 해시 확인 후 보관했다. 활성 경로에는 v1.4만 있다. 접근성 재계산·검증 완료 전에는 이전 v1.3 비교 입력을 삭제하지 않는다. 위치·해시·후속 정리 조건은 `구축코드/14_체육제외/deferred_cleanup_manifest.json`, 상세는 같은 폴더 `README.md` 참조. 영구삭제0건.
'''
    # Keep the new history entry inside the version table.
    row = next(line for line in text.splitlines() if line.startswith('| facility-v1.4 |'))
    text = text.replace('\n' + row, '')
    old_row = next(line for line in text.splitlines() if line.startswith('| facility-v1.3 |'))
    return text.replace(old_row, old_row + '\n' + row)


change(PKG / 'README.md', package_readme)


def description(text):
    end = text.index('## 기본 사용')
    head = f'''# 서울시설_2020_2025_분석용.parquet — facility-v1.4 (2026-09-29)

현재 경로 `../데이터/서울시설_2020_2025_분석용.parquet`, SHA-256 `{digest}`. 584,766행·25열, 32종×2시점(2020 285,339 / 2025 299,427), 분석가능581,888행({rate}%), 미좌표2,821행이다.

v1.3의 정확한 시설명 `체육시설업`만 두 시점에서 제외했다(10,293 / 11,007행). 다른 시설의 모든 속성·좌표·순서는 그대로이며, 이전 좌표 정정도 유지된다. 본분석27종+통제5종, 기능 카테고리7개다. 공공체육은 대체 투입하지 않았다. 명시적 선택규칙과 검증은 `../구축코드/14_체육제외/README.md` 참조.

`분석가능=True`로 공간분석에 사용하고 소매 제외 민감도·시점 가정을 명시한다. 소매2019 원배포본은 요청 중·미입수다. 보건소 등 공공시설 명부는 인접시점 대리 가정으로 수용되었으며 정확한 과거 운영 검증이 아니다. 06 현v3.2는 시설v1.3·8카테고리 결과이므로 별도 재계산 전에는 v1.4 결과로 쓰지 않는다.

'''
    text = head + text[end:]
    text = text.replace('33개 시설명', '32개 시설명')
    text = text.replace('조건부 상(체육시설업: 현재 취소·말소 상태 제외 규칙, 주유소:', '조건부 상(주유소:')
    text = text.replace(', 생활체육(체력단련·체육도장·수영장·종합체육) 4,958/6,814', '')
    text = text.replace('학교 중·고, 당구장·골프연습장, 음식점', '학교 중·고, 음식점')
    return text


change(PKG / '문서/분석용파일_설명.md', description)


def source_doc(text):
    text = text.replace('대상 자료 **facility-v1.3**', '대상 자료 **facility-v1.4**', 1)
    text = text.replace(f'(33종 × 2시점, 606,066행, SHA-256 `{old_digest}`)', f'(32종 × 2시점, 584,766행, SHA-256 `{digest}`)', 1)
    text = text.replace("판정 '상' 32종의 채택본", "활성31종의 채택본 + 제외 체육1종의 이력 보존")
    text = text.replace('32종 + 일상소매(', '선택규칙 적용31종 + 일상소매(')
    text = text.replace('603,066 / 606,066행(99.5050%)', f'581,888 / 584,766행({rate}%)')
    text = text.replace('## 3. 시설별 출처와 전처리 (33종)', '## 3. 시설별 출처와 전처리 (활성32종 + 제외 체육 이력)')
    text = text.replace('| 체육시설업(조건부) |', '| 체육시설업(**v1.4 제외, 이전판 이력**) |')
    text = text.replace('규칙 C: 현재 취소·말소 상태 행 제외', '이전 규칙 C: 현재 취소·말소 상태 행 제외; v1.4는 유형 전체 제외')
    text = text.replace('기능 카테고리 8개·국가 최저기준 5개 구성은', '기존 v1.3의 기능 카테고리8개·국가 최저기준 구성은')
    text = text.replace('2절이 유일한 정의다.', '2절에 정의되어 있다. v1.4에서는 체육 유형 전체를 제외해 기능 카테고리가7개가 되므로 06 담당자의 정의·결과 갱신이 필요하다.')
    start = text.index('패키지 첫 문서 `../README.md` 5절의 순서를 따른다')
    end = text.index('## 6. 논문에 적을 한계')
    text = text[:start] + '''현재 배포판 재현은 `python 구축코드/14_체육제외/release_v14.py verify`이며 API·키를 읽지 않는다. 두 빌드는 같은 `시설_선택규칙.json`으로 체육을 제외한다. 채택목록은 활성31종·소매와 기존 공공체육 민감도 이력을 포함하며, 민감도 행은 본분석에 넣지 않는다. 원 빌드·11승격·12/13보정은 역사적 구축 근거로 보존한다.

''' + text[end:]
    text = text.replace('폐업 입력 지연, 일괄 직권말소 → 체육시설업 규칙 C', '폐업 입력 지연·종료일 결측시 최종수정일 대체 등 근사; 체육시설업은 v1.4에서 제외')
    text = text.replace('2019 원배포본을 확보하지 못했다.', '2019 원배포본은 요청 중이며 아직 입수하지 못했다.')
    text = text.replace('조건부 규칙: 체육시설업(현재 취소·말소 제외), 주유소(현재 휴업 제외).', '조건부 규칙: 주유소 현재 휴업 제외 유지. 체육시설업 현재 상태 필터 문제는 그 유형 전체를 제외하는 v1.4 선택으로 처리했다.')
    text = text.replace('(저장소 최상위, facility-v1.3)', '(저장소 최상위, facility-v1.4)')
    text = text.replace('## 2026-09-29 v1.3 정정 및 사용 한계', '## 2026-09-29 v1.3 정정 이력 (현재 선택은 v1.4)')
    text = text.replace('06 접근성 분석의 현재 결과·연결표·출처 지문은 v1.2 입력 기준이다. 이번 v1.3을 반영한 분석값으로 쓰려면 06 담당 재계산과 검증이 필요하다.', '당시06은 v1.2였고 이후v3.2가 v1.3을 반영했다. 현v1.4(32종·7카테고리)는 아직06에 반영되지 않았다.')
    return text + '''
## 2026-09-29 v1.4 선택 및 시점 가정

체육시설업만2020·2025에서 제외하며 다른 유형·소매·좌표값은 불변이다. 원 종료일이 기준일 뒤인 기록도 현재 취소·말소 상태로 제외했던 선택 규칙이 근거다. 관련 후보1,480/167 및 최종수정일 대체14/0은 기록 단위이며 실제 누락 시설 수나 접근성 영향으로 바꿔 말하지 않는다. 공공체육을 대신 넣지 않았다. 근거 스냅샷과 전후집계는 `구축코드/14_체육제외/근거/`와 `시설연도_전후비교.csv`에 있다.

공공시설의 명부 날짜 차이는 사용자가 채택한 인접시점 대리 가정이다. 보건소 후시점 명부·주민센터·소방 연도판 등을 정확한 과거 관측 검증으로 표현하지 않는다. 소매 역사 원배포본은 요청했으나 미입수이므로 현재 소매를 유지하고 민감도·시점 한계를 보고한다.
'''


change(PKG / '문서/출처_전처리_안내.md', source_doc)
change(PKG / '문서/무결성_검증.md', lambda text: f'''# 현행 검증 안내 — facility-v1.4 (2026-09-29)

현재판은 체육시설업만 두 시점에서 제외한32종·584,766행이다. 나머지 값·스키마·순서는 v1.3과 정확히 같다. 활성 채택 입력→통합→분석용 재현 및 이전판 보관 해시 PASS. 상세 `../구축코드/14_체육제외/final_verification.json`, 재현 `../구축코드/14_체육제외/README.md`. 아래는 v1.3 및 이전판 검증 이력이며 현재 행수·유형수를 뜻하지 않는다.

''' + text)


def registry(text):
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith('| facility-v1.3 |'))
    assert not any(line.startswith('| facility-v1.4 |') for line in lines)
    lines[index] = f'| facility-v1.3 | 서울 시설33종 2020/2025, 606,066행·25열. 미좌표87행 보완·오좌표4행 교정·근거부족2행 좌표 제외 | `../_archive/facility-v1.3_superseded_20260929/데이터/서울시설_2020_2025_분석용.parquet`; 보관·삭제보류목록 `시설데이터 구축/시설데이터_패키지/구축코드/14_체육제외/deferred_cleanup_manifest.json` | 2026-09-29 | {old_digest} | 시설데이터 구축 대화 | **대체됨** (→facility-v1.4). 06 현access-engine-v3.2의 입력이므로 v1.4 접근성 재계산·검증 완료까지 이전 전체 분석본 보존. 영구삭제 없음. |'
    lines.insert(index + 1, f'| facility-v1.4 | 서울 시설32종 2020/2025. 체육시설업만10,293/11,007행 제외. 본분석27종·기능7카테고리+통제5종. 소매·나머지 속성/좌표 불변 | `시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet` (584,766행·25열); 명시적 선택·검증·재현 `구축코드/14_체육제외/README.md` | 2026-09-29 (공공시설 인접시점 대리 가정, 소매 역사 원본 요청 중·미입수) | {digest} | 시설데이터 구축 대화 | **확정** (사용자 유형 제외 결정). 분석가능581,888행({rate}%), 미좌표2,821행. v1.3 필터값·스키마·순서 일치/입력130파일 불변/재현 PASS. 06 현v3.2는 여전히v1.3·8카테고리이며 별도 재계산 필요. |')
    return '\n'.join(lines) + '\n'


change(ROOT / '데이터_배포목록.md', registry)


def sharing(text):
    text = text.replace('**시설**: 서울 33종 시설', '**시설**: 서울 32종 시설', 1)
    text = text.replace('SGIS 인구·경계 | facility-v1.2 |', 'SGIS 인구·경계. 체육 제외·본분석27종/7카테고리+통제5종 | facility-v1.4 |', 1)
    text = text.replace('`데이터_배포목록.md` facility-v1.2 행', '`데이터_배포목록.md` facility-v1.4 행', 1)
    text = text.replace('- 접근성 전체: `06_', '- 접근성 전체(현v3.2는 시설v1.3·8카테고리 기준. 시설v1.4의32종·7카테고리로 코드/메타를 갱신한 뒤 담당자가 재계산해야 함): `06_', 1)
    text = text.replace('원천 현행판은 배포목록 facility-v1.3 행을 따른다.', '시설 원천 현행판은 facility-v1.4(체육 제외32종·7카테고리)로 갱신되었다. 위v3.2는 시설v1.3 입력의 비교용 현 결과이며 v1.4 접근성 재계산 전에는 최신 시설 결과로 인용하지 않는다.')
    text += f'''

### 시설 v1.4 인계(2026-09-29)

공식 분석 입력은 기존 경로의584,766행·32종이며 SHA-256 `{digest}`. 체육시설업만 두 시점에서 제외했고 소매·나머지 값·좌표는 그대로다. 공공체육 대체 없음. 소매 과거 원본은 요청 중·미입수이며 공공시설 시점은 인접시점 대리 가정이다.

시설 검증/재현은 `시설데이터 구축/시설데이터_패키지/구축코드/14_체육제외/README.md` 참조. 06v3.2와 비교할 이전 v1.3 전체 분석본은 `{archive_root}/데이터/서울시설_2020_2025_분석용.parquet`에 보존(SHA `{old_digest}`). 교체된 시설 생성파일5개는 접근성 재계산·검증 완료 전 영구삭제하지 않으며 `deferred_cleanup_manifest.json`에 위치·해시·정리 조건을 기록했다. 원자료·코드·캐시·배제 근거는 계속 보존한다. 이번 시설 작업에서06파일/결과/정책차단stage는 손대지 않았다.
'''
    return text


change(ROOT / '공유_안내.md', sharing)

# Check optimistic concurrency immediately before each scoped write.
written = []
for path, (before, after) in changes.items():
    assert path.read_text(encoding='utf-8-sig') == before, f'Concurrent edit: {path}'
    path.write_text(after, encoding='utf-8')
    written.append({'path': str(path.relative_to(ROOT)), 'before_sha256_utf8': hashlib.sha256(before.encode()).hexdigest(), 'after_sha256': sha(path)})
write_json(HERE / 'documentation_updates.json', written)

# Exact deferred inventory: archive files can be considered only after access validation.
pending = {'status': 'pending_accessibility_v1.4_rebuild_validation', 'permanent_deletions_this_task': 0,
    'active_release': 'facility-v1.4', 'comparison_release': 'facility-v1.3',
    'old_analysis_sha256': old_digest, 'new_analysis_sha256': digest,
    'condition': '06 v1.4/7-category recalculation verified; old v1.3/v3.2 comparison completed and archived evidence retained. No automatic deletion.',
    'not_deletion_candidates': ['raw/source', 'geocoding caches', 'source and release code', 'exclusion and correction evidence', 'required reproduction input snapshots', 'hash/manifests/change logs', 'any 06 files or denied stage'],
    'files': [{**item, 'status': 'keep_until_access_validation', 'replacement': str(PKG / item['relative_path']),
               'replacement_sha256': next(x['new_sha256'] for x in read_json(HERE / 'promotion_manifest.json')['files'] if x['relative_path'] == item['relative_path']),
               'replacement_basis': 'Verified v1.4 sports-only exclusion, canonical reproducibility PASS'} for item in archive['files']]}
write_json(HERE / 'deferred_cleanup_manifest.json', pending)
print(json.dumps({'updated_docs': len(written), 'registry_v14_sha256': digest, 'deferred_files': len(pending['files'])}))
