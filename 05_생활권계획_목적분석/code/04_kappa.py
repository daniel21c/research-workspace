# -*- coding: utf-8 -*-
"""04_kappa.py — 1차(05 대화) vs 2차(독립 코더) 코딩 일치도. 코드별 이진 Cohen's κ, 문장 단위 Jaccard, 불일치 목록.
사용: python3 code/04_kappa.py data/coding_second_agent.csv  (2차 코딩 CSV: sent_id, code_user, memo)
"""
import csv, os, sys, collections
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
CODES=['가','나','다','라','마','바','기타']
second=sys.argv[1] if len(sys.argv)>1 else os.path.join(ROOT,'data','coding_second_agent.csv')
first={r['sent_id']:r for r in csv.DictReader(open(os.path.join(ROOT,'data','sentences.csv'),encoding='utf-8-sig'))}
sec={r['sent_id']:r for r in csv.DictReader(open(second,encoding='utf-8-sig'))}
ids=sorted(set(sec)&set(first))
def S(x): return set(c for c in x.split(';') if c)
rows=[]
for c in CODES:
    a=b=cc=d=0
    for i in ids:
        x=c in S(first[i]['codes_claude']); y=c in S(sec[i]['code_user'])
        if x and y: a+=1
        elif x and not y: b+=1
        elif (not x) and y: cc+=1
        else: d+=1
    n=a+b+cc+d; po=(a+d)/n; pe=((a+b)*(a+cc)+(cc+d)*(b+d))/(n*n)
    k=(po-pe)/(1-pe) if pe<1 else float('nan')
    rows.append([c,a,b,cc,d,round(po,3),round(k,3)])
jac=[len(S(first[i]['codes_claude'])&S(sec[i]['code_user']))/len(S(first[i]['codes_claude'])|S(sec[i]['code_user'])) for i in ids]
exact=sum(1 for i in ids if S(first[i]['codes_claude'])==S(sec[i]['code_user']))
os.makedirs(os.path.join(ROOT,'output'),exist_ok=True)
with open(os.path.join(ROOT,'output','kappa_by_code.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['code','both','first_only','second_only','neither','percent_agreement','cohen_kappa']); w.writerows(rows)
    w.writerow([]); w.writerow(['n_sentences',len(ids)]); w.writerow(['exact_match',exact,round(exact/len(ids),3)]); w.writerow(['mean_jaccard',round(sum(jac)/len(jac),3)])
with open(os.path.join(ROOT,'output','kappa_disagreements.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['sent_id','doc_id','codes_first','codes_second','memo_second','original'])
    for i in ids:
        if S(first[i]['codes_claude'])!=S(sec[i]['code_user']): w.writerow([i,first[i]['doc_id'],first[i]['codes_claude'],sec[i]['code_user'],sec[i].get('memo',''),first[i]['original'][:120]])
md='| 코드 | 둘 다 | 1차만 | 2차만 | 둘 다 아님 | 일치율 | Cohen κ |\n|---|---|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(str(x) for x in r)+' |' for r in rows)
md+=f'\n\n표본 {len(ids)}문장. 코드 집합 완전 일치 {exact}문장({exact/len(ids)*100:.0f}%), 평균 Jaccard {sum(jac)/len(jac):.3f}.\n'
open(os.path.join(ROOT,'output','table_kappa.md'),'w',encoding='utf-8').write(md); print(md)
