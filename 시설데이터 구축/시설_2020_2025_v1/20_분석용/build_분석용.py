# -*- coding: utf-8 -*-
"""10_신뢰도_상(상 32종) + 일상소매(상가정보, 중·조건부) → 접근성 분석용 단일 파일.
2026-09-25 개정: pandas 버전과 무관하게 문자열 열을 string으로 고정, 중복 키 검사를 실제로 수행(허용: 버스정류장 BUS_15143 2020),
환경변수 FAC_OVERRIDE_DIR(보정본 시험용)·OUT_DIR(출력 위치) 지원. 실행: python build_분석용.py"""
import pandas as pd, glob, os
BASE=os.environ.get('FAC_V1_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OV=os.environ.get('FAC_OVERRIDE_DIR','')
OUT=os.environ.get('OUT_DIR') or os.path.join(BASE,'20_분석용')
T=os.path.join(BASE,'10_신뢰도_상')
NAME={'학교':'학교','유치원':'유치원','어린이집':'어린이집','청소년수련시설':'청소년수련시설','의원':'의원','약국':'약국','병원급':'병원급',
 '보건소':'보건소·보건지소','응급의료기관':'응급의료기관','산후조리원':'산후조리원','노인복지_이용시설':'노인 이용시설','노인복지_입소시설':'노인 입소시설',
 '장애인복지_이용시설':'장애인 이용시설','가족센터_자치구본소':'가족센터(자치구 본소)','주민센터':'주민센터','소방서_안전센터':'소방서·119안전센터',
 '공공도서관':'공공도서관','문화기반시설':'문화기반시설','공연장_등록공연장':'등록공연장','체육시설업_조건부':'체육시설업','식료품소매_즉석판매제과':'식료품소매(즉석판매·제과)',
 '대규모점포_주요4업태':'대규모점포(주요4업태)','일반음식점':'일반음식점','휴게음식점':'휴게음식점','미용업':'미용업','이용업':'이용업','세탁업':'세탁업','목욕장업':'목욕장업',
 '주유소_영업_조건부':'주유소','버스정류장':'버스정류장','지하철역':'지하철역','따릉이':'따릉이 대여소'}
REL={'체육시설업_조건부':'조건부 상','주유소_영업_조건부':'조건부 상'}
KEEP=['facility_id','facility_subtype','name','address','lon','lat','x_5179','y_5179','inside_seoul','adm_dong_cd','oa_cd','grid100_cd',
      'coord_method','grade','source_org','source_dataset','source_reference_date','coord_valid_v2']
def tier(fac,sub):
    s=str(sub)
    if fac=='유치원': return ('마을단위','유치원','도보 5~10분')
    if fac=='학교': return ('마을단위','초등학교','도보 10~15분') if s.startswith('초등학교') else ('보조','','')
    if fac=='어린이집': return ('마을단위','어린이집','도보 5분')
    if fac in ('의원','약국'): return ('마을단위','기초의료(의원·약국)','도보(기준시간 없음)')
    if fac=='체육시설업': return ('마을단위','생활체육시설','도보 10분') if s in ('체력단련장','체육도장','수영장','종합체육시설') else ('보조','','')
    if fac=='일상소매': return ('마을단위','소매점','도보 10분')
    if fac=='공공도서관': return ('지역거점','공공도서관','차량 10분')
    if fac=='보건소·보건지소': return ('지역거점','보건소','차량 20분')
    if fac=='응급의료기관': return ('보조','','') if '기관 외' in s else ('지역거점','응급실 운영 의료기관','차량 30분')
    if fac=='노인 이용시설': return ('지역거점','사회복지시설(노인복지관)','차량 20~30분') if s=='노인복지관' else ('보조','','')
    if fac=='문화기반시설': return ('지역거점','공공문화시설(문예회관·전시)','차량 20분') if s in ('문예회관','박물관','미술관') else ('보조','','')
    return ('보조','','')
L=[]
for d0 in sorted(glob.glob(os.path.join(T,'*'))):
    k=os.path.basename(d0)
    if k not in NAME: continue
    for y in ['2020','2025']:
        fs=glob.glob(os.path.join(OV,k,f'facilities_*_{y}_01.parquet')) if OV else []
        fs=fs or glob.glob(os.path.join(d0,f'facilities_*_{y}_01.parquet')); assert len(fs)==1,(k,y,fs); d=pd.read_parquet(fs[0])
        d=d[[c for c in KEEP if c in d.columns]].copy(); d['시설']=NAME[k]; d['신뢰도']=REL.get(k,'상'); d['year']=int(y); L.append(d)
for y in ['2020','2025']:
    d=pd.read_parquet(os.path.join(BASE,'03_교육교통공원상가','retail_daily',f'facilities_retail_daily_{y}_01.parquet'))
    d=d[[c for c in KEEP if c in d.columns]].copy(); d['시설']='일상소매'; d['신뢰도']='중(조건부 채택)'; d['year']=int(y); L.append(d)
a=pd.concat(L,ignore_index=True)
for c in ['lon','lat','x_5179','y_5179']: a[c]=pd.to_numeric(a[c],errors='coerce')
a['기준일']=a.year.map({2020:'2019-12-31',2025:'2024-12-31'})
t=a.apply(lambda r: tier(r['시설'],r['facility_subtype']),axis=1,result_type='expand'); a['국가기준_구분'],a['국가기준_시설'],a['국가기준_접근시간']=t[0],t[1],t[2]
ins=a.inside_seoul.astype(str).isin(['True','1','true'])
valid=a['coord_valid_v2'].astype(str).ne('False') if 'coord_valid_v2' in a else True
a['inside_seoul']=ins; a['분석가능']=ins & a.lon.notna() & a.x_5179.notna() & valid
a=a.drop(columns=['coord_valid_v2'],errors='ignore')
order=['facility_id','year','기준일','시설','facility_subtype','국가기준_구분','국가기준_시설','국가기준_접근시간','신뢰도','name','address',
       'lon','lat','x_5179','y_5179','adm_dong_cd','oa_cd','grid100_cd','inside_seoul','분석가능','coord_method','grade','source_org','source_dataset','source_reference_date']
a=a[order].rename(columns={'facility_subtype':'시설_세부'})
for c in a.columns:
    if a[c].dtype==object or str(a[c].dtype)=='str': a[c]=a[c].astype('string')
dup=a[a.duplicated(['시설','facility_id','year'],keep=False)]
assert set(map(tuple,dup[['시설','facility_id','year']].drop_duplicates().values.tolist()))<={('버스정류장','BUS_15143',2020)}, dup
a.to_parquet(os.path.join(OUT,'서울시설_2020_2025_분석용.parquet'),index=False)
s=a.groupby(['시설','year']).agg(n=('facility_id','size'),분석가능=('분석가능','mean')).unstack()
print(len(a)); print(a.duplicated(['시설','facility_id','year']).sum(),'dup')
print(a.groupby(['국가기준_구분','국가기준_시설','year']).size().unstack().to_string())
s.to_csv(os.path.join(OUT,'_요약_시설별_수_좌표.csv'),encoding='utf-8-sig')
