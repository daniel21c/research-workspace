import sys,json,hashlib,ast
from pathlib import Path
import pandas as pd,numpy as np
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
OWN=Path('D:/Research/00_박사논문_연구체계/01_생활권_필요성');OUT=Path(__file__).parent
tables=[];details={}
for p in sorted(OWN.rglob('*.csv')):
 key=str(p.relative_to(OWN))
 try:d=pd.read_csv(p)
 except pd.errors.EmptyDataError:
  tables.append(dict(file=key,rows=0,columns=0,duplicate_full_rows=0,null_cells=0,error='empty CSV'));continue
 tables.append(dict(file=key,rows=len(d),columns=len(d.columns),duplicate_full_rows=int(d.duplicated().sum()),null_cells=int(d.isna().sum().sum())));details[key]=dict(columns=d.columns.tolist(),head=d.head(2).to_dict('records'))
pd.DataFrame(tables).to_csv(OUT/'table_inventory.csv',index=False,encoding='utf-8-sig')
(OUT/'table_schemas.json').write_text(json.dumps(details,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(pd.DataFrame(tables).to_string(index=False))
ww=[];bands=[]
for p in sorted((OWN/'output').glob('표4.1-9_시설별_창_*.csv')):
 d=pd.read_csv(p)
 for fac,z in d.groupby('시설',sort=False):
  K=z.K.iloc[0];a=[];b=[]
  for tag,zz in z.groupby('tag',sort=False):
   km=zz.K_min.median();f=zz['FGT0_P0후'].median();k=zz.k.iloc[0]
   if tag not in ('공식LZ','Leiden'):
    if km<=K:a.append(k)
    if f>=.01:b.append(k)
   if tag.startswith('rand'):
    ww.append(dict(file=p.name,facility=fac,tag=tag,n=len(zz),n_rep=zz.rep.nunique(),n_Kmin_missing=int(zz.K_min.isna().sum()),median_Kmin=km,median_FGT0=f,joint_pass=int(((zz.K_min<=K)&(zz['FGT0_P0후']>=.01)).sum()),actual_n_units=sorted(zz.n_units.unique().tolist())))
  bands.append(dict(file=p.name,facility=fac,K=int(K),k_bind=min(b) if b else None,k_afford=max(a) if a else None))
pd.DataFrame(ww).to_csv(OUT/'window_checks.csv',index=False,encoding='utf-8-sig');pd.DataFrame(bands).to_csv(OUT/'window_summary.csv',index=False,encoding='utf-8-sig')
print('WINDOW',pd.DataFrame(bands).to_string(index=False))
for p in sorted((OWN/'output').glob('정수해*.csv')):
 d=pd.read_csv(p);print('MILP',p.name);print(d.to_string(index=False))
print('META',[(p.name,json.loads(p.read_text(encoding='utf-8'))) for p in (OWN/'output').glob('*meta.json')])
for p in (OWN/'output').glob('*4단위비교행렬*csv'):
 d=pd.read_csv(p);print(p.name,d.columns.tolist());print(d[d.iloc[:,1].astype(str).str.contains('실제|same',case=False)].to_string(index=False))
print('MD_FILES')
for p in OWN.rglob('*.md'):print(str(p.relative_to(OWN)),len(p.read_text(encoding='utf-8').splitlines()))
