from pathlib import Path
import json,os,subprocess,sys,time,shutil
S=Path(__file__).resolve().parent;P=S/'접근성분석_패키지';R=Path('D:\\Research\\00_박사논문_연구체계');OLD=Path('D:\\Research\\00_박사논문_연구체계\\06_접근성분석\\접근성분석_패키지')
env={**os.environ,'ACCESS_REPOSITORY_ROOT':str(R),'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8','TEMP':str(S/'tmp'),'TMP':str(S/'tmp')};(S/'tmp').mkdir(exist_ok=True)
rows=[]
def execute(name,script,args=[]):
 cmd=[sys.executable,'-B','-X','utf8',str(P/'코드'/script)]+args
 if shutil.disk_usage(S).free<3_000_000_000:raise RuntimeError('disk under 3GB')
 started=time.time()
 with (S/(name+'.log')).open('w',encoding='utf8') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
 rows.append({'name':name,'command':cmd,'exit_code':p.returncode,'seconds':round(time.time()-started,2)})
 (S/'execution.json').write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding='utf8')
 print(name,'exit',p.returncode,'seconds',rows[-1]['seconds'],flush=True)
 if p.returncode:raise RuntimeError('STOP: '+name)
rows.append(next(x for x in json.loads((S/'phase1/execution.json').read_text(encoding='utf8')) if x['name']=='a02'))
execute('test_engine','tests/test_engine.py');execute('test_release','tests/test_release.py');execute('test_geometry','tests/test_geometry.py')
for f in sorted((OLD/'데이터/결과').glob('*/run_meta*.json')):
 m=json.loads(f.read_text(encoding='utf8'));tag=f.parent.name;y=m['year']
 args=['--year',str(y),'--grid',str(m['grid_m']),'--T',str(m['T_sec']),'--speed',str(m['speed_kmh']),'--catset',m['catset'],'--retail',m['retail'],'--tag',tag]
 if m.get('union'):args+=['--union']
 if m.get('net_year'):args+=['--net-year',str(m['net_year'])]
 if tag=='sens_snap':args+=['--snap']
 if m.get('boundary_year',{}).get('ld_other'):args+=['--ld-other']
 if any('grid_sfca_' in x['file'] for x in m['files']):args+=['--save-sfca-grid']
 execute(f'engine_{tag}_{y}','a06_engine.py',args)
for n in ['a06d_temporal_sensitivity.py','a06b_summary.py','a07_study3_outputs.py','a08_ku_compare.py']:
 execute(Path(n).stem,n)
print('ALL RUNS FINISHED',flush=True)
