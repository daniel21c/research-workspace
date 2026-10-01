"""Check the common-design handoff before setting its completed marker."""
from pathlib import Path
from datetime import datetime
import ast
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASELINE = REPO / '_prompts/orchestrator_rebuild_20260929/data_baseline_20260929_174154490.json'
def sha(p):
    return hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
baseline = json.loads(BASELINE.read_text(encoding='utf-8-sig'))
fingerprints = [{'path':r['path'], 'expected':r['sha256'], 'actual':sha(Path(r['path']))} for r in baseline['files']]
design = (REPO/'박사논문_연구설계.md').read_text(encoding='utf-8-sig')
readme = (REPO/'README.md').read_text(encoding='utf-8-sig')
criteria_path = ROOT/'7범주_탑다운_실행기준.md'
criteria = criteria_path.read_text(encoding='utf-8')
before = (ROOT/'7범주_적용전_보존/박사논문_연구설계.md').read_text(encoding='utf-8-sig')
checks = []
def add(name, passed):
    checks.append({'check':name,'passed':bool(passed)})
add('six_release_fingerprints_unchanged', len(fingerprints)==6 and all(r['expected']==r['actual'] for r in fingerprints))
add('current_versions_in_both_central_documents', all('facility-v1.4' in t and 'access-engine-v3.3-facility-v1.4-20260929' in t for t in (design,readme)))
for section,next_section in [('## 1.','## 2.'),('## 2.','## 3.'),('## 5.','## 6.'),('## 8.','## 9.')]:
    old = before[before.index(section):before.index(next_section)]
    new = design[design.index(section):design.index(next_section)]
    add(f'historical_section_preserved_{section}',old==new)
add('historical_seunghoon_eight_types_preserved','승훈 씨의 기존 8종을 그대로 쓴다(42:30~42:35)' in design)
config = REPO/'06_접근성분석/접근성분석_패키지/코드/a00_config.py'
expected_categories = ['교육','보육·복지','의료','문화','행정·안전','소매','생활서비스']
node = ast.parse(config.read_text(encoding='utf-8-sig'))
literal_maps = []
for stmt in node.body:
    if isinstance(stmt, ast.Assign):
        try:
            value = ast.literal_eval(stmt.value)
        except (ValueError, TypeError):
            continue
        if isinstance(value,dict): literal_maps.append(value)
actual_a = next((d for d in literal_maps if list(d)==expected_categories),None)
add('seven_categories_match_actual_config', actual_a is not None)
add('analysis_types_match_actual_config_27',actual_a is not None and sum(len(v) for v in actual_a.values())==27)
add('criteria_categories_match_config',all(f'| {c} |' in criteria for c in expected_categories))
add('current_ranges_and_distinct_subsets',all(term in design+criteria for term in ['1~7','34항목','4기능·6유형','temporal_common4','A4','A7']))
add('facility_grid_assignment_defined',all('시설도 자신이 들어 있는 격자의 단위' in t for t in (design,criteria)))
add('jtg_no_facility_dependency', '시설·접근성은 JTG 주분석 의존성 없음' in design and '주분석은 시설 접근성 의존 없음' in criteria)
errors=[]
for path in [REPO/'README.md', REPO/'박사논문_연구설계.md',criteria_path]:
    value=path.read_text(encoding='utf-8-sig')
    add(f'utf8_{path.name}','\ufffd' not in value)
    expected=None
    for lineno,line in enumerate(value.splitlines(),1):
        if line.startswith('|'):
            n=len(re.split(r'(?<!\\)\|',line))-2
            if expected is not None and n!=expected: errors.append([path.name,lineno,'table_columns'])
            expected=n
        else:expected=None
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\n)]+))\)',value):
        target=match.group(1) or match.group(2)
        if target.startswith(('http://','https://','#')): continue
        target=re.sub(r':\d+$','',target)
        dest=Path(target)
        if not dest.is_absolute():dest=path.parent/dest
        if not dest.exists():errors.append([path.name,target,'missing_link'])
add('central_and_criteria_table_links',not errors)
for name in ['README.md','박사논문_연구설계.md']:
    old=(ROOT/'7범주_적용전_보존'/name).read_text(encoding='utf-8-sig')
    new=(REPO/name).read_text(encoding='utf-8-sig')
    (ROOT/f'{name}.7범주_변경.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+name,tofile='after/'+name)),encoding='utf-8')
passed=all(c['passed'] for c in checks)
if passed:
    assert '공통설계 상태: 검증중' in criteria or '공통설계 상태: 적용완료' in criteria
    criteria=criteria.replace('공통설계 상태: 검증중','공통설계 상태: 적용완료',1)
    criteria_path.write_text(criteria,encoding='utf-8')
result={'checked_at':datetime.now().astimezone().isoformat(),'passed':passed,'scope':'central common-design application only; no research recalculation', 'checks':checks,'errors':errors,'input_fingerprints':fingerprints,'files':{str(p):sha(p) for p in [REPO/'README.md',REPO/'박사논문_연구설계.md',criteria_path]},'status_marker_written':passed}
(ROOT/'공통설계_적용검증.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':passed,'checks':len(checks),'failed':[r['check'] for r in checks if not r['passed']],'errors':errors,'status':'적용완료' if passed else '검증중'},ensure_ascii=False))
raise SystemExit(0 if passed else 1)
