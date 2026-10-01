"""Prepare public address evidence; no credentials or HTTP, original inputs read-only."""
import json,re,sys,hashlib
from collections import defaultdict,Counter
from pathlib import Path
import pandas as pd
from address_rules import parse_addr,clean,GU
from inventory import HERE,PKG,BUILD,sha
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def tidy(x):return '' if x is None or (isinstance(x,float) and pd.isna(x)) else str(x).strip()
def main():
 records=json.loads((HERE/'입력/null_records.json').read_text(encoding='utf-8'))
 paths=defaultdict(list)
 for p in BUILD.rglob('*'):
  if p.is_file():paths[p.name].append(p)
 rawgroups=defaultdict(list)
 for r in records:
  r['raw_alternatives']=[]
  fn=Path(tidy(r.get('source_file'))).name
  if fn.endswith('.csv') and ':' in tidy(r.get('source_row_id')):rawgroups[fn].append(r)
 rawstats={}
 for fn,rows in rawgroups.items():
  ps=paths.get(fn,[])
  if not ps:rawstats[fn]={'missing':True};continue
  p=sorted(ps,key=lambda p:len(str(p)))[0]
  for enc in ['utf-8-sig','cp949','euc-kr']:
   try:
    h=pd.read_csv(p,nrows=0,encoding=enc);break
   except UnicodeDecodeError:continue
  cols=[c for c in h.columns if c in ['관리번호','사업장명','지번주소','도로명주소','소재지전체주소','도로명전체주소']]
  frame=pd.read_csv(p,usecols=cols,dtype=str,encoding=enc,encoding_errors='replace',low_memory=False).fillna('')
  matched=0
  for r in rows:
   rid,control=tidy(r['source_row_id']).split(':',1)
   pos=int(rid)-1
   if not 0<=pos<len(frame) or frame.iloc[pos].get('관리번호')!=control:
    hit=frame.index[frame['관리번호']==control].tolist() if '관리번호' in frame else []
    if len(hit)!=1:continue
    pos=hit[0]
   sr=frame.iloc[pos]
   # Source ID and public business name must both identify this historical record.
   if re.sub(r'\s+','',clean(sr.get('사업장명')))!=re.sub(r'\s+','',clean(r.get('name'))):continue
   matched+=1
   for c in cols:
    if '주소' in c and tidy(sr[c]) and '\ufffd' not in tidy(sr[c]):r['raw_alternatives'].append({'address':tidy(sr[c]),'source':str(p.relative_to(PKG)),'column':c,'row':pos+1})
  rawstats[fn]={'matched_rows':matched,'rows':len(rows),'sha256':sha(p),'path':str(p.relative_to(PKG))}
 queries={};parsed=0
 for r in records:
  candidates=[];seen=set()
  addresses=[{'address':tidy(r.get('address')),'source':r['adopted_path'],'column':'address','row':tidy(r.get('source_row_id'))}]+r['raw_alternatives']
  for c in ['address_road','address_jibun']:
   if tidy(r.get(c)):addresses.append({'address':tidy(r[c]),'source':r['adopted_path'],'column':c,'row':tidy(r.get('source_row_id'))})
  expected=next((g for a in addresses for g in GU if g in a['address']),None)
  if not expected:expected=next((g for c in ['gu','gu_name'] for g in GU if g==tidy(r.get(c))),None)
  r['expected_gu']=expected
  # Explicit parcel numbers remain usable when a building name intervenes.
  # Apartment block/unit numbers without the word 번지 are deliberately excluded.
  for a in list(addresses):
   explicit=re.search(r'(?:구\s+)([가-힣]+\d*(?:동|가))\s+[^,]*?\s(\d+(?:-\d+)?)\s*번지',a['address'])
   if expected and explicit:
    addresses.append({**a,'address':f'서울특별시 {expected} {explicit[1]} {explicit[2]}','column':a['column']+'_explicit_parcel'})
  for a in addresses:
   text=a['address']
   text=re.sub(r'^(서울특별시|서울시|서울)(?=[가-힣])',r'\1 ',text)
   # A parcel subnumber written as N번지 M호 must not become parcel N alone.
   text=re.sub(r'(\d+)\s*번지\s*(\d+)\s*호',r'\1-\2',text)
   text=re.sub(r'([가-힣]+(?:동|가))\s*(\d+)\s*의\s*(\d+)',r'\1 \2-\3',text)
   if expected and not any(g in text for g in GU):text=f'서울특별시 {expected} {text}'
   for c in parse_addr(text):
    q=c['query'];cg=next((g for g in GU if re.search(r'(^|\s)'+g+r'(\s|$)',q)),None)
    if not q.startswith('서울특별시 ') or not cg or (expected and cg!=expected):continue
    if q in seen:continue
    seen.add(q);c.update(gu=cg,evidence=a);candidates.append(c);queries[q]={k:v for k,v in c.items() if k!='evidence'}
  r['candidates']=candidates;parsed+=bool(candidates)
 dump(HERE/'입력/prepared_records.json',records);dump(HERE/'입력/queries.json',queries);dump(HERE/'입력/raw_evidence.json',rawstats)
 summary={'rows':len(records),'rows_with_parsable_candidates':parsed,'unique_queries':len(queries),'raw_alt_rows':sum(bool(r['raw_alternatives']) for r in records),'raw_matched':sum(x.get('matched_rows',0) for x in rawstats.values())}
 dump(HERE/'검증/preparation.json',summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
