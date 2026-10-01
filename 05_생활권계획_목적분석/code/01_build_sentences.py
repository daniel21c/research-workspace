# -*- coding: utf-8 -*-
"""01_build_sentences.py
code/sentences_part*.txt (수동 추출·1차 코딩 원장) → data/sentences.csv, data/documents.csv
실행: python3 code/01_build_sentences.py  (자기 폴더에서)
"""
import csv, glob, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CODES = ['가','나','다','라','마','바','기타']

# 표 A 메타데이터: 문서ID, 도시·국가, 연도, 문서 유형, 권역 이름, 규모, 확보 상태, 출처/경로, 쪽수 기준
DOCS = [
 ('K01','서울(한국)',2019,'계획 백서(시)','권역생활권 5 / 지역생활권 116','지역생활권 행정동 3~5개·인구 약 10만','확보(로컬 PDF)','998_학술대회/2025_CUPUM/.../2030 서울 생활권계획 백서.pdf','인쇄 쪽(PDF쪽-9)'),
 ('K02','서울(한국)',2023,'도시기본계획(법정)','보행일상권(지역생활권 116 기반) / 권역생활권 5','도보 30분, 지역생활권 인구 10만 내외(3~5동)','확보(로컬 PDF)','00_선행연구/pdf/2023_서울시_2040서울도시기본계획.pdf','인쇄 쪽(PDF쪽-8)'),
 ('K03','전국(한국)',2021,'국책연구원 보고서(제도화 방안)','중생활권·소생활권','소생활권 복수 읍면동, 중생활권 인구 10만(실무편람)','확보(로컬 PDF)','998_학술대회/2025_CUPUM/.../도시계획 실행력 강화를 위한 생활권계획 도입방안 연구.pdf','인쇄 쪽(PDF쪽-8)'),
 ('K04','서울(한국)',2022,'시 연구원 보고서(운영실태 진단)','지역생활권 116','행정동 3~5개','확보(로컬 PDF)','998_학술대회/2025_CUPUM/.../[보고서]_22_서울시 지역생활권계획 운영실태 진단과 개선방향.pdf','인쇄 쪽(PDF쪽-11)'),
 ('K05','서울(한국)',2024,'시 연구원 보고서(변천사; 1981 관악구 계획·국토부 지침·2023 혁신방안 인용 포함)','대·중·소생활권(1981) / 지역생활권(2018)','1981 관악구: 소 2~3만·중 8~10만·대 50만','확보(로컬 PDF)','00_선행연구/pdf/2024_서울연구원_생활권계획_변천과정.pdf','인쇄 쪽(PDF쪽-15)'),
 ('F01','포틀랜드(미국)',2012,'도시 종합전략계획(Portland Plan)','Complete(20-minute) neighborhoods','도보·자전거 20분','부분 확보(공개 웹페이지 발췌; 로컬 PDF는 참여보고서로 판명)','https://www.portlandonline.com/portlandplan/index.cfm?c=58776&a=405753','원문 쪽'),
 ('F02','전국(일본)',2023,'국토계획(第三次国土形成計画 全국計画 본문 + 참고자료)','地域生活圏','생활권 인구 10만 정도 이상(目安)','확보(본문: 브라우저로 mlit PDF 열람; 참고자료: 로컬 PDF)','https://www.mlit.go.jp/kokudoseisaku/content/001621775.pdf ; 00_선행연구/pdf/2023_国土交通省_国土形成計画_参考資料.pdf','본문 = 인쇄 쪽("본문 n"), 참고자료 = PDF 쪽'),
 ('F03','전국(일본)',2025,'계획 작성 지침(국토교통성 手引き 基本編)','居住誘導区域·都市機能誘導区域','미명시','확보(로컬 PDF)','00_선행연구/pdf/2025_国土交通省_立地適正化計画_手引き.pdf','인쇄 쪽(PDF쪽-5)'),
 ('F04','전국(프랑스)',2012,'통계 구획 해설(INSEE Première 1425)','bassin de vie','1,666개; 시설 29·31·35종 3단계','확보(로컬 PDF)','00_선행연구/pdf/2012_Brutel_bassins_de_vie.pdf','PDF 쪽'),
 ('F05','잉글랜드(영국)',2012,'제도 영향평가(DCLG Impact Assessment)','neighbourhood area / neighbourhood plan','미명시','확보(로컬 PDF)','00_선행연구/pdf/2012_DCLG_neighbourhood_plans_impact_assessment.pdf','인쇄 쪽(PDF쪽-3)'),
 ('F06','전국(일본)',2009,'제도 설명자료(총무성 資料3)','地域自治区·地域協議会','미명시(17단체 123자치구, 2007)','확보(로컬 PDF)','00_선행연구/pdf/2009_総務省_地域自治区制度_資料3.pdf','인쇄 쪽(PDF쪽-1)'),
 ('F08','파리(프랑스)',2022,'시 정책 웹페이지(paris.fr)','ville du quart d\'heure','도보 15분','확보(공개 웹페이지)','https://www.paris.fr/dossiers/paris-ville-du-quart-d-heure-ou-le-pari-de-la-proximite-37','URL'),
 ('F09','멜버른(호주)',2024,'주정부 계획 웹페이지(Plan Melbourne)','20-minute neighbourhood','왕복 도보 20분','확보(공개 웹페이지)','https://www.planning.vic.gov.au/guides-and-resources/strategies-and-initiatives/20-minute-neighbourhoods','URL'),
 ('F10','베를린(독일)',2021,'주정부 제도 웹페이지','LOR(예측권역 58/구역권역 143/계획권역 542)','3계층','확보(공개 웹페이지)','https://www.berlin.de/sen/sbw/stadtdaten/stadtwissen/sozialraumorientierte-planungsgrundlagen/lebensweltlich-orientierte-raeume/','URL'),
 ('F11','국제(UN-Habitat)',2014,'국제기구 계획 원칙(Discussion Note 3)','sustainable neighbourhood','미명시','부분 확보(웹 요약 2문장; PDF 본문 미확보)','https://unhabitat.org/a-new-strategy-of-sustainable-neighbourhood-planning-five-principles','URL'),
 ('K06','전국(한국)',2023,'국토교통부 훈령(도시·군기본계획수립지침, 제1694호 2023.12.28)','생활권(일상/권역), 생활권계획','일상생활권 읍면동 1개 이상 / 권역생활권 구·군 1개 이상','확보(브라우저로 molit PDF 열람)','https://www.molit.go.kr/LCMS/DWN.jsp?fold=law&fileName=도시·군기본계획수립지침(국토교통부훈령)_전문.pdf','PDF 쪽(87쪽 본)'),
 ('K07','부산(한국)',2023,'도시기본계획(2040 부산도시기본계획)','대생활권 3 / 중생활권 6 / 소생활권(생활보행권)','중생활권 인구 40~50만, 대생활권 80~100만; 생활보행권 도보 15분','확보(브라우저로 eum.go.kr PDF 열람)','https://www.eum.go.kr 자료실 seq=245 (2040부산광역시.pdf)','인쇄 쪽'),
 ('K08','대전(한국)',2025,'도시기본계획(2040년 대전도시기본계획)','대생활권 3 / 1530 모빌리티 생활권(보행 15분·대중교통 30분)','소생활권 2~3만, 중생활권 10만 내외, 대생활권 20만 이상(기준 검토)','확보(브라우저로 daejeon.go.kr PDF 열람)','https://www.daejeon.go.kr/data/urb/urb010401/2040_basic_plan.pdf','인쇄 쪽'),
 ('K09','울산(한국)',2022,'도시기본계획(2035년 울산도시기본계획)','대생활권 3 / 중생활권 10','소 2~3만, 중 10만 내외, 대 20만 이상','확보(브라우저로 eum.go.kr PDF 열람)','https://www.eum.go.kr 자료실 seq=219 (2035울산광역시.pdf)','인쇄 쪽'),
 ('K10','광주(한국)',2017,'도시기본계획(2030년 광주도시기본계획)','대생활권 7 / 중·소생활권','대생활권 인구 20~30만 내외','확보(브라우저로 eum.go.kr PDF 열람)','https://www.eum.go.kr 자료실 seq=179 (2030광주.pdf)','인쇄 쪽'),
 ('K11','세종(한국)',2025,'도시기본계획(2040년 세종도시기본계획)','대생활권 1 / 중생활권 4','중생활권 8.8만~43만','확보(브라우저로 eum.go.kr PDF 열람)','https://www.eum.go.kr 자료실 seq=317 (2024세종.pdf)','인쇄 쪽'),
 ('F12','상하이(중국)',2023,'시 행동 지침 공고(行动工作导引)','15分钟社区生活圈','도보 15분','부분 확보(웹 공고문 3문장; 2016 규획도칙·2023 지침 본문 미확보)','https://ghzyj.sh.gov.cn/nw2431/20230606/2a4788a79cd447a0af84a14a7642ebf0.html','URL'),
 ('F13','바르셀로나(스페인)',2025,'시 프로그램 웹페이지(Superilles)','superilla(슈퍼블록)·green hubs','미명시','확보(공개 웹페이지, 브라우저)','https://ajuntament.barcelona.cat/superilles/en/','URL'),
 ('F14','상하이(중국)',2024,'시 공정건설규범(上海15分钟社区生活圈规划技术标准, 征求意见稿)','15分钟社区生活圈 基本单元','주성구 도보 15분·반경 800~1000m·인구 3~5만','확보(브라우저로 zjw.sh.gov.cn PDF 열람)','https://zjw.sh.gov.cn/cmsres/46/46a920ce8f904888a1535f7d40a7be5f/b7f3c903e57f0d13d0fc99a4400c033f.pdf','인쇄 쪽'),
]
DOC_COLS = ['doc_id','city_country','year','doc_type','unit_name','scale','status','source','page_basis']

