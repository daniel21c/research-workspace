"""통합_인벤토리.csv(각 결과 parquet에서 계산)로 최상위 README를 만든다. 수치를 손으로 적지 않는다."""
import pandas as pd
t=pd.read_csv('통합_인벤토리.csv',encoding='utf-8-sig')
t['name']=t.file.str.replace('facilities_','').str.replace(r'_20\d\d_01\.parquet','',regex=True)
p=t.pivot_table(index=['category','group','name'],columns='year',values=['rows','coord_rate','grade'],aggfunc='first')
lines=[]
for (cat,grp,name),r in p.sort_index().iterrows():
    g20,g25=r[('grade','2020_01')] if ('grade','2020_01') in r else '',r[('grade','2025_01')]
    def f(x): return '–' if pd.isna(x) else (f'{int(x):,}' if isinstance(x,(int,float)) and float(x).is_integer() else str(x))
    lines.append(f"| {cat} | {name} | {grp} | {f(r[('rows','2020_01')])} | {f(r[('rows','2025_01')])} | {f(r[('coord_rate','2020_01')])} / {f(r[('coord_rate','2025_01')])} | {'' if pd.isna(g20) else g20} / {'' if pd.isna(g25) else g25} |")
body=open('README_template.md',encoding='utf-8').read().replace('{{TABLE}}','\n'.join(lines))
open('README.md','w',encoding='utf-8').write(body); print('ok',len(lines))
