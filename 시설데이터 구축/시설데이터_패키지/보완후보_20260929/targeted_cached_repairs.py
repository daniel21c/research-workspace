"""Inspect exact full-address cache entries for six confirmed parser failures."""
import json,sys,hashlib
from pathlib import Path
from collections import defaultdict
from geocode_candidate import sanitize,exact_match,districts
from address_rules import parse_addr
from inventory import sha
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PKG=HERE.parent;OUT=HERE/'승격검토'
queries={69:['서울특별시 성동구 금호동1가 688','서울특별시 성동구 난계로 20'],206:['서울특별시 강서구 곰달래로57가길 26'],207:['서울특별시 성북구 보국문로16가길 20'],276:['서울특별시 강서구 곰달래로57가길 26'],10242:['서울특별시 종로구 인사동9길 9'],450816:[]}
byname=defaultdict(list)
for p in (PKG/'구축코드').rglob('*.json'):
 if any('cache' in x.lower() or 'geocoding' in x.lower() for x in p.parts):byname[p.name].append(p)
geoms=districts();out=[]
for idx,qs in queries.items():
 matches=[];searched=0
 for q in qs:
  for c in parse_addr(q):
   if c['query']!=q:continue
   c['gu']=q.split()[1]
   names=[]
   for tag in ['kakao','vworld_road','vworld_parcel']:
    h=hashlib.sha1(f'{tag}|{q}'.encode()).hexdigest()[:20];names.append((tag.split('_')[0],f'{tag}_{h}.json'))
   for provider,name in names:
    for p in byname[name]:
     searched+=1;z=json.loads(p.read_text(encoding='utf-8'));body=z.get('response',{});points=sanitize(provider,body);point=exact_match(c,{'points':points},geoms)
     if point:matches.append({'query':q,'kind':c['kind'],'gu':c['gu'],'provider':provider,'point':point,'path':str(p.relative_to(PKG)),'sha256':sha(p)})
 out.append({'row_index':idx,'complete_source_queries':qs,'cached_files_checked':searched,'matches':matches,'decision':'correct_from_exact_cache' if matches else 'clear_unsupported_coordinate'})
(OUT/'targeted_repairs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='matches'}|{'exact_matches':len(r['matches'])} for r in out],ensure_ascii=False))
