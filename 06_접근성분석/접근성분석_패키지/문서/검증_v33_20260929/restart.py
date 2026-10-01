from pathlib import Path
import shutil,json
S=Path(__file__).resolve().parent;P=S/'phase1';P.mkdir()
for f in S.iterdir():
 if f.is_file() and f.suffix in ('.json','.log'):shutil.copy2(f,P/f.name)
shutil.copy2(S/'verification.log',S/'verification_phase1.log')
r=(S/'run_all.py').read_text(encoding='utf8')
r=r.replace("execute('a02','a02_facility_boundary.py')","rows.append(next(x for x in json.loads((S/'phase1/execution.json').read_text(encoding='utf8')) if x['name']=='a02'))")
(S/'run_all.py').write_text(r,encoding='utf8')
# Main/SFCA numbers must remain exact after the B-label-only edit.
import hashlib
rows=[]
for f in (S/'접근성분석_패키지/데이터/결과').glob('*/*'):
 if f.is_file() and f.suffix in ['.csv','.parquet'] and f.parent.name!='natstd_B':
  rows.append({'file':f.relative_to(S/'접근성분석_패키지').as_posix(),'sha256':hashlib.file_digest(open(f,'rb'),'sha256').hexdigest()})
(S/'independent_reuse_guard.json').write_text(json.dumps(rows,ensure_ascii=False,indent=1),encoding='utf8')
