from pathlib import Path
import json,shutil,hashlib,subprocess
import pandas as pd
S=Path(__file__).resolve().parent
R=Path('D:/Research/00_박사논문_연구체계');O=R/'06_접근성분석/접근성분석_패키지';Q=S/'접근성분석_패키지'
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=1),encoding='utf8')
files=[p for p in O.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
write(S/'baseline.json',{'root':str(O),'files':[{'file':p.relative_to(O).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]})
(S/'git_status.txt').write_text(subprocess.check_output(['git','-C',str(R),'status','--short'],text=True,encoding='utf8'),encoding='utf8')
shutil.copytree(O,Q,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
D=Q/'문서/검증_v33_20260929';D.mkdir()
H=D/'이전_v32';H.mkdir()
for f in ['데이터/release_provenance.json','데이터/검증결과.json','문서/검증보고서.md','README.md','문서/지표정의_확정.md','문서/공동연구자_시작_20260929.md','문서/출처_전처리_연결표_20260929.md']:
 p=O/f
 if p.exists():t=H/f;t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,t)
for p in (O/'데이터/결과').glob('*/run_meta*.json'):
 t=H/'run_metadata'/p.parent.name/p.name;t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,t)
for p in (O/'코드').rglob('*.py'):
 t=H/'code'/p.relative_to(O/'코드');t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,t)
old=Path('D:/Research/_archive/facility-v1.3_superseded_20260929/데이터/서울시설_2020_2025_분석용.parquet')
new=R/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet'
a=pd.read_parquet(old);b=pd.read_parquet(new);expected=a.loc[a['시설'].ne('체육시설업')].reset_index(drop=True)
pd.testing.assert_frame_equal(b,expected,check_exact=True)
assert sha(new)=='c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb'
write(D/'facility_comparison.json',{'old_sha256':sha(old),'new_sha256':sha(new),'old_rows':len(a),'new_rows':len(b),'new_columns':len(b.columns),'new_types':b['시설'].nunique(),'analysis_ready':int(b['분석가능'].sum()),'removed_by_year':a.loc[a['시설'].eq('체육시설업')].groupby('year').size().to_dict(),'remaining_exact':True,'coordinate_changes':0,'other_type_changes':0})
def edit(name,replacements):
 p=Q/'코드'/name;s=p.read_text(encoding='utf8')
 for a,b in replacements:
  assert a in s,(name,a);s=s.replace(a,b)
 p.write_text(s,encoding='utf8')
edit('a00_config.py',[(" '체육': ['체육시설업'],\n",''),("'체육·문화': ['체육','문화']","'문화': ['문화']")])
p=Q/'코드/a00_config.py';s=p.read_text(encoding='utf8');s='\n'.join(l for l in s.split('\n') if not ("'체육','체육시설업'" in l));s += "\n# facility-v1.4: both years exclude the full sports-business type; no public-sports replacement.\nFACILITY_SELECTION_JSON = FACPKG / '구축코드' / '시설_선택규칙.json'\nANALYSIS_SCOPE = {'facility_release': 'facility-v1.4', 'excluded_types': ['체육시설업'], 'excluded_years': [2020, 2025], 'excluded_rows_by_year': {'2020': 10293, '2025': 11007}, 'A_categories': list(CAT_A), 'A_K': len(CAT_A), 'A_types': sum(map(len,CAT_A.values())), 'B_functions': list(dict.fromkeys(x[0] for x in CAT_B)), 'public_sports_replacement': False, 'retail_historic_original': 'requested_not_received'}\n";p.write_text(s,encoding='utf8')
edit('a11_provenance.py',[("access-engine-v3.2-facility-v1.3-20260929","access-engine-v3.3-facility-v1.4-20260929"),("inventory([C.FACILITY_PARQUET],C.BASE)","inventory([C.FACILITY_PARQUET,C.FACILITY_SELECTION_JSON],C.BASE),analysis_scope=C.ANALYSIS_SCOPE")])
edit('a06_engine.py',[("CAT_B_ORDER = ['교육', '돌봄', '의료', '체육', '편의']","CAT_B_ORDER = list(dict.fromkeys(x[0] for x in C.CAT_B))")])
p=Q/'코드/a02_facility_boundary.py';s=p.read_text(encoding='utf8');i=s.index('    sp_ = fac.loc[');j=s.index('    # 격자 g',i);s=s[:i]+"    P('\\n### 5.7 체육시설업 제외\\n- facility-v1.4에서 두 연도 전체 제외. 공공체육 대체 없음. 선택규칙 JSON 및 원천 증거 보존.')\n\n"+s[j:];s=s.replace('33종','32종').replace('A 8개','A 7개').replace('B 5개','B 4개').replace('A 28종','A 27종').replace('1..8','1..7');s=s.replace('source_sha256=sha256(C.FACILITY_PARQUET), units_sha256=sha256(OUT_PQ)','source_sha256=sha256(C.FACILITY_PARQUET), units_sha256=sha256(OUT_PQ), selection_rule_sha256=sha256(C.FACILITY_SELECTION_JSON), analysis_scope=C.ANALYSIS_SCOPE');p.write_text(s,encoding='utf8')
for name in ['a06_engine.py','a06b_summary.py','a06c_delta.py','a07_study3_outputs.py','a08_ku_compare.py']:
 p=Q/'코드'/name;s=p.read_text(encoding='utf8');s=s.replace('A8','A7').replace('A 8개','A 7개').replace('A 8','A 7').replace('카테고리 8 + 시설종 28','카테고리 7 + 시설종 27').replace('우리 8개','우리 7개').replace('33종','32종');s=s.replace("plt.subplots(2, 8, figsize=(18, 5.6))","plt.subplots(2, len(cats), figsize=(16, 5.6))");p.write_text(s,encoding='utf8')
edit('a10_verify.py',[('facility-v1.3','facility-v1.4'),('facility-v1\\.3','facility-v1\\.4')])
p=Q/'코드/run_engine.bat'
if p.exists():p.write_text(p.read_text(encoding='utf8').replace('v3.2','v3.3'),encoding='utf8')
run=Path('C:/Users/cyion/.codex/tmp/access-v32-release-20260929-01a0ea59/run_all.py').read_text(encoding='utf8')
run=run.replace("R=S.parent.parent;OLD=S.parent/'접근성분석_패키지'",f"R=Path({str(R)!r});OLD=Path({str(O)!r})")
(S/'run_all.py').write_text(run,encoding='utf8')
print('Prepared',S,'source exact: removed 21300 only')
