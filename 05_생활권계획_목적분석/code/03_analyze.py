# -*- coding: utf-8 -*-
"""03_analyze.py — 코딩 집계(표 B), 대표 문장(표 C), 실증 가능성 대응표(표 D), 키워드 빈도(국내/해외), 코드 공출현, 그림
입력: data/sentences.csv, data/documents.csv   출력: output/
숫자는 모두 이 스크립트 출력에서만 가져온다.
"""
import csv, os, re, json, collections
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Noto Sans CJK JP'; plt.rcParams['axes.unicode_minus']=False
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); OUT=os.path.join(ROOT,'output'); os.makedirs(OUT,exist_ok=True)
CODES=['가','나','다','라','마','바','기타']
CODE_NAME={'가':'접근성·형평','나':'행정 효율·자원배분','다':'참여·협의','라':'통계·모니터링','마':'협력·정체성','바':'이동·생활 실태 반영','기타':'여섯 코드 밖'}
rows=list(csv.DictReader(open(os.path.join(ROOT,'data','sentences.csv'),encoding='utf-8-sig')))
docs=list(csv.DictReader(open(os.path.join(ROOT,'data','documents.csv'),encoding='utf-8-sig')))
for r in rows: r['codes']=[c for c in r['codes_claude'].split(';') if c]
docorder=sorted([d['doc_id'] for d in docs if int(d['n_sentences'])>0], key=lambda x:(0 if x.startswith('K') else 1, x))
NK=sum(1 for d in docorder if d.startswith('K'))
def md_table(header,body):
    return '| '+' | '.join(header)+' |\n|'+'---|'*len(header)+'\n'+'\n'.join('| '+' | '.join(str(x) for x in b)+' |' for b in body)+'\n'

# ---------- 표 B: 문서×코드 빈도(문장 수)와 비율(문서 문장 수 대비, 복수코딩이라 합계>100% 가능)
cnt={d:collections.Counter() for d in docorder}; ntot={d:0 for d in docorder}
for r in rows:
    ntot[r['doc_id']]+=1
    for c in r['codes']: cnt[r['doc_id']][c]+=1
def agg(group):
    c=collections.Counter(); n=0
    for r in rows:
        if r['domestic']==group:
            n+=1
            for k in r['codes']: c[k]+=1
    return c,n
dom,ndom=agg('국내'); frn,nfrn=agg('해외')
body=[]
for d in docorder:
    body.append([d,ntot[d]]+[f"{cnt[d][c]} ({cnt[d][c]/ntot[d]*100:.0f}%)" for c in CODES])