def parse():
    rows=[]
    for f in sorted(glob.glob(os.path.join(HERE,'sentences_part*.txt'))):
        for ln in open(f,encoding='utf-8'):
            ln=ln.rstrip('\n')
            if not ln.strip() or ln.startswith('#'): continue
            parts=[p.strip() for p in ln.split('|||')]
            assert len(parts)==5, ln[:80]
            doc,page,codes,orig,gloss=parts
            codes=[c for c in codes.split(';') if c]
            for c in codes: assert c in CODES, (c, ln[:60])
            rows.append(dict(doc_id=doc,page=page,original=orig,gloss_ko=gloss,codes_claude=';'.join(codes)))
    return rows

def lang_of(doc):
    return {'K':'ko'}.get(doc[0],{'F01':'en','F02':'ja','F03':'ja','F04':'fr','F05':'en','F06':'ja','F08':'fr','F09':'en','F10':'de','F11':'en','F12':'zh','F13':'en','F14':'zh'}.get(doc,'en'))

if __name__=='__main__':
    rows=parse()
    os.makedirs(os.path.join(ROOT,'data'),exist_ok=True)
    with open(os.path.join(ROOT,'data','sentences.csv'),'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(['sent_id','doc_id','domestic','lang','page','original','gloss_ko','codes_claude'])
        for i,r in enumerate(rows,1):
            w.writerow([f'S{i:03d}',r['doc_id'],'국내' if r['doc_id'].startswith('K') else '해외',lang_of(r['doc_id']),r['page'],r['original'],r['gloss_ko'],r['codes_claude']])
    n_by={}
    for r in rows: n_by[r['doc_id']]=n_by.get(r['doc_id'],0)+1
    with open(os.path.join(ROOT,'data','documents.csv'),'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f); w.writerow(DOC_COLS+['n_sentences'])
        for d in sorted(DOCS,key=lambda d:(0 if d[0].startswith('K') else 1,d[0])): w.writerow(list(d)+[n_by.get(d[0],0)])
    print('sentences',len(rows),'docs',len(DOCS)); print(n_by)
