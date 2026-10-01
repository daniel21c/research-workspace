# -*- coding: utf-8 -*-
"""02_coding_sample.py — 사용자 2차 독립 코딩용 표본(문장 25%, 문서별 층화 무작위, seed 고정)
출력: data/coding_sample_for_user.csv (1차 코드는 비워 둠; 원문·요지만 제공)
"""
import csv, os, random, math
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
SEED=20260924; FRAC=0.25
rows=list(csv.DictReader(open(os.path.join(ROOT,'data','sentences.csv'),encoding='utf-8-sig')))
random.seed(SEED)
by={}
for r in rows: by.setdefault(r['doc_id'],[]).append(r)
sample=[]
for d in sorted(by):
    k=max(1,math.ceil(len(by[d])*FRAC))
    sample+=random.sample(by[d],k)
sample.sort(key=lambda r:r['sent_id'])
out=os.path.join(ROOT,'data','coding_sample_for_user.csv')
with open(out,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['sent_id','doc_id','page','original','gloss_ko','code_user(가;나;다;라;마;바;기타 중 복수 가능)','memo'])
    for r in sample: w.writerow([r['sent_id'],r['doc_id'],r['page'],r['original'],r['gloss_ko'],'',''])
print(f'seed={SEED} frac={FRAC} sample={len(sample)}/{len(rows)}')
