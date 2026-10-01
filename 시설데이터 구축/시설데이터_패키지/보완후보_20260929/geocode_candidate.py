"""Bounded, exact-address candidate geocoding. Only this directory is writable.

Offline is default. --online authorizes the already approved providers for this
task, with an aggregate persisted 12,000 HTTP cap. Credentials never leave memory
except in the intended provider authentication mechanism. No exception messages,
request URLs, headers, or raw API responses are logged or saved.
"""
import sys,os,re,json,time,math,hashlib,argparse,datetime
from pathlib import Path
from collections import Counter,defaultdict
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
from address_rules import parse_addr,clean,GU
from inventory import HERE,PKG,BUILD,sha
from prepare import dump,tidy
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
ROOT=next(p for p in PKG.parents if (p/'시설데이터 구축').is_dir())
CAP=12000
TR=Transformer.from_crs(4326,5179,always_xy=True)
NOW=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()

def credentials():
 result={}
 for p in [os.environ.get('FACILITY_API_ENV',''),str(ROOT/'_secrets/facility_api.env')]:
  if not p or not Path(p).is_file():continue
  for line in Path(p).read_text(encoding='utf-8-sig').splitlines():
   if '=' not in line or line.lstrip().startswith('#'):continue
   k,v=line.split('=',1);k=k.strip();v=v.strip().strip('\"\'')
   if k in ['KAKAO_REST_API_KEY','VWORLD_API_KEY'] and v:result.setdefault(k,v)
 return result

def integer(x):
 try:return int(str(x or '0').strip())
 except (ValueError,TypeError):return -1

def sanitize(provider,body):
 """Public address fields only; no provider errors or private response data."""
 out=[]
 if provider=='kakao':
  for d in body.get('documents',[]):
   a=d.get('address') or {};r=d.get('road_address') or {}
   if d.get('address_type') not in ['REGION_ADDR','ROAD_ADDR']:continue
   for kind,z in [('road',r),('jibun',a)]:
    if not z:continue
    out.append({'kind':kind,'lon':z.get('x') or d.get('x'),'lat':z.get('y') or d.get('y'),
     'city':z.get('region_1depth_name',''),'gu':z.get('region_2depth_name',''),
     'road':z.get('road_name',''),'dong':z.get('region_3depth_name',''),
     'main':integer(z.get('main_building_no') if kind=='road' else z.get('main_address_no')),
     'sub':integer(z.get('sub_building_no') if kind=='road' else z.get('sub_address_no')),
     'san':z.get('mountain_yn')=='Y'})
 else:
  z=body.get('response',body)
  if z.get('status')!='OK':return []
  p=z.get('result',{}).get('point',{});s=z.get('refined',{}).get('structure',{})
  nm=str(s.get('level5',''));m=re.match(r'^(산\s*)?(\d+)(?:-(\d+))?',nm)
  if m:
   out.append({'kind':'road' if s.get('level4L') else 'jibun','lon':p.get('x'),'lat':p.get('y'),
    'city':s.get('level1',''),'gu':s.get('level2',''),'road':s.get('level4L',''),
    'dong':s.get('level4LC') or s.get('level4A') or s.get('level3',''),
    'main':int(m.group(2)),'sub':int(m.group(3) or 0),'san':bool(m.group(1))})
 safe=[]
 for x in out:
  try:x['lon']=float(x['lon']);x['lat']=float(x['lat'])
  except (ValueError,TypeError):continue
  if all(math.isfinite(x[k]) for k in ['lon','lat']):safe.append(x)
 return safe

def key(provider,query,kind):return hashlib.sha256(f'{provider}|{kind}|{query}'.encode()).hexdigest()

