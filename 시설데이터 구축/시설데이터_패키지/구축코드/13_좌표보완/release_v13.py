"""Offline facility-v1.3 build and deterministic verification.

No credentials or networking. Existing adopted inputs are immutable during staging.
The original 87-row candidate is retained as evidence; four cached repairs and two
unsupported-coordinate exclusions are applied on top of it. Promotion uses the
separate, explicit-file PowerShell manifest workflow.
"""
import argparse,hashlib,json,math,os,shutil,subprocess,sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pyproj import Transformer
HERE=Path(__file__).resolve().parent;PKG=HERE.parent.parent
CAND=PKG/'보완후보_20260929';DATA=PKG/'데이터';STAGE=HERE/'staging'
sys.path.insert(0,str(CAND));sys.dont_write_bytecode=True
from build_verify import spatial,COORD,FACILITY_COORD_META
from geocode_candidate import exact_match,districts
from address_rules import parse_addr
sys.stdout.reconfigure(encoding='utf-8')
BASE_SHA='b87ed1cc198bec94d21808b2eb8d0314b6b4b45662782db019a96f3804aef39f'
ANALYSIS='서울시설_2020_2025_분석용.parquet';MERGED='통합_신뢰도상_2020_2025.parquet'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def dump(p,z):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(z,ensure_ascii=False,indent=2),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def base_for(rel):
 p=CAND/'입력/시설별'/Path(rel).parent.name/Path(rel).name
 if p.exists():return p
 p=HERE/'입력'/rel
 return p if p.exists() else PKG/rel
