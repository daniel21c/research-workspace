# -*- coding: utf-8 -*-
"""공공도서관·청소년수련시설 구(區) 조건 미달분 좌표 보완 (2026-09-24). 정확일치 지오코딩 + 두 번째 근거."""
import sys, os, shutil; sys.path.insert(0,'02_명부/_lib'); import mb, pandas as pd
C='11_신뢰도_승격/_좌표보완_v3/cache'; OUT='11_신뢰도_승격/_좌표보완_v3'
FIX={('공공도서관','2020'):[('LIB2060111075','서울특별시 성북구 종암로 167','2020 명부 건물명(동일하이빌뉴시티)=2025 명부 주소; Kakao POI 달빛마루도서관'),
                          ('LIB2060111035','서울특별시 구로구 디지털로27다길 65','Kakao POI 꿈마을도서관; 좌표가 2020 명부의 구로3동 안'),
                          ('LIB2060811019','서울특별시 송파구 신천동 14','Kakao POI 송파어린이영어도서관 도로명 오금로 1 = 명부'),
                          ('LIB20601110007','서울특별시 성북구 석관동 134-2','Kakao POI 도로명 한천로66길 203 = 2020 명부, 지번 = 2025 명부'),
                          ('LIB2060111067','서울특별시 구로구 개봉동 266','Kakao POI 도로명 개봉로16길 30-11 = 명부(30 11), 서울개봉초 동일 주소'),
                          ('LIB2060111089','서울특별시 종로구 종로58가길 19','2020 명부 도로명(번호 없음) = 2025 명부 종로58가길 19; Kakao POI')],
     ('공공도서관','2025'):[('LIB2060811019','서울특별시 송파구 신천동 14','Kakao POI 도로명 오금로 1 = 명부'),
                          ('LIB2060111067','서울특별시 구로구 개봉동 266','Kakao POI 도로명 개봉로16길 30-11 = 명부')],
     ('청소년수련시설','2020'):[('YTH00003','서울특별시 강남구 삼성동 171-1','2020 명부 봉은사로114길 43 ↔ 지번 삼성동 171-1 (114.co.kr 등록정보); 2023 이후 양천구 이전'),
                            ('YTH00041','서울특별시 성북구 한천로 660-9','2020 명부 주소(한천로95길 7) 미존재; 센터 연혁상 2002 개관 후 이전 없음(sbyouth.or.kr/company/history)')]}
for (k,y),rows in FIX.items():
    src=f'10_신뢰도_상/{k}/facilities_{k}_{y}_01.parquet'; d=pd.read_parquet(src)
    for c in ['coord_evidence']:
        if c not in d.columns: d[c]=pd.NA
    for fid,addr,ev in rows:
        lon,lat,m,det=mb.geocode(addr,C); assert lon is not None,(fid,addr)
        i=d.index[d.facility_id==fid]; assert len(i)==1,(fid,len(i))
        d.loc[i,['lon','lat']]=[lon,lat]; d.loc[i,'coord_method']='search_verified'; d.loc[i,'coord_evidence']=f'{addr} ({det}); {ev}'
        s=mb.spatial(d.loc[i,['lon','lat']].reset_index(drop=True))
        for c in ['x_5179','y_5179','adm_dong_cd','oa_cd','grid100_cd','inside_seoul']: d.loc[i,c]=s[c].values
    os.makedirs(f'{OUT}/{k}',exist_ok=True)
    for c in d.columns:
        if d[c].dtype==object: d[c]=d[c].astype('string')
    d.to_parquet(f'{OUT}/{k}/facilities_{k}_{y}_01.parquet',index=False); d.to_csv(f'{OUT}/{k}/facilities_{k}_{y}_01.csv',index=False,encoding='utf-8-sig')
    print(k,y,'coord',round(d.inside_seoul.astype(str).eq('True').mean()*100,1))