def import_legacy(queries):
 """Import only sanitized success records for needed public-address queries."""
 target=HERE/'cache/legacy_v2.json'
 if target.exists():return json.loads(target.read_text(encoding='utf-8'))
 hits={};scanned=0
 for p in BUILD.rglob('*.json'):
  if not any('cache' in part.lower() or 'geocoding' in part.lower() for part in p.parts):continue
  scanned+=1
  try:z=json.loads(p.read_text(encoding='utf-8-sig'))
  except (ValueError,UnicodeError):continue
  if not isinstance(z,dict):continue
  original_q=z.get('query');q=original_q
  if q not in queries:
   parsed=parse_addr(q or '');q=next((c['query'] for c in parsed if c['query'] in queries),None)
  if q not in queries:continue
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
   points=sanitize(provider,body)
   known_response=('documents' in body if provider=='kakao' else body.get('response',body).get('status') in ['OK','NOT_FOUND','ZERO_RESULT'])
   if points or known_response:
    k=key(provider,q,queries[q]['kind']);item={'provider':provider,'query':q,'kind':queries[q]['kind'],'points':points,'source':'legacy','status':'success_points' if points else 'provider_no_result','source_file':str(p.relative_to(PKG)),'source_sha256':sha(p)}
    if k not in hits or (points and not hits[k]['points']):hits[k]=item
 dump(target,hits);print(json.dumps({'legacy_scanned':scanned,'legacy_needed_successes':len(hits)}),flush=True)
 return hits

class Client:
 def __init__(self,online):
  self.online=online;self.keys=credentials() if online else {};self.dir=HERE/'cache/requests';self.dir.mkdir(exist_ok=True)
  self.ledger_path=HERE/'검증/http_ledger.json'
  self.ledger=json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {'total':0,'provider_calls':{},'disabled':{},'status_counts':{}}
  self.this_run=0
 def request(self,provider,c,test=False):
  k=key(provider,c['query'],c['kind']);p=self.dir/(k+'.json')
  if p.exists():return json.loads(p.read_text(encoding='utf-8'))
  if not self.online:return {'source':'offline_missing','points':[]}
  if provider in self.ledger['disabled']:return {'source':'provider_disabled','points':[]}
  cred=self.keys.get('KAKAO_REST_API_KEY' if provider=='kakao' else 'VWORLD_API_KEY')
  if not cred:return {'source':'credential_missing','points':[]}
  import requests
  status='unknown';points=[]
  for attempt in range(3):
   if self.ledger['total']>=CAP:status='cap_reached';break
   self.ledger['total']+=1;self.this_run+=1;self.ledger['provider_calls'][provider]=self.ledger['provider_calls'].get(provider,0)+1
   dump(self.ledger_path,self.ledger)
   try:
    if provider=='kakao':
     resp=requests.get('https://dapi.kakao.com/v2/local/search/address.json',params={'query':c['query'],'size':10,'analyze_type':'exact'},headers={'Authorization':'KakaoAK '+cred},timeout=(8,20),allow_redirects=False)
    else:
     resp=requests.get('https://api.vworld.kr/req/address',params={'service':'address','request':'getcoord','version':'2.0','crs':'epsg:4326','address':c['query'],'refine':'true','simple':'false','format':'json','type':'road' if c['kind']=='road' else 'parcel','key':cred},timeout=(8,20),allow_redirects=False)
    status=str(resp.status_code)
    if resp.status_code in [401,403,429]:self.ledger['disabled'][provider]='http_'+status
    if resp.status_code==200:
     try:body=resp.json()
     except ValueError:body={};status='invalid_json'
     if provider=='vworld':
      error=body.get('response',{}).get('error',{});code=str(error.get('code',''))
      # Never persist provider messages; recognize authentication/quota failure codes.
      if code in ['INVALID_KEY','INCORRECT_KEY','EXPIRED_KEY','UNREGISTERED_KEY','LIMIT_EXCEEDED','OVER_LIMIT','REQUEST_LIMIT_EXCEEDED'] or any(t in str(error).lower() for t in ['quota','limit','인증키','횟수','사용량','요금']):
       self.ledger['disabled'][provider]='provider_auth_or_quota';status='provider_auth_or_quota'
     points=sanitize(provider,body)
    transient=resp.status_code in [408,500,502,503,504]
   except requests.RequestException:
    status='transport_error';transient=True
   except Exception:
    # Deliberately do not stringify exceptions, including URLs that contain API keys.
    status='sanitized_client_error';transient=False
   sk=provider+':'+status;self.ledger['status_counts'][sk]=self.ledger['status_counts'].get(sk,0)+1;dump(self.ledger_path,self.ledger)
   if not transient or provider in self.ledger['disabled']:break
   if attempt<2:time.sleep(2**attempt)
  item={'provider':provider,'query':c['query'],'kind':c['kind'],'source':'api','fetched_utc':NOW(),'status':status,'points':points,'test':test}
  dump(p,item);return item

