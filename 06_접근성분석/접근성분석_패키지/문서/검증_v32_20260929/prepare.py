from pathlib import Path
import json,hashlib,shutil,subprocess,sys
import pandas as pd
S=Path(__file__).resolve().parent;R=S.parent.parent;P=S.parent/'접근성분석_패키지';Q=S/'접근성분석_패키지'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
base={p.relative_to(P).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in P.rglob('*') if p.is_file()}
(S/'baseline.json').write_text(json.dumps(base,ensure_ascii=False,indent=1),encoding='utf8')
for n in ['README.md','데이터_배포목록.md','공유_안내.md']:shutil.copy2(R/n,S/('hub_before_'+n))
shutil.copytree(P,Q,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# Historical record of replaced run metadata and current release documentation.
h=Q/'문서/검증_v32_20260929/이전_v31';h.mkdir(parents=True)
for f in [P/'README.md',P/'데이터/release_provenance.json',P/'데이터/검증결과.json',P/'데이터/manifest_sha256.csv']+list((P/'문서').glob('*.md'))+list((P/'데이터/결과').glob('*/run_meta*.json')):
 dst=h/f.relative_to(P);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
new=R/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet'
old=Path(r'D:\Research\_archive\facility-v1.2_superseded_20260929\데이터\서울시설_2020_2025_분석용.parquet')
assert sha(new)=='1a097e954a134d4440a64bf668252943de0ace6a0bc38ec5b5f499c36be17a47'
assert sha(old)=='b87ed1cc198bec94d21808b2eb8d0314b6b4b45662782db019a96f3804aef39f'
a=pd.read_parquet(old);b=pd.read_parquet(new);assert a.shape==b.shape==(606066,25)
assert list(a.columns)==list(b.columns)
keys=['시설','facility_id','year'];assert a[keys].equals(b[keys])
changed=~a.eq(b).fillna(False).where(~(a.isna()&b.isna()),True).all(axis=1)
coord=['lon','lat','x_5179','y_5179','inside_seoul','분석가능','adm_dong_cd','oa_cd','grid100_cd']
noncoord=[c for c in a.columns if c not in coord]
diffcols={c:int((~((a[c]==b[c]).fillna(False)|(a[c].isna()&b[c].isna()))).sum()) for c in a.columns}
report={'version':'facility-v1.3','old_sha256':sha(old),'new_sha256':sha(new),'shape':b.shape,'analysis_ready':int(b['분석가능'].sum()),'changed_rows':int(changed.sum()),'changed_by_type':b.loc[changed].groupby(['시설','year']).size().reset_index(name='n').to_dict('records'),'changed_columns':diffcols,'noncoordinate_changed_columns':[c for c in noncoord if diffcols[c]],'old_path':str(old)}
assert report['analysis_ready']==603066
(S/'facility_delta.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('snapshot',len(base),'facility changed',report['changed_rows'],'columns', {k:v for k,v in diffcols.items() if v})
# Stage source changes fixed before computation.
p=Q/'코드/a00_config.py';t=p.read_text(encoding='utf8').replace('BASE = ROOT.parent.parent','BASE = Path(os.environ.get("ACCESS_REPOSITORY_ROOT", ROOT.parent.parent))');p.write_text(t,encoding='utf8')
p=Q/'코드/a11_provenance.py';t=p.read_text(encoding='utf8').replace("SCHEMA = 'access-run-provenance/1'","SCHEMA = 'access-run-provenance/2'").replace("access-engine-v3.1-20260929","access-engine-v3.2-facility-v1.3-20260929")
t=t.replace("C.UNITS_SOURCE_JSON,C.FACILITY_PARQUET]","C.UNITS_SOURCE_JSON]")
t=t.replace("code_base='package_code',input_base='repository',","code_base='package_code',input_base='package_inputs',")
t=t.replace("inputs=inventory(paths,C.BASE),","inputs=inventory(paths,C.DATA),upstream_inputs=inventory([C.FACILITY_PARQUET],C.BASE),")
t=t.replace("elif prov.get('schema')!=SCHEMA:failures.append('unknown provenance schema')","elif prov.get('schema') not in (SCHEMA,'access-run-provenance/1'):failures.append('unknown provenance schema')")
t=t.replace("failures += ['input '+x for x in check_inventory(prov.get('inputs',{}),repo_root or C.BASE)]","ibase=package_root/'데이터/입력' if prov.get('input_base')=='package_inputs' else (repo_root or C.BASE)\n        failures += ['input '+x for x in check_inventory(prov.get('inputs',{}),ibase)]\n        if prov.get('schema')==SCHEMA:\n            failures += ['upstream '+x for x in check_inventory(prov.get('upstream_inputs',{}),repo_root or C.BASE)]")
p.write_text(t,encoding='utf8')
p=Q/'코드/a06_engine.py';t=p.read_text(encoding='utf8').replace("ENGINE_VERSION = 'access-engine-v3.1'","ENGINE_VERSION = 'access-engine-v3.2'").replace("drift = P.check_inventory(provenance['inputs'], C.BASE)","drift = P.check_inventory(provenance['inputs'], C.DATA) + P.check_inventory(provenance['upstream_inputs'], C.BASE)")
assert 'access-engine-v3.2' in t;p.write_text(t,encoding='utf8')
p=Q/'코드/a10_verify.py';t=p.read_text(encoding='utf8').replace('facility-v1.2','facility-v1.3').replace('facility-v1\\.2','facility-v1\\.3');p.write_text(t,encoding='utf8')
p=Q/'코드/run_engine.bat';p.write_text(p.read_text(encoding='utf8').replace('access engine v3.1','access engine v3.2'),encoding='utf8')
(S/'stage_env.json').write_text(json.dumps({'ACCESS_REPOSITORY_ROOT':str(R)},ensure_ascii=False),encoding='utf8')
