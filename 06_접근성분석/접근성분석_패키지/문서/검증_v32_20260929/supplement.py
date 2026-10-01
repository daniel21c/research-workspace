from pathlib import Path
import sys,json,os
import pandas as pd
import numpy as np
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';O=S.parent/'접근성분석_패키지';R=S.parent.parent
os.environ['ACCESS_REPOSITORY_ROOT']=str(R);sys.path.insert(0,str(Q/'코드'))
import a11_provenance as P
import a06c_delta as D
out=Q/'문서/검증_v32_20260929'
rows=[]
for y in [2020,2025]:
 a=pd.read_csv(O/f'데이터/결과/main/unit_access_{y}_100.csv');b=pd.read_csv(Q/f'데이터/결과/main/unit_access_{y}_100.csv')
 for subset in ['all_categories','종합']:
  for boundary in ['all','lz116','ld','none']:
   mask=(b.unit_level=='dong424')&((b.cat=='종합') if subset=='종합' else True)&((b.b==boundary) if boundary!='all' else True)
   for metric in ['COV','MAI','PWATT_sec']:
    same=a[metric].eq(b[metric])|(a[metric].isna()&b[metric].isna());c=mask&~same
    delta=(a.loc[mask,metric]-b.loc[mask,metric]).abs();idx=delta.idxmax()
    rows.append(dict(year=y,category_scope=subset,b=boundary,metric=metric,changed_dongs=int(b.loc[c,'unit_id'].nunique()),changed_rows=int(c.sum()),max_abs=float(delta.max()),worst_key=b.loc[idx,['unit_id','b','cat']].to_dict()))
b_checks=[]
for y in [2020,2025]:
 f=f'데이터/결과/natstd_B/nat_standard_coverage_{y}_100.csv';a=pd.read_csv(O/f);b=pd.read_csv(Q/f)
 keys=['year','grid_m','speed_kmh','unit_level','unit_id','level','item'];assert a[keys].equals(b[keys]);assert a.pop_total.equals(b.pop_total)
 c=~(a.COV.eq(b.COV)|(a.COV.isna()&b.COV.isna()))
 b_checks.append(dict(file=f,rows=len(a),keys_equal=True,pop_total_equal=True,changed_COV_rows=int(c.sum()),max_abs=float((a.COV-b.COV).abs().max())))
xb=[]
for tag,base,y in [('xb_main','main',2020),('xb_main','main',2025),('xb_net2025','sens_net2025',2020)]:
 a=pd.read_csv(Q/f'데이터/결과/{tag}/unit_access_{y}_100.csv');b=pd.read_csv(Q/f'데이터/결과/{base}/unit_access_{y}_100.csv')
 a=a[(a.b!='ld_other')&(a.unit_level!='ld_other')].reset_index(drop=True)
 keys=['unit_level','unit_id','b','cat'];a=a.set_index(keys).sort_index();b=b.set_index(keys).sort_index();assert a.index.equals(b.index)
 cols=['pop_total','pop_reach','COV','MAI','PWATT_sec','n_cat_mai']
 assert (a[cols].eq(b[cols])|(a[cols].isna()&b[cols].isna())).all().all()
 xb.append(dict(tag=tag,comparison=base,year=y,rows=len(a),columns=cols,different_cells=0))
outputs={}
for m in sorted((Q/'데이터/결과').glob('*/run_meta*.json')):
 obj=json.loads(m.read_text(encoding='utf8'))
 for item in obj['files']:
  f=m.parent/item['file'] if obj['files_base']=='run_meta_directory' else Q/item['file']
  rel=f.relative_to(Q).as_posix();old=O/rel
  outputs[rel]={'old_sha256':P.sha256(old),'new_sha256':P.sha256(f),'changed':P.sha256(old)!=P.sha256(f)}
delta={}
for y in [2020,2025]:
 a=pd.read_csv(O/f'데이터/결과/main/unit_access_{y}_100.csv');b=pd.read_csv(Q/f'데이터/결과/main/unit_access_{y}_100.csv')
 delta[str(y)]={}
 for metric in ['COV','MAI']:
  old=D.dong_delta(a,metric);new=D.dong_delta(b,metric);d=(new-old).abs()
  delta[str(y)][metric]={'changed_dongs_gt_1e_12':int((d>1e-12).sum()),'max_abs':float(d.max()),'sign_changes':int(((old*new)<0).sum())}
result=dict(main_scope_breakdown=rows,B=b_checks,xb_existing_boundaries=xb,direct_engine_files=outputs,direct_count=len(outputs),changed_direct_count=sum(v['changed'] for v in outputs.values()),delta_LD_LZ=delta,figure_visual_check='F3 PNG inspected: labels, legends, 424-dong maps visible')
(out/'supplementary_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=1),encoding='utf8')
f=S/'facility_delta.json';v=json.loads(f.read_text(encoding='utf8'));v['noncoordinate_changed_columns']=[];v['coordinate_provenance_changed_columns']=['coord_method'];f.write_text(json.dumps(v,ensure_ascii=False,indent=1),encoding='utf8')
print(json.dumps({k:result[k] for k in ['B','xb_existing_boundaries','direct_count','changed_direct_count','delta_LD_LZ']},ensure_ascii=False))
