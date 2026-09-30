import sys,json,ast,types
from pathlib import Path
import numpy as np,pandas as pd
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
OUT=Path(__file__).parent;R=Path('D:/Research/00_박사논문_연구체계');OWN=R/'01_생활권_필요성';PKG=R/'06_접근성분석/접근성분석_패키지'
before=json.loads((OUT/'before_inputs.json').read_text(encoding='utf-8'));manifest=pd.read_csv(PKG/'데이터/manifest_sha256.csv');lookup=dict(zip(manifest.file,manifest.sha256));rows=[]
for v in before:
 p=Path(v['path'])
 if p.is_relative_to(PKG):
  key=p.relative_to(PKG).as_posix();expected=lookup.get(key);rows.append(dict(file=key,expected=expected,actual=v['sha256'],match=(expected==v['sha256']) if expected else None))
pd.DataFrame(rows).to_csv(OUT/'manifest_checks.csv',index=False,encoding='utf-8-sig')
print('MANIFEST',len(rows),'matched',sum(x['match'] is True for x in rows),'missing',sum(x['expected'] is None for x in rows),'bad',[x for x in rows if x['match'] is False])
source=json.loads((PKG/'데이터/입력/facility/facility_2020_2025_units.source.json').read_text(encoding='utf-8'));print('SOURCE',source)
raw=pd.read_parquet(R/source['source']);f=pd.read_parquet(PKG/'데이터/입력/facility/facility_2020_2025_units.parquet');common=[c for c in raw if c in f];print('RAW JOIN',raw.shape,f.shape,len(common),'common_equal',raw[common].equals(f[common]),'columns',raw.columns.tolist())
for v in before[:3]:print('INPUT',v)
M=pd.read_parquet(PKG/'데이터/입력/grid/grid100_master.parquet');reg=pd.read_csv(R/'00_공통_코어엔진/data/dong_to_official_livingzone_mapping_424.csv');gm=M.groupby('dong424')[['lz116','ld2020','ld2025','ku']].first();print('UNITCOUNTS',M[['dong424','lz116','ld2020','ld2025','ku']].nunique().to_dict());print('LZ attached_match',np.array_equal(gm.lz116,reg.set_index('Dong').life_zone_id.reindex(gm.index)))
for y in (2020,2025):
 p=R/f'00_공통_코어엔진/output/leiden/{y}/metrics/leiden_mapping_{y}.csv';d=pd.read_csv(p).set_index('Dong');print('LD match',y,np.array_equal(gm[f'ld{y}'],d.global_community_id.reindex(gm.index)))
tree=ast.parse((OWN/'code/r1lib.py').read_text(encoding='utf-8'));cl=next(n for n in tree.body if isinstance(n,ast.ClassDef));fn=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='random_partition')
xtree=ast.parse((R/'00_공통_코어엔진/exploration/xcommon.py').read_text(encoding='utf-8'));xfn=[n for n in xtree.body if isinstance(n,ast.FunctionDef) and n.name in ('random_connected_partition','random_balanced_partition')];xns={'np':np};exec(compile(ast.Module(body=xfn,type_ignores=[]),'isolated-random','exec'),xns)
ns={'np':np,'pd':pd,'X':types.SimpleNamespace(**{k:v for k,v in xns.items() if k.startswith('random_')})};exec(compile(ast.Module(body=[fn],type_ignores=[]),'isolated-method','exec'),ns)
n=10;g=types.SimpleNamespace(n=n,nodes=np.arange(n),adj=[{j for j in (i-1,i+1) if 0<=j<n} for i in range(n)],pop=np.arange(1,n+1));obj=types.SimpleNamespace(off_k=pd.Series({1:3}),n_dong_ku=pd.Series({1:n}),dong_gdf=pd.DataFrame(index=range(n)),kg={1:g})
for seed in (1,7,20260927):
 a=ns['random_partition'](obj,3,np.random.default_rng(seed),'dong');b=ns['random_partition'](obj,3,np.random.default_rng(seed),'free');print('NULL SAME SEED',seed,a.equals(b),a.tolist())
picks=json.loads((OWN/'output/exp5_picks.json').read_text(encoding='cp949'));p0=np.array(picks['2020']['P0']);p1=np.array(picks['2020']['P1 공식LZ']);u,codes=pd.factorize(M.ku)
q=pd.DataFrame([dict(ku=int(k),old_diff=len(set(np.where(u[p0]==i)[0])^set(np.where(u[p1]==i)[0])),correct_diff=len(set(p0[u[p0]==i])^set(p1[u[p1]==i]))) for i,k in enumerate(codes)])
q.to_csv(OUT/'case_selection_check.csv',index=False,encoding='utf-8-sig');print('CASE',q.sort_values('correct_diff',ascending=False).head(8).to_string(index=False));print('OLD',q.sort_values('old_diff',ascending=False).head(4).to_string(index=False))
d=pd.read_csv(OWN/'output/부록_IFR_접근성_상관.csv');print('IFR',d.columns.tolist());print(d.head(18).to_string(index=False))
print('BASELINE MAX',pd.read_csv(OUT/'baseline_checks.csv')[['C0_error','tau_error']].max().to_dict());print('EFF MAX',pd.read_csv(OUT/'recomputed_fixed_units.csv').query('variant=="saved_algorithm"').saved_eff_error.max())
