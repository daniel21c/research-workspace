"""Bounded offline cache evidence for the existing parser substring risk."""
import sys,json,ast,math,hashlib,re
from pathlib import Path
from collections import Counter,defaultdict
from pyproj import Transformer
import address_rules as strict
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PKG=HERE.parent;OUT=HERE/'승격검토';BUILD=PKG/'구축코드'
src=(HERE/'address_rules.py').read_text(encoding='utf-8');src='\n'.join(x for x in src.splitlines() if not x.startswith('ROAD_RE = re.compile(ROAD_RE.pattern') and not x.startswith('JIBUN_RE = re.compile(JIBUN_RE.pattern'))
old={};exec(compile(src,'legacy_parser_pure','exec'),old)
tree=ast.parse((HERE/'geocode_candidate.py').read_text(encoding='utf-8'));ns={'re':re,'math':math}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['integer','sanitize']],type_ignores=[]),'sanitize_only','exec'),ns)
risks=json.loads((OUT/'parser_risk_rows.json').read_text(encoding='utf-8'))
targets={c['query'] for r in risks for c in r['removed']+r['strict']};hits=defaultdict(list);scanned=0
for p in BUILD.rglob('*.json'):
 if not any('cache' in x.lower() or 'geocoding' in x.lower() for x in p.parts):continue
 scanned+=1
 try:z=json.loads(p.read_text(encoding='utf-8-sig'))
 except (ValueError,UnicodeError):continue
 if not isinstance(z,dict):continue
 q=z.get('query','');queries={q}|{c['query'] for c in old['parse_addr'](q)}
 qs=queries&targets
 if not qs:continue
 providers=[]
 if z.get('provider'):
  provider='kakao' if 'kakao' in z['provider'].lower() else 'vworld' if 'vworld' in z['provider'].lower() else ''
  if provider:providers.append((provider,z.get('response',{})))
 for provider in ['kakao','vworld']:
  if isinstance(z.get(provider),dict):providers.append((provider,z[provider].get('response',{})))
 if not providers and isinstance(z.get('response'),dict):
  body=z['response']
  if 'documents' in body:providers.append(('kakao',body))
  elif isinstance(body.get('response'),dict):providers.append(('vworld',body))
 for provider,body in providers:
  if not isinstance(body,dict):continue
  points=ns['sanitize'](provider,body)
  if not points:continue
  item={'query':q,'provider':provider,'points':points,'path':str(p.relative_to(PKG))}
  for qq in qs:hits[qq].append(item)
tr=Transformer.from_crs(4326,5179,always_xy=True)
def match(c,point):
 return c['kind']==point['kind'] and c['main']==point['main'] and c['sub']==point['sub'] and (c['road']==point['road'] if c['kind']=='road' else c['dong']==point['dong'] and c['san']==point['san'])
def evidence(r,cs):
 x,y=tr.transform(r['lon'],r['lat']);out=[]
 for c in cs:
  for h in hits.get(c['query'],[]):
   for p in h['points']:
    if not match(c,p):continue
    xx,yy=tr.transform(p['lon'],p['lat']);d=math.hypot(xx-x,yy-y)
    if d<=15:out.append({'query':c['query'],'cache_query':h['query'],'provider':h['provider'],'distance_m':round(d,3),'path':h['path'],'point':p})
 return out
for r in risks:
 r['strict_evidence']=evidence(r,r['strict']);r['removed_evidence']=evidence(r,r['removed'])
 r['status']='strict_cache_supported' if r['strict_evidence'] else 'removed_query_coordinate_match' if r['removed_evidence'] else 'no_matching_cache'
(OUT/'parser_cache_evidence.json').write_text(json.dumps(risks,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'cache_files_scanned':scanned,'query_cache_hits':len(hits),'rows':len(risks),'status':dict(Counter(r['status'] for r in risks)),'unresolved_facilities':dict(Counter(r['facility'] for r in risks if r['status']!='strict_cache_supported'))}
(OUT/'parser_cache_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
