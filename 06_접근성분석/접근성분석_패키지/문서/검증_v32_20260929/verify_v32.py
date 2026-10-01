"""Task verification: use with retained execution.json, baseline.json and previous package.
The old package is comparison-only. Writes only the new package and this script's directory.
"""
from pathlib import Path
import os,sys,json,time,subprocess,gc
import numpy as np
import pandas as pd
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지';OLD=S.parent/'접근성분석_패키지';R=S.parent.parent
os.environ['ACCESS_REPOSITORY_ROOT']=str(R)
sys.path.insert(0,str(Q/'코드'))
import a10_verify as V
import a11_provenance as P
t0=time.time()
D=Q/'문서/검증_v32_20260929';D.mkdir(exist_ok=True)
def save(name,value):(D/name).write_text(json.dumps(value,ensure_ascii=False,indent=1,default=str),encoding='utf8')
base=json.loads((S/'baseline.json').read_text(encoding='utf8'))
print('BASE TYPE',type(base).__name__,flush=True)
execution=json.loads((S/'execution.json').read_text(encoding='utf8'))
assert len([x for x in execution if x['name'].startswith('engine_') and x['exit_code']==0])==22
if '--resume-comparison' in sys.argv:
    # Preserve completed expensive checks after a comparison-script typo; exact log extraction.
    import re
    log=(S/'verification_phase1.log').read_text(encoding='utf8')
    hits=re.findall(r'^(PASS|WARN|FAIL) (1\. 입력 무결성|2\. 계산 정확성) (.+?) — (.*)$',log,re.M)
    assert len(hits)==47,len(hits)
    for status,group,name,detail in hits:V.rec(group,name,{'PASS':True,'FAIL':False,'WARN':None}[status],detail)
else:
    V.check_inputs();V.check_run_meta()
    for name,n in [('test_engine',17),('test_geometry',4)]:
        r=next(x for x in execution if x['name']==name)
        V.rec('2. 계산 정확성',name,r['exit_code']==0,f'{n}개 통과; 실행 로그 보존')
    with (S/'test_release_v32.log').open('w',encoding='utf8') as f:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(Q/'코드/tests/test_release.py')],stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'TEMP':str(S/'tmp'),'TMP':str(S/'tmp')})
    V.rec('2. 계산 정확성','배포 회귀시험 v3.2',p.returncode==0,'11개; schema2 이동 후 검증 및 upstream 변경 감지 포함')
    for y in [2020,2025]:
        V.independent_sfca(y,items=('공공도서관','어린이집','체육시설업','주민센터','문화','의료','체육'),bounds=('none','lz116'));gc.collect()