def builder(out,override=None):
 out.mkdir(parents=True,exist_ok=True);env=os.environ.copy()
 for k in ['FAC_T_DIR','FAC_OVERRIDE_DIR','FAC_V1_DIR','OUT_DIR','OUT_CSV']:env.pop(k,None)
 env.update(OUT_DIR=str(out),PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
 if override:env['FAC_OVERRIDE_DIR']=str(override)
 logs=[]
 for name in ['build_통합.py','build_분석용.py']:
  p=subprocess.run([sys.executable,str(PKG/'구축코드'/name)],env=env,capture_output=True,text=True,encoding='utf-8')
  assert p.returncode==0,f'{name} failed ({p.returncode})'
  logs.append(name+': PASS')
 return logs
def stage():
 current=sha(DATA/ANALYSIS)
 prior_manifest=read(HERE/'promotion_manifest.json') if (HERE/'promotion_manifest.json').exists() else None
 released=next((r['new_sha256'] for r in prior_manifest['files'] if Path(r['relative_path']).name==ANALYSIS),'') if prior_manifest else ''
 assert current in [BASE_SHA,released],'registered input changed'
 STAGE.mkdir(parents=True,exist_ok=True)
 inputs={str(p.relative_to(PKG)):sha(base_for(str(p.relative_to(PKG)))) for p in (DATA/'시설별').rglob('*.parquet')}
 for p in (PKG/'구축코드/03_교육교통공원상가/retail_daily').glob('facilities_*_01.parquet'):inputs[str(p.relative_to(PKG))]=sha(p)
 dump(HERE/'입력/accepted_baseline_hashes.json',inputs)
 # Snapshot the public evidence independently of the old candidate's review files.
 for f in ['parser_risk_summary.json','parser_cache_summary.json','parser_cache_evidence.json','parser_provenance_rows.json','targeted_repairs.json']:
  dst=HERE/'근거'/f;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(CAND/'승격검토'/f,dst)
 changed=read(CAND/'결과/changed_files.json');relpaths=set()
 for r in changed:
  rel=Path(r['base']);assert sha(base_for(rel))==r['base_sha256']
  dest=STAGE/rel.relative_to('데이터');dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(CAND/r['candidate'],dest);shutil.copyfile((CAND/r['candidate']).with_suffix('.csv'),dest.with_suffix('.csv'));relpaths.add(str(rel))
 baseline=pd.read_parquet(CAND/'입력'/ANALYSIS)
 expected=pd.read_parquet(CAND/'결과/서울시설_2020_2025_분석용_보완후보.parquet')
 risk={r['row_index']:r for r in read(HERE/'근거/parser_provenance_rows.json')};repairs=read(HERE/'근거/targeted_repairs.json')
 good=[];geoms=districts();tr=Transformer.from_crs(4326,5179,always_xy=True)
 for r in repairs:
  idx=r['row_index'];r['facility_id']=risk[idx]['facility_id'];r['year']=risk[idx]['year'];r['facility']=risk[idx]['facility'];r['adopted_path']=risk[idx]['trace']['path']
  r['old_coordinate']={c:baseline.loc[idx,c].item() if isinstance(baseline.loc[idx,c],np.generic) else baseline.loc[idx,c] for c in COORD}
  if r['matches']:
   first=r['matches'][0];c=next(c for c in parse_addr(first['query']) if c['query']==first['query']);c['gu']=first['gu']
   assert exact_match(c,{'points':[first['point']]},geoms)
   xy=tr.transform(first['point']['lon'],first['point']['lat']);assert max(math.dist(xy,tr.transform(m['point']['lon'],m['point']['lat'])) for m in r['matches'])<=15
   assert all(sha(PKG/m['path'])==m['sha256'] for m in r['matches'])
   r['new_point']=first['point'];r['move_m']=math.dist(xy,tr.transform(baseline.loc[idx,'lon'],baseline.loc[idx,'lat']))
   good.append({'row_index':idx,'lon':first['point']['lon'],'lat':first['point']['lat'],'evidence_source':'parser_repair_cache','provider':first['provider'],'kind':first['kind']})
 points=spatial(good).set_index('row_index')
 for r in repairs:
  idx=r['row_index'];rel=Path(r['adopted_path']);original=base_for(rel)
  snap=HERE/'입력'/rel;snap.parent.mkdir(parents=True,exist_ok=True)
  if not snap.exists():shutil.copyfile(original,snap)
  dest=STAGE/rel.relative_to('데이터');dest.parent.mkdir(parents=True,exist_ok=True)
  frame=pd.read_parquet(dest if dest.exists() else original);mask=frame.facility_id==r['facility_id'];assert mask.sum()==1
  if r['matches']:
   values=points.loc[idx,COORD].to_dict();values['coord_method']='facility_v13_cached_full_address_exact'
  else:
   values={c:np.nan for c in ['lon','lat','x_5179','y_5179']}
   values.update({c:'' for c in ['adm_dong_cd','oa_cd','grid100_cd']});values.update(inside_seoul=False,분석가능=False,coord_method='unresolved_parser_substring_v13')
  for c,v in values.items():
   expected.loc[idx,c]=v
   if c in frame:frame.loc[mask,c]=str(v) if isinstance(frame[c].dtype,pd.StringDtype) and not pd.isna(v) else v
  for c in FACILITY_COORD_META:
   if c not in frame:continue
   if c=='coord_stage':value='facility_v13_parser_review'
   elif c=='gu_coord':value=r['matches'][0]['gu'] if r['matches'] else ''
   else:
    old=frame.loc[mask,c].iloc[0];old='' if pd.isna(old) else str(old)
    value=old+'; facility-v1.3 '+r['decision']+'; evidence=구축코드/13_좌표보완/근거/repairs.json#row_index='+str(idx)
   frame.loc[mask,c]=value
  frame.to_parquet(dest,index=False,schema=pq.read_schema(original));frame.to_csv(dest.with_suffix('.csv'),index=False,encoding='utf-8-sig');relpaths.add(str(rel))
 dump(HERE/'근거/repairs.json',repairs)
 builder(STAGE,STAGE/'시설별')
 actual=pd.read_parquet(STAGE/ANALYSIS);pd.testing.assert_frame_equal(expected,actual,check_exact=True)
 ids={p['row_index'] for p in read(CAND/'결과/patch_manifest.json')}|{r['row_index'] for r in repairs}
 pd.testing.assert_frame_equal(baseline.drop(columns=COORD),actual.drop(columns=COORD),check_exact=True)
 pd.testing.assert_frame_equal(baseline.loc[~baseline.index.isin(ids)],actual.loc[~actual.index.isin(ids)],check_exact=True)
 assert pq.read_schema(DATA/ANALYSIS).remove_metadata().equals(pq.read_schema(STAGE/ANALYSIS).remove_metadata())
 assert actual.shape==(606066,25) and actual['시설'].nunique()==33 and len(actual.groupby(['시설','year']))==66
 assert actual[['시설','facility_id','year']].duplicated().sum()==1
 assert actual.lon.isna().sum()==2941 and actual['분석가능'].sum()==603066
 adoption_snapshot=HERE/'입력/채택목록_v1.2.csv'
 if not adoption_snapshot.exists():
  assert current==BASE_SHA
  shutil.copyfile(DATA/'채택목록.csv',adoption_snapshot)
 adoption=pd.read_csv(adoption_snapshot)
 for rel in sorted(relpaths):
  p=Path(rel);new=pd.read_parquet(STAGE/p.relative_to('데이터'));old=pd.read_parquet(base_for(rel));mutable=[c for c in COORD+FACILITY_COORD_META if c in old]
  pd.testing.assert_frame_equal(old.drop(columns=mutable),new.drop(columns=mutable),check_exact=True,check_dtype=False)
  assert pq.read_schema(base_for(rel)).remove_metadata().equals(pq.read_schema(STAGE/p.relative_to('데이터')).remove_metadata())
  fac=p.parent.name;year=p.stem.split('_')[-2];mask=adoption['시설']==fac;assert mask.sum()==1,(fac,mask.sum())
  oldnote=adoption.loc[mask,'보정_'+year].iloc[0];oldnote='' if pd.isna(oldnote) else str(oldnote)
  adoption.loc[mask,'보정_'+year]=oldnote+('; ' if oldnote else '')+'13_좌표보완/release_v13.py (facility-v1.3)'
  adoption.loc[mask,'좌표율_'+year]=round(float(new.lon.notna().mean()*100),2)
 adoption.to_csv(STAGE/'채택목록.csv',index=False,encoding='utf-8-sig')
 summary={'release':'facility-v1.3','PASS':True,'file':'데이터/'+ANALYSIS,'sha256':sha(STAGE/ANALYSIS),'rows':606066,'n_facility':33,'all_33_both_years':True,'columns':25,'dup_ok':True,'allowed_duplicate':['버스정류장','BUS_15143',2020],'baseline_sha256':BASE_SHA,'new_null_coordinates_filled':87,'previous_coordinates_corrected':4,'unsupported_coordinates_cleared':2,'remaining_null_coordinates':2941,'analysis_ready':603066,'분석가능_pct':float(actual['분석가능'].mean()*100),'noncoordinate_attribute_changes':0,'unaffected_row_changes':0,'schema_and_key_order_preserved':True,'changed_adopted_parquets':len(relpaths),'new_http_calls_this_release':0,'candidate_http_calls_prior_task':582,'exact_cache_repair_rows':4,'parser_review_checked_rows':29032,'parser_review_candidate_rows':1295,'parser_review_strict_cache_supported':1234,'parser_review_confirmed_repairs_or_exclusions':6,'parser_review_other_retained':55,'integrated_rows':len(pd.read_parquet(STAGE/MERGED)),'integrated_excludes_retail':True,'adopted_to_analysis_exact':True,'past_audit_checks':'v1.2 full audit is historical evidence; this release rechecks changed rows and core invariants.','consumer_status':'06 access-engine-v3.1 still uses v1.2; rebuild and provenance refresh required before claiming v1.3 results.'}
 assert summary['integrated_rows']==550509
 dump(STAGE/'검증결과.json',summary)
 targets=[]
 for rel in sorted(relpaths):targets.extend([Path(rel),Path(rel).with_suffix('.csv')])
 targets += [Path('데이터')/n for n in [ANALYSIS,MERGED,'_요약_시설별_수_좌표.csv','채택목록.csv','검증결과.json']]
 manifest=[]
 for rel in targets:
  old=PKG/rel;new=STAGE/rel.relative_to('데이터')
  prior=next((r for r in prior_manifest['files'] if r['relative_path']==str(rel)),None) if prior_manifest else None
  manifest.append({'relative_path':str(rel),'old_sha256':prior['old_sha256'] if prior else sha(old),'old_bytes':prior['old_bytes'] if prior else old.stat().st_size,'new_sha256':sha(new),'new_bytes':new.stat().st_size,'staged_relative_path':str(new.relative_to(PKG))})
 assert len(manifest)==55
 dump(HERE/'promotion_manifest.json',{'release':'facility-v1.3','files':manifest,'file_count':len(manifest),'old_total_bytes':sum(r['old_bytes'] for r in manifest),'new_total_bytes':sum(r['new_bytes'] for r in manifest)})
 dump(HERE/'stage_verification.json',summary)
 print(json.dumps(summary,ensure_ascii=False))
def verify(output=None):
 manifest=read(HERE/'promotion_manifest.json');baseline=read(HERE/'입력/accepted_baseline_hashes.json');changed={r['relative_path']:r for r in manifest['files']}
 assert all(sha(PKG/r['relative_path'])==r['new_sha256'] for r in manifest['files'])
 assert all(sha(PKG/k)==v for k,v in baseline.items() if k not in changed),'unrelated adopted input changed'
 # Rebuild in a new output directory; never rewrites canonical distribution.
 out=Path(output).resolve() if output else HERE/'rebuild_check'
 assert out.is_relative_to(HERE.resolve()) and out!=HERE.resolve()
 builder(out)
 for n in [ANALYSIS,MERGED,'_요약_시설별_수_좌표.csv']:assert sha(out/n)==sha(DATA/n),n
 a=pd.read_parquet(DATA/ANALYSIS);old=pd.read_parquet(CAND/'입력'/ANALYSIS)
 ids={p['row_index'] for p in read(CAND/'결과/patch_manifest.json')}|{r['row_index'] for r in read(HERE/'근거/repairs.json')}
 pd.testing.assert_frame_equal(old.drop(columns=COORD),a.drop(columns=COORD),check_exact=True)
 pd.testing.assert_frame_equal(old.loc[~old.index.isin(ids)],a.loc[~a.index.isin(ids)],check_exact=True)
 # Coherent missing coordinates and finite valid coordinate pairs.
 assert a.lon.isna().equals(a.lat.isna()) and a.lon.isna().equals(a.x_5179.isna()) and a.lon.isna().equals(a.y_5179.isna())
 assert np.isfinite(a.loc[a.lon.notna(),['lon','lat','x_5179','y_5179']].to_numpy()).all()
 assert not a.loc[a.lon.isna(),'분석가능'].any()
 for r in read(HERE/'근거/repairs.json'):
  if not r['matches']:
   z=a.loc[r['row_index']];assert not z['분석가능'] and not z.inside_seoul and pd.isna(z.lon) and all(z[c]=='' for c in ['adm_dong_cd','oa_cd','grid100_cd'])
 report={'PASS':True,'sha256':sha(DATA/ANALYSIS),'rows':len(a),'analysis_ready':int(a['분석가능'].sum()),'remaining_null':int(a.lon.isna().sum()),'rebuild_analysis_byte_identical':True,'rebuild_integrated_byte_identical':True,'rebuild_summary_byte_identical':True,'unchanged_other_adopted_inputs':sum(k not in changed for k in baseline),'old_noncoordinate_attributes_preserved':True,'unaffected_rows_preserved':True,'offline_http_calls':0,'replacement_file_count':len(manifest['files'])}
 dump(HERE/'final_verification.json',report);print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','verify']);p.add_argument('--output');args=p.parse_args()
 stage() if args.action=='stage' else verify(args.output)