def districts():
 p=PKG/'SGIS_인구경계_2019_2024/03_행정구역/경계_2025_2Q/bnd_sigungu_00_2025_2Q/bnd_sigungu_00_2025_2Q.shp'
 g=gpd.read_file(p);g=g[g.SIGUNGU_CD.astype(str).str.startswith('11')].to_crs(5179)
 return {str(r.SIGUNGU_NM).split()[-1]:r.geometry for _,r in g.iterrows()}

def exact_match(c,item,geoms):
 matches=[]
 for x in item.get('points',[]):
  if x['kind']!=c['kind'] or x['gu']!=c['gu'] or x['city'] not in ['서울','서울특별시','서울시']:continue
  if x['main']!=c['main'] or x['sub']!=c['sub']:continue
  if c['kind']=='road' and x['road']!=c['road']:continue
  if c['kind']=='jibun' and (x['dong']!=c['dong'] or x['san']!=c['san']):continue
  xx,yy=TR.transform(x['lon'],x['lat'])
  if not geoms.get(c['gu'],Point()).covers(Point(xx,yy)):continue
  matches.append(x)
 if not matches:return None
 first=matches[0];fx,fy=TR.transform(first['lon'],first['lat'])
 if any(math.hypot(TR.transform(x['lon'],x['lat'])[0]-fx,TR.transform(x['lon'],x['lat'])[1]-fy)>25 for x in matches[1:]):return None
 return first

def verified_reuse(records,geoms):
 """Two reviewed building-address cases from registered exact-geocoded rows.

 Do not use the bus ID with missing historical address; do not use the subway
 address whose official point lies in another district. Complex retail premises
 must explicitly name the same shopping building, not just the same large site.
 """
 allow={'서울특별시 성동구 매봉길 13':'옥수리버젠','서울특별시 종로구 성균관로4길 21':''}
 a=pd.read_parquet(HERE/'입력/서울시설_2020_2025_분석용.parquet');v=a[a.lon.notna() & a.inside_seoul & a.coord_method.str.contains('geocode_.*exact',regex=True,na=False)]
 refs=defaultdict(list)
 for idx,r in v.iterrows():
  for c in parse_addr(r.address):
   if c['query'] in allow:
    refs[c['query']].append({'row_index':int(idx),'facility_id':r.facility_id,'year':int(r.year),'address':r.address,'lon':float(r.lon),'lat':float(r.lat),'coord_method':r.coord_method})
 result={}
 for r in records:
  for c in r['candidates']:
   q=c['query'];ref=refs.get(q,[])
   if not ref:continue
   token=allow[q]
   if token and (token not in re.sub(r'\s+','',r.get('address') or '') or not all(token in re.sub(r'\s+','',x['address']) for x in ref)):continue
   x,y=TR.transform(ref[0]['lon'],ref[0]['lat'])
   if not geoms[c['gu']].covers(Point(x,y)):continue
   if any(math.hypot(TR.transform(z['lon'],z['lat'])[0]-x,TR.transform(z['lon'],z['lat'])[1]-y)>15 for z in ref):continue
   result[r['row_index']]={'lon':ref[0]['lon'],'lat':ref[0]['lat'],'provider':'registered','evidence_source':'verified_address_reuse','query':q,'kind':c['kind'],'gu':c['gu'],'cache_key':None,'provider_point':None,'legacy_file':None,'reuse_reference_rows':ref,'building_token':token,'address_evidence':c['evidence']}
   break
 return result

