"""Read immutable facility-v1.2; create a scoped candidate input inventory."""
import sys,json,hashlib,ast,shutil
from pathlib import Path
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PKG=HERE.parent;BUILD=PKG/'구축코드';DATA=PKG/'데이터'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for z in iter(lambda:f.read(4194304),b''):h.update(z)
 return h.hexdigest()
def main():
 for d in ['입력','결과','cache','검증']: (HERE/d).mkdir(exist_ok=True)
 base=DATA/'서울시설_2020_2025_분석용.parquet';snapshot=HERE/'입력'/base.name
 assert sha(base)=='b87ed1cc198bec94d21808b2eb8d0314b6b4b45662782db019a96f3804aef39f'
 if not snapshot.exists():shutil.copyfile(base,snapshot)
 assert sha(snapshot)==sha(base)
 a=pd.read_parquet(snapshot);n=a[a.lon.isna()].copy();n['row_index']=n.index
 names={}
 for z in ast.parse((BUILD/'build_분석용.py').read_text(encoding='utf-8-sig')).body:
  if isinstance(z,ast.Assign) and isinstance(z.targets[0],ast.Name) and z.targets[0].id=='NAME':names=ast.literal_eval(z.value)
 lookup={v:k for k,v in names.items()}; records=[];hashes={str(base.relative_to(PKG)):sha(base)}
 for (fac,year),g in n.groupby(['시설','year']):
  folder=lookup.get(fac)
  p=next((DATA/'시설별'/folder).glob(f'facilities_*_{year}_01.parquet')) if folder else BUILD/f'03_교육교통공원상가/retail_daily/facilities_retail_daily_{year}_01.parquet'
  full=pd.read_parquet(p).set_index('facility_id');hashes[str(p.relative_to(PKG))]=sha(p)
  for _,r in g.iterrows():
   src=full.loc[r.facility_id]
   x={k:r[k] for k in ['row_index','facility_id','year','시설','name','address','시설_세부']}
   for c in ['source_file','source_row_id','gu','gu_name','address_road','address_jibun','status_current','src_status','coord_stage','temporal_reason']:
    if c in src:x[c]=src[c]
   x['adopted_path']=str(p.relative_to(PKG));records.append(x)
 n.groupby(['시설','year']).size().reset_index(name='null_rows').to_csv(HERE/'입력/미좌표_시설별.csv',index=False,encoding='utf-8-sig')
 (HERE/'입력/null_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2,default=lambda x:None if pd.isna(x) else str(x)),encoding='utf-8')
 (HERE/'입력/baseline_hashes.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
 print(n.groupby(['시설','year']).size().to_string()); print('null_rows',len(n),'distinct_name_address',n[['name','address']].drop_duplicates().shape[0],'address_missing',int(n.address.isna().sum()))
if __name__=='__main__':main()
