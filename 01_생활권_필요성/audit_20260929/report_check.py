import sys,re,json,csv
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).parent; p=B.parent/'무결성감사_20260929.md'
s=p.read_text(encoding='utf-8')
bad=[]; refs=0
for target in re.findall(r'\]\(([^)]+)\)',s):
    if not re.match(r'[A-Za-z]:/',target): continue
    refs+=1; z=re.sub(r':\d+$','',target)
    if not Path(z).exists(): bad.append(target)
rows=list(csv.DictReader((B/'recomputed_fixed_units.csv').open(encoding='utf-8-sig')))
key=[r for r in rows if r['variant']=='correct_T' and r['level']=='공식LZ']
result={'report_bytes':p.stat().st_size,'report_lines':len(s.splitlines()),'local_links':refs,'missing_links':bad,'corrected_official_rows':key}
(B/'report_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if bad: raise SystemExit(1)
