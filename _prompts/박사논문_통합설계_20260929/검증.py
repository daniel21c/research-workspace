"""Validate only this integration draft and read-only source fingerprints."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASELINE = REPO / '_prompts/orchestrator_rebuild_20260929/data_baseline_20260929_174154490.json'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

now = datetime.now().astimezone().isoformat()
baseline = json.loads(BASELINE.read_text(encoding='utf-8-sig'))
baseline_rows = []
for row in baseline['files']:
    path = Path(row['path'])
    current = digest(path) if path.exists() else None
    baseline_rows.append({'path':str(path), 'expected_sha256':row['sha256'], 'current_sha256':current,
                          'matches':current == row['sha256']})

checks, sources, link_errors, table_errors = [], {}, [], []
documents = ['통합설계안.md', '근거표.md', '작업기록.md', '7범주_탑다운_실행기준.md']
for name in documents:
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    checks.append({'check':f'{name}: utf8_no_replacement', 'passed':'\ufffd' not in text})
    checks.append({'check':f'{name}: balanced_fences', 'passed':sum(line.startswith('```') for line in text.splitlines()) % 2 == 0})
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\n)]+))\)', text):
        target = match.group(1) or match.group(2)
        if target.startswith(('https://','http://','codex://','#')):
            continue
        lineno = None
        line_match = re.search(r':(\d+)$', target)
        if line_match:
            lineno = int(line_match.group(1))
            target = target[:line_match.start()]
        source = Path(target)
        if not source.is_absolute():
            source = ROOT / source
        if not source.exists():
            link_errors.append({'document':name,'target':target,'reason':'missing_file'})
            continue
        source = source.resolve()
        line_count = None
        if source.suffix in ['.md','.txt','.py']:
            line_count = len(source.read_text(encoding='utf-8-sig').splitlines())
            if lineno and lineno > line_count:
                link_errors.append({'document':name,'target':target,'line':lineno,'reason':'line_out_of_range'})
        sources[str(source)] = {'sha256':digest(source),'bytes':source.stat().st_size,
                                'mtime_ns':source.stat().st_mtime_ns,'line_count':line_count}
    expected_cols = None
    for index, line in enumerate(text.splitlines(), 1):
        if line.startswith('|'):
            cols = len(re.split(r'(?<!\\)\|', line)) - 2
            if expected_cols is None:
                expected_cols = cols
            elif cols != expected_cols:
                table_errors.append({'document':name,'line':index,'columns':cols,'expected':expected_cols})
        else:
            expected_cols = None

main = (ROOT / '통합설계안.md').read_text(encoding='utf-8')
ids_used = set(re.findall(r'\b(?:C0[012]|D0[1-5]|L01|R[1-4])\b', main))
evidence = (ROOT / '근거표.md').read_text(encoding='utf-8')
ids_defined = set(re.findall(r'^\| ((?:C0[012]|D0[1-5]|L01|R[1-4])) \|', evidence, re.M))
checks += [
    {'check':'baseline_six_fingerprints','passed':len(baseline_rows)==6 and all(r['matches'] for r in baseline_rows)},
    {'check':'local_links_and_line_anchors','passed':not link_errors},
    {'check':'markdown_table_columns','passed':not table_errors},
    {'check':'evidence_ids_resolve','passed':ids_used <= ids_defined},
    {'check':'required_ten_sections','passed':all(re.search(rf'^## {i}\. ',main,re.M) for i in range(1,11))},
    {'check':'five_chapter_outline','passed':all(f'### 제{i}장 ' in main for i in range(1,6))},
    {'check':'flowchart_present','passed':'```mermaid\nflowchart' in main},
]
write_json('근거_스냅샷.json', {'captured_at':now,'scope':'current source fingerprints; not rerun of research analyses',
    'baseline_path':str(BASELINE),'baseline_sha256':digest(BASELINE),'baseline_files':baseline_rows,'linked_files':sources})
result = {'checked_at':now,'passed':all(c['passed'] for c in checks),'checks':checks,
          'link_errors':link_errors,'table_errors':table_errors,
          'not_performed':['research recalculation','production data verification rerun','professor approval','external publication']}
write_json('검증결과.json',result)
print(json.dumps({'passed':result['passed'],'checks':len(checks),'source_files':len(sources),
                  'link_errors':link_errors,'table_errors':table_errors}, ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
