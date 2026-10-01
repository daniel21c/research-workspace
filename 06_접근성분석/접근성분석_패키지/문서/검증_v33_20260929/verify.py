from pathlib import Path
import os,sys,json,time,gc
import pandas as pd,numpy as np
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';R=Path('D:/Research/00_박사논문_연구체계');O=R/'06_접근성분석/접근성분석_패키지'
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a10_verify as V,a11_provenance as P,a06c_delta as D,a00_config as C
Z=Q/'문서/검증_v33_20260929';t0=time.time()
def save(name,x):(Z/name).write_text(json.dumps(x,ensure_ascii=False,indent=1,default=str),encoding='utf8')
ex=json.loads((S/'execution.json').read_text(encoding='utf8'))
assert sum(x['name'].startswith('engine_') and x['exit_code']==0 for x in ex)==22
for y in [2020,2025]:
 m=json.loads((Q/f'데이터/결과/main/run_meta_{y}_100.json').read_text(encoding='utf8'))
 assert m['sfca']['items']==34
if '--reuse-independent' in sys.argv:
 import re
 for row in json.loads((S/'independent_reuse_guard.json').read_text(encoding='utf8')):
  assert P.sha256(Q/row['file'])==row['sha256'],('independent result reuse guard',row['file'])
 for status,group,name,detail in re.findall(r'^(PASS|WARN|FAIL) (2\. 계산 정확성) (2SFCA 서울 전체 독립 구현 대조 .+?) — (.*)$',(S/'verification_phase1.log').read_text(encoding='utf8'),re.M):
  V.rec(group,name,status=='PASS',detail)
 assert len(V.RES.get('2. 계산 정확성',[]))==2
V.check_inputs();V.check_run_meta();V.check_current_scope()
for n,count in [('test_engine',17),('test_release',14),('test_geometry',4)]:
 r=next(x for x in ex if x['name']==n);V.rec('2. 계산 정확성',n,r['exit_code']==0,f'{count} tests, retained actual log')
if '--reuse-independent' not in sys.argv:
 for y in [2020,2025]:V.independent_sfca(y,items=('공공도서관','어린이집','주민센터','문화','의료'),bounds=('none','lz116'));gc.collect()
diff=[];main=[];sfca_rows=0;invariant_rows=0;pop_rows=0
for f in sorted((Q/'데이터/결과').glob('*/*.csv')):
 if not f.name.startswith(('unit_access_','sfca_unit_','nat_standard_')):continue
 old=O/f.relative_to(Q);a=pd.read_csv(old);b=pd.read_csv(f)
 keys=[k for k in ['year','grid_m','T_sec','speed_kmh','retail','unit_level','unit_id','b','item_type','item','catset','cat','level'] if k in a]
 if f.parent.name=='sens_A4':a['cat']=a['cat'].replace({'체육·문화':'문화'})
 if f.name.startswith('nat_standard'):
  assert set(b.loc[b.level.eq('composite'),'item'])=={'종합(4개 단순평균)'}
  a['item']=a['item'].replace({'종합(5개 단순평균)':'종합(4개 단순평균)'})
 a=a.set_index(keys).sort_index();b=b.set_index(keys).sort_index()
 assert not b.index.duplicated().any();assert b.index.isin(a.index).all(),str(f)
 removed=a.loc[~a.index.isin(b.index)].reset_index();a=a.reindex(b.index)
 if len(removed):assert removed['cat' if 'cat' in removed else 'item'].astype(str).str.contains('체육').all()
 cols=[c for c in b if pd.api.types.is_numeric_dtype(b[c])]
 neq=~(a[cols].eq(b[cols])|(a[cols].isna()&b[cols].isna()))
 assert not neq['pop_total'].any();pop_rows+=len(b)
 row={'file':f.relative_to(Q).as_posix(),'rows':len(b),'removed_rows':len(removed),'changed_rows':int(neq.any(axis=1).sum()),'metrics':{c:{'changed_rows':int(neq[c].sum()),'max_abs':float((a[c]-b[c]).abs().max())} for c in cols}};diff.append(row)
 if f.name.startswith('sfca'):
  assert not neq.any().any(),row;sfca_rows+=len(b)
 elif f.name.startswith('nat_standard'):
  mask=b.index.get_level_values('level')!='composite'
  assert not neq.loc[mask].any().any(),row;invariant_rows+=int(mask.sum())
  z=b.reset_index();means=z[z.level.eq('category')].groupby(['unit_level','unit_id']).COV.mean()
  composite=z[z.level.eq('composite')].set_index(['unit_level','unit_id']).COV
  assert np.max(np.abs(means-composite))<1.01e-6
 else:
  cat=b.index.get_level_values('cat');mask=cat!='종합'
  if f.parent.name=='sens_A4':mask&=cat!='문화'
  assert not neq.loc[mask,['COV','PWATT_sec','pop_reach']].any().any(),row;invariant_rows+=int(mask.sum())
  k=4 if f.parent.name=='sens_A4' else 7
  assert b.MAI.dropna().between(1-1e-6,k+1e-6).all()
  means=b.loc[cat!='종합','COV'].groupby(level=[n for n in b.index.names if n!='cat']).mean()
  composite=b.loc[cat=='종합','COV'].droplevel('cat')
  assert np.max(np.abs(means-composite))<1.01e-6
 if f.parent.name=='main':
  level=b.index.get_level_values('unit_level')=='dong424';year=int(b.index.get_level_values('year')[0]);isc=f.name.startswith('sfca')
  for scope in (['all_items'] if isc else ['all_categories','종합']):
   mask=level if scope!='종합' else level&(b.index.get_level_values('cat')=='종합')
   for met in (['SFCA_per10k'] if isc else ['COV','MAI','PWATT_sec']):
    changed=mask&neq[met].to_numpy();main.append({'year':year,'scope':scope,'metric':met,'changed_rows':int(changed.sum()),'changed_dongs':int(b.loc[changed].index.get_level_values('unit_id').nunique()),'max_abs':float((a.loc[mask,met]-b.loc[mask,met]).abs().max())})
