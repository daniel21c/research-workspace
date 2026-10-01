"""Local source-row trace review only, with no writes to adopted input files."""
import sys,json,re
from pathlib import Path
from collections import Counter,defaultdict
import pandas as pd
import pyarrow.parquet as pq
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PKG=HERE.parent;OUT=HERE/'승격검토'
src=(HERE/'address_rules.py').read_text(encoding='utf-8');src='\n'.join(x for x in src.splitlines() if not x.startswith('ROAD_RE = re.compile(ROAD_RE.pattern') and not x.startswith('JIBUN_RE = re.compile(JIBUN_RE.pattern'))
old={};exec(compile(src,'legacy_parser_pure','exec'),old)
rows=json.loads((OUT/'parser_risk_rows.json').read_text(encoding='utf-8'));keys={(r['facility_id'],r['year']):r for r in rows}
for f in (PKG/'데이터/시설별').rglob('*.parquet'):
 columns=pq.read_schema(f).names
 cols=[c for c in columns if c in ['facility_id','year_snapshot','address','coord_method','source_row_id'] or any(s in c for s in ['detail','fix_note','coord_stage'])]
 if not {'facility_id','year_snapshot'}.issubset(cols):continue
 a=pd.read_parquet(f,columns=cols)
 a=a[a.facility_id.isin([x[0] for x in keys])]
 for _,z in a.iterrows():
  k=(str(z.facility_id),int(str(z.year_snapshot)[:4]))
  if k in keys:keys[k]['trace']={'path':str(f.relative_to(PKG)),**{c:None if pd.isna(v) else str(v) for c,v in z.items()}}
for r in rows:
 fragments=[]
 for address in old['_norm_variants'](r['address']):
  for kind,regex in [('road',old['ROAD_RE']),('jibun',old['JIBUN_RE'])]:
   m=regex.search(address)
   if m and address[m.end():m.end()+1] and re.match('[0-9가-힣-]',address[m.end():m.end()+1]):fragments.append({'kind':kind,'matched':m.group(0),'tail':address[m.end():m.end()+12]})
 r['fragments']=fragments
(OUT/'parser_provenance_rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'rows':len(rows),'trace_rows':sum('trace' in r for r in rows),'tail_first_char':dict(Counter(x['tail'][0] for r in rows for x in r['fragments']))},ensure_ascii=False))
