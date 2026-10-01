"""Apply audited null-only coordinate patches and verify deterministic offline output."""
import json,sys,math,shutil
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import geopandas as gpd
import pyarrow.parquet as pq
from pyproj import Transformer
from shapely.geometry import Point
from inventory import HERE,PKG,sha
from prepare import dump
from geocode_candidate import exact_match,districts,credentials,key,verified_reuse
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True
COORD=['lon','lat','x_5179','y_5179','adm_dong_cd','oa_cd','grid100_cd','inside_seoul','분석가능','coord_method']
FACILITY_COORD_META=['coord_stage','gu_coord','geocode_detail','geocode_detail2','coord_fix_note']
def grid100(x,y):
 s='가나다라마바사아자차카타파하'
 return s[int((x-700000)//100000)]+s[int((y-1300000)//100000)]+f'{int((x%100000)//100):03d}{int((y%100000)//100):03d}'
def spatial(patch):
 f=pd.DataFrame(patch);tr=Transformer.from_crs(4326,5179,always_xy=True);xs,ys=tr.transform(f.lon.values,f.lat.values)
 f['x_5179']=np.round(xs,2);f['y_5179']=np.round(ys,2)
 points=gpd.GeoDataFrame(f[[]],geometry=gpd.points_from_xy(xs,ys),crs=5179)
 b=PKG/'SGIS_인구경계_2019_2024';d=gpd.read_file(b/'03_행정구역/경계_2025_2Q/bnd_dong_00_2025_2Q/bnd_dong_00_2025_2Q.shp');d=d[d.ADM_CD.astype(str).str.startswith('11')]
 o=gpd.read_file(b/'02_집계구/경계_2025_2Q/bnd_oa_00_2025_2Q.shp');o=o[o.ADM_CD.astype(str).str.startswith('11')]
 for dst,geo,col in [('adm_dong_cd',d,'ADM_CD'),('oa_cd',o,'TOT_OA_CD')]:
  j=gpd.sjoin(points,geo[[col,'geometry']],how='left',predicate='within');j=j[~j.index.duplicated()]
  f[dst]=j[col].fillna('').astype(str).values
 f['grid100_cd']=[grid100(x,y) for x,y in zip(xs,ys)];f['inside_seoul']=f.adm_dong_cd!='';f['분석가능']=f.inside_seoul
 f['coord_method']=['candidate20260929_'+x['evidence_source']+'_'+x['provider']+'_exact_'+x['kind'] for x in patch]
 return f
def main():
 patches=json.loads((HERE/'결과/patch_manifest.json').read_text(encoding='utf-8'));offline=json.loads((HERE/'결과/patch_manifest_offline.json').read_text(encoding='utf-8'))
 assert patches==offline,'offline patch mismatch'
 osummary=json.loads((HERE/'검증/run_summary_offline.json').read_text(encoding='utf-8'));assert osummary['http_this_run']==0
 baseline=json.loads((HERE/'입력/baseline_hashes.json').read_text(encoding='utf-8'))
 assert all(sha(PKG/k)==v for k,v in baseline.items()),'original inputs changed'
 src=HERE/'입력/서울시설_2020_2025_분석용.parquet';a=pd.read_parquet(src);out=a.copy(deep=True);p=spatial(patches);ids=p.row_index.astype(int).tolist()
 assert len(set(ids))==len(ids) and len(ids)<=3026 and a.loc[ids,'lon'].isna().all() and a.loc[ids,'lat'].isna().all()
 assert p.inside_seoul.all() and np.isfinite(p[['lon','lat','x_5179','y_5179']].to_numpy()).all()
 for c in COORD:out.loc[ids,c]=p[c].values
 pd.testing.assert_frame_equal(a.drop(columns=COORD),out.drop(columns=COORD),check_exact=True)
 pd.testing.assert_frame_equal(a.loc[~a.index.isin(ids)],out.loc[~out.index.isin(ids)],check_exact=True)
 assert a.dtypes.equals(out.dtypes) and a.shape==out.shape==(606066,25)
 assert out.groupby(['시설','year']).size().equals(a.groupby(['시설','year']).size()) and len(out.groupby(['시설','year']))==66
 assert out[['facility_id','year']].duplicated().sum()==a[['facility_id','year']].duplicated().sum()==1
 # Re-check every exact match from the persisted, sanitized evidence with district geometry.
 geoms=districts();queries=json.loads((HERE/'입력/queries.json').read_text(encoding='utf-8'))
 records=json.loads((HERE/'입력/prepared_records.json').read_text(encoding='utf-8'));reuse=verified_reuse(records,geoms)
 for x in patches:
  if x['provider']=='registered':
   assert x['row_index'] in reuse and x['reuse_reference_rows']==reuse[x['row_index']]['reuse_reference_rows']
   assert (x['lon'],x['lat'])==(reuse[x['row_index']]['lon'],reuse[x['row_index']]['lat'])
  else:assert exact_match(queries[x['query']],{'points':[x['provider_point']]},geoms) is not None
 target=HERE/'결과/서울시설_2020_2025_분석용_보완후보.parquet';out.to_parquet(target,index=False)
 readback=pd.read_parquet(target);pd.testing.assert_frame_equal(out,readback,check_exact=True)
 assert pq.read_schema(src).remove_metadata().equals(pq.read_schema(target).remove_metadata())
 changed=[]
 for rel,group in p.groupby('adopted_path'):
  original=PKG/rel;data=pd.read_parquet(original);new=data.copy(deep=True)
  for _,r in group.iterrows():
   mask=new.facility_id==r.facility_id;assert mask.sum()==1 and new.loc[mask,'lon'].isna().all()
   for c in COORD:
    if c in new:
     value=str(r[c]) if isinstance(new[c].dtype,pd.StringDtype) else r[c]
     new.loc[mask,c]=value
   for c in FACILITY_COORD_META:
    if c not in new:continue
    if c=='gu_coord':value=r.gu
    elif c=='coord_stage':value='candidate20260929_verified'
    else:
     old=new.loc[mask,c].iloc[0];old='' if pd.isna(old) else str(old)
     value=(old+'; ' if old else '')+'candidate20260929:'+r.coord_method+'; evidence=patch_manifest.json#row_index='+str(r.row_index)
    new.loc[mask,c]=value
  mutable=[c for c in COORD+FACILITY_COORD_META if c in data]
  pd.testing.assert_frame_equal(data.drop(columns=mutable),new.drop(columns=mutable),check_exact=True)
  unpatched=~data.facility_id.isin(group.facility_id)
  pd.testing.assert_frame_equal(data.loc[unpatched],new.loc[unpatched],check_exact=True)
  # Snapshot only the changed source files, plus a manifest to unchanged registered inputs.
  snap=HERE/'입력/시설별'/Path(rel).parent.name/original.name;snap.parent.mkdir(parents=True,exist_ok=True)
  if not snap.exists():shutil.copyfile(original,snap)
  dest=HERE/'결과/시설별'/Path(rel).parent.name/original.name;dest.parent.mkdir(parents=True,exist_ok=True);new.to_parquet(dest,index=False,schema=pq.read_schema(original))
  csv=dest.with_suffix('.csv');new.to_csv(csv,index=False,encoding='utf-8-sig')
  assert data.dtypes.equals(new.dtypes)
  assert pq.read_schema(original).remove_metadata().equals(pq.read_schema(dest).remove_metadata())
  # Arrow field schema is checked above. Pandas reads a formerly-null object
  # boolean column as native bool once its last null has been filled.
  pd.testing.assert_frame_equal(new,pd.read_parquet(dest),check_exact=True,check_dtype=False)
  changed.append({'base':rel,'base_sha256':sha(original),'candidate':str(dest.relative_to(HERE)),'candidate_sha256':sha(dest),'csv_sha256':sha(csv),'patched_rows':len(group)})
 p.drop(columns=['provider_point','address_evidence']).to_csv(HERE/'결과/보완행_요약.csv',index=False,encoding='utf-8-sig')
 left=json.loads((HERE/'결과/unresolved.json').read_text(encoding='utf-8'));remaining=pd.DataFrame(left)
 before=pd.read_csv(HERE/'입력/미좌표_시설별.csv');fc=p.groupby(['시설','year']).size().rename('filled');table=before.merge(fc,left_on=['시설','year'],right_index=True,how='left').fillna({'filled':0});table['filled']=table.filled.astype(int);table['remaining']=table.null_rows-table.filled;table.to_csv(HERE/'결과/시설별_보완결과.csv',index=False,encoding='utf-8-sig')
 # Scan all text-like deliverables and binary outputs for exact secret bytes, never print values.
 secrets=credentials();leak_files=0
 for file in HERE.rglob('*'):
  if file.is_file() and file.suffix in ['.py','.json','.md','.csv','.parquet']:
   b=file.read_bytes();leak_files+=int(any(v.encode() in b for v in secrets.values() if len(v)>8))
 assert leak_files==0
 assert all(sha(PKG/k)==v for k,v in baseline.items())
 ledger=json.loads((HERE/'검증/http_ledger.json').read_text());assert ledger['total']<=12000
 evidence={'passed':True,'base_sha256':sha(PKG/'데이터/서울시설_2020_2025_분석용.parquet'),'candidate_sha256':sha(target),'rows':len(out),'facilities':out['시설'].nunique(),'year_groups':66,'columns':len(out.columns),'filled':len(ids),'remaining_null':int(out.lon.isna().sum()),'analysis_ready':int(out['분석가능'].sum()),'analysis_ready_pct':float(out['분석가능'].mean()*100),'base_analysis_ready':int(a['분석가능'].sum()),'non_coordinate_changes':0,'previous_valid_coordinate_changes':0,'unpatched_row_changes':0,'schema_preserved':True,'key_order_preserved':True,'offline_patch_identical':True,'offline_http_calls':0,'exact_evidence_passed':len(ids),'district_geometry_passed':len(ids),'key_leak_files':leak_files,'http':ledger,'base_files_unchanged':len(baseline),'changed_facility_files':len(changed),'remaining_reasons':remaining.reason.value_counts().to_dict()}
 dump(HERE/'검증/verification.json',evidence);dump(HERE/'결과/changed_files.json',changed)
 dump(HERE/'검증/build_hashes.json',{str(f.relative_to(HERE)):sha(f) for f in HERE.glob('*.py')});print(json.dumps(evidence,ensure_ascii=False))
if __name__=='__main__':main()