def run(online=False,test=False):
 records=json.loads((HERE/'입력/prepared_records.json').read_text(encoding='utf-8'));queries=json.loads((HERE/'입력/queries.json').read_text(encoding='utf-8'))
 client=Client(online)
 if test:
  c=parse_addr('서울특별시 중구 세종대로 110')[0];c['gu']='중구';geoms=districts();summary={}
  for provider in ['kakao','vworld']:
   result=client.request(provider,c,True);summary[provider]={'credential_present':bool(client.keys.get('KAKAO_REST_API_KEY' if provider=='kakao' else 'VWORLD_API_KEY')),'status':result.get('status'),'exact_match':exact_match(c,result,geoms) is not None}
  dump(HERE/'검증/connection_test.json',summary);print(json.dumps(summary));return
 legacy=import_legacy(queries);geoms=districts();reuse=verified_reuse(records,geoms);resolved={};patch=[];remaining=[]
 blockpath=HERE/'검증/cross_provider_blocklist.json';blocked=set(json.loads(blockpath.read_text(encoding='utf-8'))) if blockpath.exists() else set()
 # Query resolution is deterministic and reused for both historical snapshots.
 for i,r in enumerate(records):
  chosen=reuse.get(r['row_index']);tried=[]
  for c in r['candidates']:
   if chosen:break
   q=c['query']
   if q not in resolved:
    hit=None;attempts=[]
    for source in ['legacy','api']:
     for provider in ['kakao','vworld']:
      k=key(provider,q,c['kind'])
      item=legacy.get(k,{'points':[]}) if source=='legacy' else (legacy[k] if k in legacy else client.request(provider,c))
      point=exact_match(c,item,geoms)
      attempts.append({'provider':provider,'source':source,'status':item.get('status',item.get('source','no_cache')),'point_count':len(item.get('points',[]))})
      if point:
       hit={'lon':point['lon'],'lat':point['lat'],'provider':provider,'evidence_source':item.get('source'), 'query':q,'kind':c['kind'],'gu':c['gu'],'cache_key':k,'provider_point':point,'legacy_file':item.get('source_file')};break
     if hit:break
    resolved[q]={'hit':hit,'attempts':attempts}
   answer=resolved[q];tried.append({'query':q,'attempts':answer['attempts']})
   if answer['hit']:
    chosen={**answer['hit'],'address_evidence':c['evidence']};break
  if chosen and chosen['query'] not in blocked:patch.append({'row_index':r['row_index'],'facility_id':r['facility_id'],'year':r['year'],'시설':r['시설'],'adopted_path':r['adopted_path'],**chosen})
  else:remaining.append({'row_index':r['row_index'],'facility_id':r['facility_id'],'year':r['year'],'시설':r['시설'],'reason':'cross_provider_coordinate_disagreement' if chosen else 'no_parsable_seoul_numbered_address' if not r['candidates'] else 'no_exact_provider_and_district_match','attempts':tried})
  if (i+1)%100==0:
   dump(HERE/'검증/progress.json',{'processed':i+1,'filled':len(patch),'remaining':len(remaining),'http_total':client.ledger['total'],'disabled':client.ledger['disabled'],'at':NOW()});print(json.dumps({'processed':i+1,'filled':len(patch),'http_total':client.ledger['total']}),flush=True)
 suffix='_offline' if not online else ''
 dump(HERE/f'결과/patch_manifest{suffix}.json',patch);dump(HERE/f'결과/unresolved{suffix}.json',remaining)
 summary={'rows':len(records),'filled':len(patch),'remaining':len(remaining),'http_this_run':client.this_run,'http_total':client.ledger['total'],'provider_disabled':client.ledger['disabled'],'by_facility':dict(Counter(p['시설'] for p in patch)),'methods':dict(Counter(p['evidence_source']+'_'+p['provider'] for p in patch))}
 dump(HERE/f'검증/run_summary{suffix}.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--online',action='store_true');a.add_argument('--test',action='store_true');z=a.parse_args();run(z.online,z.test)