diff=[];main=[];unchanged_pop=[];sfca_unaffected=[]
fu0=pd.read_parquet(OLD/'데이터/입력/facility/facility_2020_2025_units.parquet')
fu1=pd.read_parquet(Q/'데이터/입력/facility/facility_2020_2025_units.parquet')
geo=['x_5179','y_5179','분석가능','grid100_cd']
changed=~(fu0[geo].eq(fu1[geo])|(fu0[geo].isna()&fu1[geo].isna())).all(axis=1)
affected={str(y):{'facility':sorted(fu1.loc[changed&(fu1.year==y),'시설'].unique().tolist()),'category':sorted(fu1.loc[changed&(fu1.year==y),'cat_A'].dropna().unique().tolist())} for y in [2020,2025]}
for new in sorted((Q/'데이터/결과').glob('*/*.csv')):
    old=OLD/new.relative_to(Q)
    if not old.exists() or not (new.name.startswith('unit_access_') or new.name.startswith('sfca_unit_')):continue
    a=pd.read_csv(old);b=pd.read_csv(new)
    keys=['year','grid_m','T_sec','speed_kmh','retail','unit_level','unit_id','b']
    keys+=['item_type','item'] if new.name.startswith('sfca') else ['catset','cat']
    keys=[k for k in keys if k in a and k in b]
    assert list(a.columns)==list(b.columns),(new,'schema drift')
    a=a.set_index(keys).sort_index();b=b.set_index(keys).sort_index();assert a.index.equals(b.index),(new,'keys drift')
    metrics=[c for c in a if pd.api.types.is_numeric_dtype(a[c])]
    neq=(~(a[metrics].eq(b[metrics])|(a[metrics].isna()&b[metrics].isna())))
    row={'file':new.relative_to(Q).as_posix(),'rows':len(a),'changed_rows':int(neq.any(axis=1).sum()),'metrics':{c:{'changed_rows':int(neq[c].sum()),'max_abs':float((a[c]-b[c]).abs().max())} for c in metrics}}
    diff.append(row)
    if 'pop_total' in neq:unchanged_pop.append(row['metrics']['pop_total']['changed_rows']==0)
    if new.parent.name=='main':
        year=int(b.index.get_level_values('year')[0]);level=b.index.get_level_values('unit_level')=='dong424'
        measure='SFCA_per10k' if new.name.startswith('sfca') else None
        for met in ([measure] if measure else ['COV','MAI','PWATT_sec']):
            mask=level&neq[met].to_numpy();sub=b.loc[mask]
            main.append({'year':year,'metric':met,'scope':'dong424, all 5 boundary conditions',
                'changed_rows':int(mask.sum()),'changed_dongs':int(sub.index.get_level_values('unit_id').nunique()),
                'categories_or_items':sorted(sub.index.get_level_values('item' if measure else 'cat').unique().tolist()),
                'max_abs':float((a.loc[level,met]-b.loc[level,met]).abs().max())})
    if new.name.startswith('sfca'):
        year=int(b.index.get_level_values('year')[0]);typ=b.index.get_level_values('item_type');item=b.index.get_level_values('item')
        unaffected=np.array([it not in affected[str(year)].get(str(tp),[]) for tp,it in zip(typ,item)])
        errors=int(neq.loc[unaffected,'SFCA_per10k'].sum())
        sfca_unaffected.append({'file':row['file'],'rows':int(unaffected.sum()),'changed':errors})
save('numerical_changes.json',{'comparisons':diff,'main':main,'affected_source_items':affected,'unaffected_sfca':sfca_unaffected})
V.rec('3. facility-v1.3 전후 대조','전체 CSV 키·스키마 보존',True,f'{len(diff)}파일; 집계키 완전 일치')
V.rec('3. facility-v1.3 전후 대조','인구 분모 불변',all(unchanged_pop),f'{len(unchanged_pop)}파일 pop_total 변경 0')
V.rec('3. facility-v1.3 전후 대조','시설/범주 입력 불변인 2SFCA 항목',all(x['changed']==0 for x in sfca_unaffected),f'{sum(x["rows"] for x in sfca_unaffected):,}행; 변경 {sum(x["changed"] for x in sfca_unaffected)}행')
unchanged=[]
for folder in ['grid','boundary','network','ttm']:
    for old in sorted((OLD/'데이터/입력'/folder).rglob('*')):
        if old.is_file():
            new=Q/old.relative_to(OLD);assert P.sha256(old)==P.sha256(new),old
            unchanged.append(old.relative_to(OLD).as_posix())
save('unchanged_inputs.json',{'count':len(unchanged),'files':unchanged})
V.rec('1. 입력 무결성','시설 비의존 입력 불변',True,f'격자/경계/망/TTM/스냅 {len(unchanged)}파일 SHA 일치')
V.check_reliability()
V.rec('5. 입력 적합성','체육 포함 역사비교 확정 해석',None,'HOLD: 현재 취소·말소 상태로 과거 운영 후보가 제외된 시설 선택 문제는 v1.3 좌표 보정으로 해결되지 않음. 계산 PASS와 분리. AG S1.6 및 출처 연결표 참조.')
V.rec('5. 입력 적합성','미실행',None,'체육 선택 규칙 정정/민감도, 서울 밖 시설, 면적 배정, LD고정×snap 추가 결합은 미실행; 22설정 계산과 별개')
verdict=V.write_report(0,0,t0)
save('verification_summary.json',{'release':P.RELEASE,'verdict':verdict,'tests':{'engine':17,'release':11,'geometry':4,'total':32},'successful_engine_runs':22,'comparisons':len(diff),'main':main,'scientific_fitness':'HOLD for definitive historical comparisons including sports','failed':sum(r['결과']=='FAIL' for k,rows in V.RES.items() if not k.startswith('_') for r in rows),'elapsed_seconds':round(time.time()-t0,2)})
print('VERIFICATION',verdict,flush=True)
if verdict!='PASS':sys.exit(1)