save('numerical_changes.json',{'comparisons':diff,'main':main,'sfca_unchanged_rows':sfca_rows,'category_and_B_invariant_rows':invariant_rows,'population_unchanged_rows':pop_rows})
V.rec('3. 체육 제외 회귀','생존 2SFCA 공급·결과 불변',True,f'{sfca_rows:,} CSV rows exact')
V.rec('3. 체육 제외 회귀','비체육 개별 COV/PWATT·B 불변',True,f'{invariant_rows:,} rows exact; A4 문화는 묶음 변경이므로 제외')
V.rec('3. 체육 제외 회귀','분모·7범주 종합·MAI 범위',True,f'{pop_rows:,} population rows; K=7 (A4 K=4), mean tolerance 1.01e-6')
grid=[]
for y in [2020,2025]:
 for tag,stem,keys,cols in [('main','grid_access',['grid_cd','b','cat'],['pop','r','t_min_sec']),('main','grid_sfca',['grid_cd','b','item'],['A_per10k']),('natstd_B','grid_access',['grid_cd'],None)]:
  rel=f'데이터/결과/{tag}/{stem}_{y}_100.parquet';a=pd.read_parquet(O/rel);b=pd.read_parquet(Q/rel)
  if stem=='grid_access' and tag=='main':assert not b.cat.eq('체육').any();assert b.m.dropna().between(1,7).all()
  if tag=='natstd_B':assert not any('체육' in c for c in b.columns)
  a=a.set_index(keys);b=b.set_index(keys);assert b.index.isin(a.index).all();a=a.reindex(b.index)
  cols=cols or list(b.columns)
  pd.testing.assert_frame_equal(a[cols],b[cols],check_exact=True)
  grid.append({'file':rel,'rows':len(b),'columns':cols,'unchanged':True});del a,b;gc.collect()
save('grid_regression.json',grid);V.rec('3. 체육 제외 회귀','main 격자 도달·시간·2SFCA와 B',True,f'{sum(x["rows"] for x in grid):,} rows; 6 files exact surviving values')
xb=[]
for tag,base,y in [('xb_main','main',2020),('xb_main','main',2025),('xb_net2025','sens_net2025',2020)]:
 a=pd.read_csv(Q/f'데이터/결과/{tag}/unit_access_{y}_100.csv');b=pd.read_csv(Q/f'데이터/결과/{base}/unit_access_{y}_100.csv');a=a[(a.b!='ld_other')&(a.unit_level!='ld_other')]
 keys=['unit_level','unit_id','b','cat'];cols=['pop_total','pop_reach','COV','MAI','PWATT_sec','n_cat_mai']
 pd.testing.assert_frame_equal(a.set_index(keys)[cols].sort_index(),b.set_index(keys)[cols].sort_index(),check_exact=True)
 xb.append({'tag':tag,'year':y,'rows':len(a),'unchanged_against_base':True})
save('xb_regression.json',xb);V.rec('3. 체육 제외 회귀','xb 기존 경계 대응값',True,'3 runs equal to main/net2025')
base=json.loads((S/'baseline.json').read_text(encoding='utf8'));unchanged=[]
for x in base['files']:
 if any(x['file'].startswith('데이터/입력/'+k+'/') for k in ['grid','boundary','network','ttm']):
  assert P.sha256(Q/x['file'])==x['sha256'];assert P.sha256(O/x['file'])==x['sha256'];unchanged.append(x)
save('unchanged_inputs.json',{'count':len(unchanged),'files':unchanged});V.rec('1. 입력 무결성','시설 비의존 입력 보존',len(unchanged)==1033,f'{len(unchanged)} hashes unchanged')
V.check_reliability()
V.rec('5. 적용 조건','체육 제외와 시점 근사',None,'7범주판에 체육 현재상태 선택 문제는 미적용. 시설 시점 대리·일상소매 원본 미확보·의료 종료일 근사·OSM 수록변화 한계는 유지. 조건부 연구 사용.')
verdict=V.write_report(0,0,t0)
summary={'release':P.RELEASE,'verdict':verdict,'tests':35,'engine_runs':22,'main':main,'sfca_unchanged_rows':sfca_rows,'category_B_invariant_rows':invariant_rows,'population_unchanged_rows':pop_rows,'grid_compared_rows':sum(x['rows'] for x in grid),'unchanged_inputs':len(unchanged),'scientific_fitness':'conditional use under documented source-date and retail assumptions; historical sports HOLD does not apply to active 7 categories','counts':{s:sum(r['결과']==s for k,rs in V.RES.items() if not k.startswith('_') for r in rs) for s in ['PASS','WARN','FAIL']}}
save('verification_summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
assert verdict=='PASS' and summary['counts']['FAIL']==0