body.append(['국내 소계',ndom]+[f"{dom[c]} ({dom[c]/ndom*100:.0f}%)" for c in CODES])
body.append(['해외 소계',nfrn]+[f"{frn[c]} ({frn[c]/nfrn*100:.0f}%)" for c in CODES])
allc=dom+frn; nall=ndom+nfrn
body.append(['전체',nall]+[f"{allc[c]} ({allc[c]/nall*100:.0f}%)" for c in CODES])
tableB=md_table(['문서','문장 수']+[f'({c}) {CODE_NAME[c]}' for c in CODES],body)
with open(os.path.join(OUT,'table_B_doc_by_code.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['doc_id','n_sentences']+CODES+[c+'_pct' for c in CODES])
    for d in docorder: w.writerow([d,ntot[d]]+[cnt[d][c] for c in CODES]+[round(cnt[d][c]/ntot[d]*100,1) for c in CODES])
    w.writerow(['국내',ndom]+[dom[c] for c in CODES]+[round(dom[c]/ndom*100,1) for c in CODES])
    w.writerow(['해외',nfrn]+[frn[c] for c in CODES]+[round(frn[c]/nfrn*100,1) for c in CODES])
# 코드 순위(국내/해외)
rank_dom=[c for c,_ in dom.most_common()]; rank_frn=[c for c,_ in frn.most_common()]
# 단일코드 문장 수(순수 문장) / 코드 수 분포
single=collections.Counter(len(r['codes']) for r in rows)
# 문서 수준: 코드가 1회 이상 나타난 문서 수(국내/해외)
docs_with={c:{'국내':0,'해외':0} for c in CODES}
for d in docorder:
    g='국내' if d.startswith('K') else '해외'
    for c in CODES:
        if cnt[d][c]>0: docs_with[c][g]+=1
ndocs={'국내':sum(1 for d in docorder if d.startswith('K')),'해외':sum(1 for d in docorder if d.startswith('F'))}

# ---------- 표 C: 코드별 대표 문장 — 규칙: 해당 코드를 가진 문장 중 코드 수가 가장 적은(순수한) 것, 국내 1 + 해외 1~2, 동률은 sent_id 순
tableC_rows=[]
for c in CODES:
    cands=[r for r in rows if c in r['codes']]
    cands.sort(key=lambda r:(len(r['codes']),r['sent_id']))
    picks=[]
    for g in ['국내','해외','해외']:
        for r in cands:
            if r['domestic']==g and r not in picks: picks.append(r); break
    for r in picks:
        tableC_rows.append([c,r['sent_id'],r['doc_id'],r['page'],r['original'].replace('|','｜'),r['gloss_ko'].replace('|','｜') or '(원문 한국어)'])
tableC=md_table(['코드','문장ID','문서','쪽','원문','요지(번역은 요지임)'],tableC_rows)

# ---------- 표 D: 코드 × 연구1 실험 대응(판정 칸은 비움; 연구1이 채움)
# 연구1 실험 정의 출처: 01_생활권_필요성/작업기록.md 2026-09-24 (실험 4개: 1 접근성 은폐 H·Theil / 2 예산 배치 P0·P1·P2·P_actual, K_min / 3 이동 반영 IFR / 4 행정 대리지표)
tableD_rows=[
 ['(가) 접근성·형평','실험1 접근성 은폐(H, Theil 분해), 실험2 예산 배치(P0 vs P1: Coverage, VC, W10, Gini)','"권역별 균등 공급·취약지 해소"가 단위별 하한 배치에서 개인 수준 형평을 실제로 바꾸는가; 구 단위에서는 취약지가 가려지는가','검증 가능(핵심)',''],
 ['(나) 행정 효율·자원배분','실험2(P2 단위별 예산 배분, K_min), 실험4 행정 대리지표(예산 수령 단위 수, 수혜 귀속률, 협의 범위, 계획 안정성)','"예산·사업 조정 단위"로서 생활권이 격자·동·구보다 실행 가능한가; 대리지표만 관측되고 협의 비용 자체는 측정 안 됨','부분 검증(대리지표), 나머지는 문헌 논증',''],
 ['(다) 참여·협의','실험4 협의 범위(시설당 영향 행정 주체 수)만 간접 대응','"이해관계자 축소가 협의를 가능하게 한다"(9/21 45:56)의 관측 가능한 부분만. 참여의 질·대표성은 실증 범위 밖','실증 범위 밖(대리지표 1개만)',''],
 ['(라) 통계·모니터링','실험1(단위별 지표 집계와 은폐), 실험3(IFR 계산 단위)','"진단 단위·지표 관리"는 어떤 단위가 진단에 적합한가로 바꿔 검증 가능(은폐 H가 작고 안정적인 단위)','검증 가능(간접)',''],
 ['(마) 협력·정체성','실험3 이동 반영(IFR: 비슷하게 움직이는 권역), 실험4 수혜 귀속률','권역 간 협력·공동체 의식은 실증 범위 밖. "장소성·인식 범위"는 IFR로 일부 대리','대부분 실증 범위 밖',''],
 ['(바) 이동·생활 실태 반영','실험3 이동 반영(동×동 생활이동 OD 기반 IFR: 공식 생활권 vs 이동 기반 구획 vs 동·구)','"실제 통행권·보행권·일상 행동 범위"를 담는다는 약속이 공식 경계에서 성립하는가','검증 가능(핵심)',''],
]
tableD=md_table(['코드','대응하는 연구1 실험·지표','검증할 수 있는 형태의 질문','실증 가능성(05 판단)','판정(연구1 기입)'],tableD_rows)

# ---------- 키워드 빈도(보조): 한국어 원문(국내) / 한국어 요지(해외) → KoNLPy Okt 명사; 영어 원문 → 단순 토큰
from konlpy.tag import Okt
okt=Okt()
STOP_KO=set('것 수 등 및 년 위 내 중 간 때 시 개 명 이 그 저 바 함 있음 함께 통해 대한 위해 따라 경우 관련 위한 통한 따른 대해 여 또한 이후 이전 지역 서울 서울시 계획 생활권 도시 구 단위 수립 도시기본계획 생활권계획 지역생활권 지역생활권계획 권역생활권계획 권역 방안 필요 역할 제시 내용 사항 정도 이상 정 명확 기존 각종 다양 하나'.split())
STOP_EN=set('the a an and or of to in for on with by is are be as that this these those it its from at their our we can more most such also than into which who through within where both all any such'.split())
def ko_nouns(text):
    return [n for n in okt.nouns(text) if len(n)>1 and n not in STOP_KO]
kw={'국내':collections.Counter(),'해외':collections.Counter()}
kw_en=collections.Counter()
for r in rows:
    txt=r['original'] if r['lang']=='ko' else r['gloss_ko']
    if txt: kw[r['domestic']].update(ko_nouns(txt))
    if r['lang']=='en':
        kw_en.update(w for w in re.findall(r"[a-zA-Z][a-zA-Z\-']+",r['original'].lower()) if w not in STOP_EN and len(w)>2)
top_dom=kw['국내'].most_common(25); top_frn=kw['해외'].most_common(25); top_en=kw_en.most_common(20)
with open(os.path.join(OUT,'keywords_domestic_vs_foreign.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['group','rank','keyword','count'])
    for g,top in [('국내',top_dom),('해외(한국어 요지)',top_frn),('해외(영어 원문)',top_en)]:
        for i,(k,n) in enumerate(top,1): w.writerow([g,i,k,n])

# ---------- 코드 공출현(문장 내), 문서 간 코드 프로필 유사도(코사인)
co=collections.Counter()
for r in rows:
    cs=sorted(set(r['codes']))
    for i in range(len(cs)):
        for j in range(i+1,len(cs)): co[(cs[i],cs[j])]+=1
import math
def vec(d): return [cnt[d][c] for c in CODES[:6]]
def cos(a,b):
    na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/(na*nb) if na and nb else 0
sim=[[round(cos(vec(a),vec(b)),2) for b in docorder] for a in docorder]
with open(os.path.join(OUT,'doc_code_profile_cosine.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['doc_id']+docorder)
    for a,srow in zip(docorder,sim): w.writerow([a]+srow)
# 국내-해외 프로필 유사도
prof_dom=[dom[c] for c in CODES[:6]]; prof_frn=[frn[c] for c in CODES[:6]]

# ---------- 그림
# 그림1 코드 비율 막대(문서별, 문장 대비 %)
fig,ax=plt.subplots(figsize=(14,5.5))
import numpy as np
x=np.arange(len(docorder)); wdt=0.13
for i,c in enumerate(CODES[:6]):
    ax.bar(x+(i-2.5)*wdt,[cnt[d][c]/ntot[d]*100 for d in docorder],wdt,label=f'({c}) {CODE_NAME[c]}')
ax.set_xticks(x); ax.set_xticklabels([f"{d}\n(n={ntot[d]})" for d in docorder],fontsize=8)
ax.set_ylabel('해당 코드가 붙은 문장 비율(%)'); ax.set_title('문서별 목적 코드 비율 (1차 코딩, 복수 코딩 허용)'); ax.legend(fontsize=8,ncol=3)
ax.axvline(NK-0.5,color='grey',ls='--',lw=0.8); ax.text(NK/2-0.5,ax.get_ylim()[1]*0.95,'국내',ha='center'); ax.text(NK+(len(docorder)-NK)/2-0.5,ax.get_ylim()[1]*0.95,'해외',ha='center')
fig.tight_layout(); fig.savefig(os.path.join(OUT,'fig1_code_share_by_doc.png'),dpi=160); plt.close(fig)
# 그림2 국내 vs 해외 코드 비율
fig,ax=plt.subplots(figsize=(7,4))
x=np.arange(6)
ax.bar(x-0.2,[dom[c]/ndom*100 for c in CODES[:6]],0.4,label=f'국내 (문장 {ndom})')
ax.bar(x+0.2,[frn[c]/nfrn*100 for c in CODES[:6]],0.4,label=f'해외 (문장 {nfrn})')
ax.set_xticks(x); ax.set_xticklabels([f'({c})\n{CODE_NAME[c]}' for c in CODES[:6]],fontsize=8); ax.set_ylabel('문장 비율(%)'); ax.legend(); ax.set_title('국내/해외 목적 코드 비율')
fig.tight_layout(); fig.savefig(os.path.join(OUT,'fig2_code_share_domestic_foreign.png'),dpi=160); plt.close(fig)
# 그림3 키워드 비교
fig,axes=plt.subplots(1,2,figsize=(11,5))
for ax,(g,top) in zip(axes,[('국내(원문 명사)',top_dom[:15]),('해외(한국어 요지 명사)',top_frn[:15])]):
    ax.barh([k for k,_ in top][::-1],[n for _,n in top][::-1]); ax.set_title(g)
fig.suptitle('목적 문장 상위 키워드 (KoNLPy Okt 명사, 불용어 제거)'); fig.tight_layout(); fig.savefig(os.path.join(OUT,'fig3_keywords.png'),dpi=160); plt.close(fig)


# ---------- 국내 하위집단: 계획 원문(도시기본계획) / 연구·백서 / 지침
SUB={'국내_도시기본계획원문':['K02','K07','K08','K09','K10','K11'],'국내_백서·연구보고서':['K01','K03','K04','K05'],'국내_수립지침':['K06'],'해외_15분·20분류':['F01','F08','F09','F13','F14','F12'],'해외_통계·계획권역':['F04','F10','F02','F03'],'해외_협의제도':['F05','F06']}
sub_out={}
for name,ds in SUB.items():
    c=collections.Counter(); n=0
    for r in rows:
        if r['doc_id'] in ds:
            n+=1
            for k in r['codes']: c[k]+=1
    sub_out[name]={'n':n,**{k:f"{c[k]} ({c[k]/n*100:.0f}%)" for k in CODES}} if n else {'n':0}
tableB_sub=md_table(['하위집단','문장 수']+CODES,[[k,v['n']]+[v.get(c,'') for c in CODES] for k,v in sub_out.items()])
open(os.path.join(OUT,'table_B_subgroups.md'),'w',encoding='utf-8').write(tableB_sub)
summary_sub=sub_out

# ---------- 결과 묶음 저장
summary=dict(n_sentences=nall,n_docs=len(docorder),n_domestic_sent=ndom,n_foreign_sent=nfrn,
  n_docs_group=ndocs,rank_domestic=rank_dom,rank_foreign=rank_frn,
  counts_domestic=dict(dom),counts_foreign=dict(frn),codes_per_sentence=dict(single),
  docs_with_code=docs_with,cooccurrence={f'{a}-{b}':n for (a,b),n in co.most_common()},
  cos_domestic_foreign=round(cos(prof_dom,prof_frn),3),
  subgroups=summary_sub,
  top_keywords_domestic=top_dom[:15],top_keywords_foreign=top_frn[:15],top_keywords_english=top_en[:15])
json.dump(summary,open(os.path.join(OUT,'summary.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
open(os.path.join(OUT,'table_B.md'),'w',encoding='utf-8').write(tableB)
open(os.path.join(OUT,'table_C.md'),'w',encoding='utf-8').write(tableC)
open(os.path.join(OUT,'table_D.md'),'w',encoding='utf-8').write(tableD)
print(json.dumps(summary,ensure_ascii=False,indent=1))
