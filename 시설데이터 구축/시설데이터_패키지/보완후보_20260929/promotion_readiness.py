"""Read-only existing geocode parser risk review; never imports provider clients."""
import sys,json,re,math
from pathlib import Path
from collections import Counter
import pandas as pd
import address_rules as strict
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PKG=HERE.parent
out=HERE/'승격검토';out.mkdir(exist_ok=True)
src=(HERE/'address_rules.py').read_text(encoding='utf-8')
src='\n'.join(x for x in src.splitlines() if not x.startswith('ROAD_RE = re.compile(ROAD_RE.pattern') and not x.startswith('JIBUN_RE = re.compile(JIBUN_RE.pattern'))
old={};exec(compile(src,'legacy_parser_pure','exec'),old)
a=pd.read_parquet(PKG/'데이터/서울시설_2020_2025_분석용.parquet')
valid=a[a.lon.notna() & a.coord_method.str.contains('geocod|geocod|borrow',case=False,na=False)]
risks=[]
for i,r in valid.iterrows():
 before=old['parse_addr'](r.address);after=strict.parse_addr(r.address)
 removed=[c for c in before if c['query'] not in {z['query'] for z in after}]
 if removed:risks.append({'row_index':int(i),'facility_id':str(r.facility_id),'year':int(r.year),'facility':str(r['시설']),'address':str(r.address),'lon':float(r.lon),'lat':float(r.lat),'method':str(r.coord_method),'removed':removed,'strict':after})
(out/'parser_risk_rows.json').write_text(json.dumps(risks,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'valid_method_counts':dict(Counter(a.loc[a.lon.notna(),'coord_method'].fillna(''))),'checked_rows':len(valid),'risk_rows':len(risks),'risk_facilities':dict(Counter(r['facility'] for r in risks)),'risk_unique_removed_queries':len({c['query'] for r in risks for c in r['removed']})}
(out/'parser_risk_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
