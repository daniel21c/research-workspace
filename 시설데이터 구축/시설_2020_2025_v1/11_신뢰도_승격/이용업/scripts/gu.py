"""자치구 코드·이름 유틸 (11_신뢰도_승격 공용)."""
import re
import pandas as pd
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구',
      '마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
ORG2GU = {str(3000000 + 10000 * i): g for i, g in enumerate(GU)}   # 개방자치단체코드(인허가) → 자치구
SGIS2GU = {}   # adm_dong_cd 앞 5자리 → 자치구 (SGIS 2025 경계 코드 11010~11250)
for i, g in enumerate(GU):
    SGIS2GU[f'11{(i+1)*10:03d}'] = g

def gu_from_address(s: pd.Series) -> pd.Series:
    x = s.fillna('').str.extract(r'서울(?:특별시|시)?\s*([가-힣]{1,4}구)')[0]
    return x.where(x.isin(GU))

def add_gu(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['gu_org'] = df.facility_id.str.extract(r'-(3\d{6})-')[0].map(ORG2GU)
    df['gu_addr'] = gu_from_address(df.address)
    df['gu'] = df.gu_addr.fillna(df.gu_org)            # 분석용 자치구: 주소 우선, 없으면 관할 자치단체
    df['gu_coord'] = df.adm_dong_cd.fillna('').astype(str).str[:5].map(SGIS2GU)
    return df
