import sys, ast, json, hashlib,time,types,heapq
from pathlib import Path
import numpy as np,pandas as pd,pyarrow.dataset as ds
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
ROOT=Path('D:/Research/00_박사논문_연구체계'); OWN=ROOT/'01_생활권_필요성';PKG=ROOT/'06_접근성분석/접근성분석_패키지/데이터';OUT=Path(__file__).parent
src=(OWN/'code/r1lib.py').read_text(encoding='utf-8'); tree=ast.parse(src)
nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Year']
ns=dict(np=np,pd=pd,ds=ds,heapq=heapq);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(OWN/'code/r1lib.py'),'exec'),ns)
Year=ns['Year']
facdefs={
 '도서관':(lambda f:f['시설'].eq('공공도서관'),900),
 '공공문화시설':(lambda f:f['시설'].eq('문화기반시설')&~f['시설_세부'].str.contains('도서관',na=False),900),
 '국공립유치원10분':(lambda f:f['시설'].eq('유치원')&f['시설_세부'].str.contains('공립|국립',na=False),600),
 '국공립어린이집5분':(lambda f:f['시설'].eq('어린이집')&f['시설_세부'].eq('국공립'),300),
 '노인이용시설':(lambda f:f['시설'].eq('노인 이용시설'),900),
 '청소년수련시설':(lambda f:f['시설'].eq('청소년수련시설'),900),
 '주민센터':(lambda f:f['시설'].eq('주민센터'),900)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
paths=[PKG/'입력/grid/grid100_master.parquet',PKG/'입력/facility/facility_2020_2025_units.parquet',ROOT/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet']
paths+=list((PKG/'입력/ttm').glob('ttm100_20*/ku=*/*.parquet'))
paths+=[ROOT/'00_공통_코어엔진/data/dong_to_official_livingzone_mapping_424.csv']
manifest=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]
(OUT/'before_inputs.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
M=pd.read_parquet(paths[0]);F=pd.read_parquet(paths[1]);raw=pd.read_parquet(paths[2]);print('grid',M.shape,'facility',F.shape,'raw',raw.shape,flush=True)
print('grid_duplicates',M.grid_cd.duplicated().sum(),'missing units',M[['dong424','lz116','ld2020','ld2025','ku']].isna().sum().to_dict(),flush=True)
print('facility_columns',F.columns.tolist(),flush=True)
gridix=pd.Series(np.arange(len(M)),index=M.grid_cd)
counts=[]
facidx={}
for year in (2020,2025):
 fy=F[(F.year==year)&F['분석가능']];facidx[year]={}
 for fac,(sel,T) in facdefs.items():
  z=fy[sel(fy)]; idx=gridix.reindex(z.grid100_cd.dropna().unique()).dropna().astype(int).to_numpy();facidx[year][fac]=np.unique(idx)
  counts.append(dict(year=year,facility=fac,rows=len(z),sites=len(idx),missing_grid=int(z.grid100_cd.isna().sum()),T=T))
pd.DataFrame(counts).to_csv(OUT/'facility_counts.csv',index=False,encoding='utf-8-sig')
rows=[];checks=[];growth=[];tstart=time.time()
for year,py in ((2020,2019),(2025,2024)):
 y=Year.__new__(Year);y.year=str(year);y.M=M[['grid_cd','dong424','lz116',f'ld{year}','ku',f'pop_{py}',f'biz_{py}','x_c','y_c']].copy();y.M.columns=['grid_cd','dong','lz','ld','ku','pop','biz','x_c','y_c'];y.gix=gridix;y.pop=y.M['pop'].to_numpy(float);y.popped=y.pop>0
 y.units={lab:pd.factorize(y.M[col])[0] for lab,col in [('동','dong'),('공식LZ','lz'),('Leiden','ld'),('구','ku')]}
 tt=ds.dataset(PKG/f'입력/ttm/ttm100_{year}',format='parquet',partitioning='hive').to_table(columns=['o_grid','d_grid','t_sec'],filter=ds.field('t_sec')<=900).to_pandas()
 o=gridix.reindex(tt.o_grid).to_numpy();d=gridix.reindex(tt.d_grid).to_numpy();ok=~(np.isnan(o)|np.isnan(d));order=np.argsort(d[ok],kind='stable');y.o=o[ok].astype(np.int64)[order];y.d=d[ok].astype(np.int64)[order];y.t=tt.t_sec.to_numpy()[ok][order];del tt,o,d,order
 y.starts=np.searchsorted(y.d,np.arange(len(M)));y.ends=np.searchsorted(y.d,np.arange(len(M)),side='right');y.fac={f:(facidx[year][f],T) for f,(_,T) in facdefs.items()}
 print('loaded',year,'population',y.pop.sum(),'edges',len(y.o),'invalid_edges',int((~ok).sum()),'elapsed',round(time.time()-tstart),flush=True)
 W=pd.read_csv(OWN/f'output/표4.1-9_시설별_창_{year}.csv')
 for fac,(_,T) in facdefs.items():
  # Independent edge membership and weighted group aggregation.
  mask=np.isin(y.d,facidx[year][fac])&(y.t<=T);r0=np.zeros(len(M),bool);r0[np.unique(y.o[mask])]=True
  assert np.array_equal(r0,y.reach(fac))
  dd=np.bincount(y.units['동'],weights=y.pop);num=np.bincount(y.units['동'],weights=y.pop*r0);Cd=np.divide(num,dd,out=np.zeros_like(num),where=dd>0);order=np.argsort(Cd[dd>0]);xx=Cd[dd>0][order];ww=dd[dd>0][order];tau=.6*xx[np.searchsorted(ww.cumsum(),ww.sum()/2)]
  K=len(facidx[2025][fac])-len(facidx[2020][fac]);K=K if K>=3 else max(3,round(.1*len(facidx[2020][fac])))
  cand=y.candidates(fac);p0,_,_=y.place(r0,None,0,K,cand);cov0=y.cov_after(r0,p0,K);gain0=np.dot(y.pop,cov0&~r0)
  wwtab=W[W['시설']==fac]; checks.append(dict(year=year,fac=fac,C0_error=float(abs(y.cov(r0)-wwtab['서울C'].iloc[0])),tau_error=float(abs(tau-wwtab['τ'].iloc[0])),K=K,candidate_count=len(cand)))
  for lv in ('동','공식LZ','Leiden','구'):
   u=y.units[lv];pk,km,sf=y.place(r0,u,tau,K,cand,kcap=max(700,4*K));c=y.cov_after(r0,pk,K);Cu,den=y.unit_cov(u,c);v=den>0;p0Cu,_=y.unit_cov(u,cov0)
   row=dict(year=year,facility=fac,variant='saved_algorithm',level=lv,K=K,T=T,tau=tau,Kmin=km,gain=float(np.dot(y.pop,c&~r0)),eff=float(np.dot(y.pop,c&~r0)/gain0),FGT0_P0=float(den[v&(p0Cu<tau)].sum()/den[v].sum()),FGT0_P1=float(den[v&(Cu<tau)].sum()/den[v].sum()),picks=len(pk[:K]))
   saved=wwtab[wwtab.tag==lv].iloc[0];row['saved_Kmin']=None if pd.isna(saved.K_min) else float(saved.K_min);row['saved_eff_error']=float(abs(row['eff']-saved['효율유지율']));rows.append(row)
  # Same selected sites independently reevaluated with requested T; then corrected greedy.
  if T<900:
   y.cover_of=types.MethodType(lambda self,j:self.o[self.starts[j]:self.ends[j]][self.t[self.starts[j]:self.ends[j]]<=T],y)
   fixed_p0=y.cov_after(r0,p0,K);p0new,_,_=y.place(r0,None,0,K,cand);new_cov0=y.cov_after(r0,p0new,K);new_gain0=float(np.dot(y.pop,new_cov0&~r0))
   for lv in ('동','공식LZ','Leiden','구'):
    u=y.units[lv];pk,km,sf=y.place(r0,u,tau,K,cand,kcap=max(700,4*K));c=y.cov_after(r0,pk,K);Cu,den=y.unit_cov(u,c);v=den>0;p0Cu,_=y.unit_cov(u,new_cov0)
    rows.append(dict(year=year,facility=fac,variant='correct_T',level=lv,K=K,T=T,tau=tau,Kmin=km,gain=float(np.dot(y.pop,c&~r0)),eff=float(np.dot(y.pop,c&~r0)/new_gain0),FGT0_P0=float(den[v&(p0Cu<tau)].sum()/den[v].sum()),FGT0_P1=float(den[v&(Cu<tau)].sum()/den[v].sum()),picks=len(pk[:K]),bug_P0_gain=float(gain0),same_picks_correct_gain=float(np.dot(y.pop,fixed_p0&~r0)),correct_P0_gain=new_gain0))
   del y.cover_of
  if year==2020:
   new=np.setdiff1d(facidx[2025][fac],facidx[2020][fac]);lost=np.setdiff1d(facidx[2020][fac],facidx[2025][fac]);off_cand=np.setdiff1d(new,cand)
   growth.append(dict(facility=fac,net=K,new_sites=len(new),removed_sites=len(lost),new_outside_candidate=len(off_cand),unreachable_new=int((y.ends[new]==y.starts[new]).sum())))
  pd.DataFrame(rows).to_csv(OUT/'recomputed_fixed_units.csv',index=False,encoding='utf-8-sig');pd.DataFrame(checks).to_csv(OUT/'baseline_checks.csv',index=False,encoding='utf-8-sig');pd.DataFrame(growth).to_csv(OUT/'growth.csv',index=False,encoding='utf-8-sig')
  print('DONE',year,fac,'K',K,'T',T,'elapsed',round(time.time()-tstart),flush=True)
 print('YEAR DONE',year,flush=True)
print(pd.DataFrame(rows).to_string(index=False),flush=True)
