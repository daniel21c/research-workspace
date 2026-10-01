"""Compare every unique accepted address with the other approved provider."""
import json,math,sys
from collections import Counter
from inventory import HERE
from prepare import dump
from geocode_candidate import Client,exact_match,districts,key,TR
sys.stdout.reconfigure(encoding='utf-8')
def main():
 patches=json.loads((HERE/'결과/patch_manifest.json').read_text(encoding='utf-8'));queries=json.loads((HERE/'입력/queries.json').read_text(encoding='utf-8'));legacy=json.loads((HERE/'cache/legacy_v2.json').read_text(encoding='utf-8'))
 client=Client(True);geoms=districts();seen=set();out=[];blocked=[]
 for p in patches:
  q=p['query']
  if q in seen:continue
  seen.add(q);c=queries[q];provider='vworld' if p['provider']=='kakao' else 'kakao';k=key(provider,q,c['kind']);item=legacy.get(k)
  if item is None:item=client.request(provider,c)
  point=exact_match(c,item,geoms);rec={'query':q,'primary_provider':p['provider'],'comparison_provider':provider,'source':item.get('source'),'point_count':len(item.get('points',[])),'comparison_exact':point is not None}
  if point:
   x,y=TR.transform(p['lon'],p['lat']);xx,yy=TR.transform(point['lon'],point['lat']);d=math.hypot(xx-x,yy-y);rec['distance_m']=round(d,3);rec['comparison_point']=point
   if d>50:blocked.append(q);rec['verdict']='hold_coordinate_disagreement'
   else:rec['verdict']='corroborated_within_50m'
  else:rec['verdict']='second_provider_no_exact_match'
  out.append(rec)
 dump(HERE/'검증/cross_provider.json',{'addresses':len(out),'results':out,'verdicts':dict(Counter(r['verdict'] for r in out)),'http_this_run':client.this_run})
 dump(HERE/'검증/cross_provider_blocklist.json',blocked)
 print(json.dumps({'addresses':len(out),'verdicts':dict(Counter(r['verdict'] for r in out)),'http_this_run':client.this_run},ensure_ascii=False))
if __name__=='__main__':main()
