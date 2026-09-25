"""공공체육시설 추가 좌표 보완(한강공원 시설지도, 엄격 규칙) + 도시재생 기본방침 별표2 분류 + 구 단위 결측 편중 검사.
보완 규칙(좌표 미해결 행만): 명부 이름에 한강공원 지구명(이촌·뚝섬·망원·강서·광나루·난지·잠실·잠원·여의도·반포·양화)이 있고
  시설지도 후보 = 이름이 같은 지구명으로 시작 & 같은 종목어(축구·야구·테니스·게이트볼) 포함 & (명부 이름에 번호가 있으면 번호 겹침)
  & 명부 이름 핵심어 = 종목명, 시설지도 이름(괄호 앞, 지구명·번호 제거) = 종목명(예: '어린이야구장' ≠ '야구장') & 후보 좌표의 자치구(경계 판정) = 명부 자치구. 후보 1건 → 그 좌표, 2건 이상이면 모두 300 m 안일 때만 중심점. 그 외 미채택.
  coord_method='borrowed_hangang_facility_map', coord_stage='4_한강시설지도_지구·종목일치'."""
import re, json, sys
from pathlib import Path
import numpy as np, pandas as pd
import math
def _gammaincc(a, x):
    """정규화 상부 불완전 감마 Q(a,x) (Numerical Recipes 방식)."""
    if x <= 0: return 1.0
    if x < a + 1:
        ap, sm, de = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1; de *= x / ap; sm += de
            if abs(de) < abs(sm) * 1e-12: break
        return 1 - sm * math.exp(-x + a * math.log(x) - math.lgamma(a))
    b = x + 1 - a; c = 1e300; dd = 1 / b; hh = dd
    for i in range(1, 500):
        an = -i * (i - a); b += 2; dd = an * dd + b; dd = 1e-300 if abs(dd) < 1e-300 else dd
        c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c; dd = 1 / dd; de = dd * c; hh *= de
        if abs(de - 1) < 1e-12: break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * hh
def chi2_contingency(ct):
    o = ct.values.astype(float); e = o.sum(1, keepdims=True) * o.sum(0, keepdims=True) / o.sum()
    m = e > 0; x = float(((o - e)[m] ** 2 / e[m]).sum()); dof = (o.shape[0] - 1) * (o.shape[1] - 1)
    return x, _gammaincc(dof / 2, x / 2), dof
HERE = Path(__file__).resolve().parents[1]; V1 = HERE.parents[1]; SRC = V1 / '02_명부/공공체육시설'
sys.path.insert(0, str(V1 / '01_인허가/_common')); from lic_common import spatial_attach, tf
GU = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']
SGG = dict(zip([f'11{i:02d}0' for i in range(1, 26)], GU))
ZONES = ['이촌', '뚝섬', '망원', '강서', '광나루', '난지', '잠실', '잠원', '여의도', '반포', '양화']
TYPES = {'축구장': '축구', '야구장': '야구', '테니스장': '테니스', '게이트볼장': '게이트볼'}
# 별표2(제2차 국가도시재생기본방침): 마을단위 '생활체육시설: 간이운동장, 수영장, 체육도장 등'(도보 10분) / 지역거점 '공공체육시설: 경기장, 체육관, 수영장'(차량 15~30분)
URC = {'육상경기장': ('지역거점', '별표2 예시 직접(경기장)'), '축구장': ('지역거점', '별표2 예시 직접(경기장; 문체부 분류상 규격 축구장)'), '야구장': ('지역거점', '별표2 예시 직접(경기장)'),
       '하키장': ('지역거점', '별표2 예시 직접(경기장)'), '싸이클경기장': ('지역거점', '별표2 예시 직접(경기장)'), '빙상장': ('지역거점', '별표2 예시 직접(경기장)'),
       '구기체육관': ('지역거점', '별표2 예시 직접(체육관)'), '투기체육관': ('지역거점', '별표2 예시 직접(체육관)'), '생활체육관': ('지역거점', '별표2 예시 직접(체육관)'),
       '수영장': ('지역거점', '별표2 예시 직접(수영장; 마을단위 예시에도 있어 이중 해당)'),
       '테니스장': ('마을단위', '연구자 판단(소규모 옥외 단일종목 = 간이운동장 성격)'), '게이트볼장': ('마을단위', '연구자 판단(간이운동장 성격)'),
       '기타체육시설(풋살장)': ('마을단위', '연구자 판단(간이운동장 성격)'), '기타체육시설(그외)': ('마을단위', '연구자 판단(배드민턴·농구·족구 등 간이운동장 성격)'),
       '기타체육시설': ('마을단위', '연구자 판단(간이운동장 성격)'), '파크골프장': ('마을단위', '연구자 판단(공원 내 간이시설)'),
       '롤러스케이트장': ('마을단위', '연구자 판단(서울은 공원 내 인라인장 위주)'),
       '골프연습장': ('지역거점', '연구자 판단(모호: 전문시설·광역 이용)'), '국궁장': ('지역거점', '연구자 판단(모호: 전문시설·광역 이용)')}
NONCORE = {'기타체육시설', '기타체육시설(풋살장)', '기타체육시설(그외)', '파크골프장'}
h = pd.read_csv(HERE / 'raw/hangang_sports_facilities_20260924.csv')
hx = spatial_attach(pd.DataFrame({'x_5179': tf(4326, 5179).transform(h.lon.values, h.lat.values)[0], 'y_5179': tf(4326, 5179).transform(h.lon.values, h.lat.values)[1]}))
h['gu_pt'] = hx.adm_dong_cd.astype(str).str[:5].map(SGG).values; h['x'] = hx.x_5179.values; h['y'] = hx.y_5179.values
nums = lambda s: set(re.findall(r'\d+', re.sub(r'(\d)\s*~\s*(\d)', lambda m: ' '.join(str(i) for i in range(int(m[1]), int(m[2]) + 1)), str(s))))
summ, gurows, cls_rows, fill_log = {}, [], [], []
for k in ['2020_01', '2025_01']:
    d = pd.read_parquet(SRC / f'facilities_공공체육시설_{k}.parquet')
    before = (d.inside_seoul.astype(str) == 'True').mean()
    for i in d.index[d.coord_method == 'unresolved']:
        nm, st, g = d.at[i, 'name'], d.at[i, 'facility_subtype'], d.at[i, 'gu']
        z = next((z for z in ZONES if z in nm), None); t = TYPES.get(st)
        if not (z and t and ('한강' in nm or '지구' in nm)): continue
        core = re.sub(r'\(임시\)|한강시민공원|한강공원|한강공워너|' + z + r'지구|' + z + r'|[\d~\s]', '', nm)
        if core != st:                       # 명부 이름의 핵심어가 종목명과 정확히 같을 때만(예: '축구교육장' 제외)
            fill_log.append(dict(snapshot=k, name=nm, subtype=st, gu=g, n_cand=None, cand='', result='rejected_name_core_not_type')); continue
        hcore = h.name.str.split('(').str[0].str.replace(r'^' + z, '', regex=True).str.replace(r'[\d,\s]', '', regex=True)
        c = h[h.name.str.startswith(z) & (hcore == st) & (h.gu_pt == g)]
        n0 = nums(re.sub(r'한강\S*|지구', '', nm)) - set()
        if n0: c = c[c.name.map(lambda s: bool(nums(s.split('(')[0]) & n0))]
        rec = dict(snapshot=k, name=nm, subtype=st, gu=g, n_cand=len(c), cand=' | '.join(c.name))
        if len(c) == 0: rec['result'] = 'no_candidate'
        else:
            spread = float(np.hypot(c.x.max() - c.x.min(), c.y.max() - c.y.min()))
            if len(c) == 1 or spread <= 300:
                lo, la = float(c.lon.mean()), float(c.lat.mean()); X, Y = tf(4326, 5179).transform(lo, la)
                d.loc[i, ['lon', 'lat', 'x_5179', 'y_5179']] = [lo, la, X, Y]; d.at[i, 'coord_method'] = 'borrowed_hangang_facility_map'
                d.at[i, 'coord_stage'] = '4_한강시설지도_지구·종목일치'; d.at[i, 'borrow_source'] = 'hangang.seoul.go.kr 시설지도: ' + ' | '.join(c.name)
                rec['result'] = 'accepted' + ('' if len(c) == 1 else f'_centroid(spread {spread:.0f}m)')
            else: rec['result'] = f'rejected_spread_{spread:.0f}m'
        fill_log.append(rec)
    d = spatial_attach(d)
    d['gu_seoul'] = d.gu.where(d.gu.isin(GU))
    d['scope_flag'] = np.where(d.gu_seoul.isna() | (d.inside_seoul == False), '서울밖소재(분석제외)', np.where(d.facility_subtype.isin(NONCORE), '기타·파크골프(정의변경 가능 종목)', '핵심종목'))
    d['urban_regen_class'] = d.facility_subtype.map(lambda s: URC.get(s, ('미분류', ''))[0]); d['urban_regen_basis'] = d.facility_subtype.map(lambda s: URC.get(s, ('', ''))[1])
    d['coord_strict'] = d.coord_method.isin(['geocode_kakao_exact', 'geocode_vworld_exact', 'borrowed_official_list_name_gu', 'borrowed_hangang_facility_map'])
    d.to_parquet(HERE / f'facilities_공공체육시설_{k}.parquet', index=False); d.to_csv(HERE / f'facilities_공공체육시설_{k}.csv', index=False, encoding='utf-8-sig')
    s = d[d.scope_flag != '서울밖소재(분석제외)']; ok = s.inside_seoul == True; oks = ok & s.coord_strict
    r = ok.groupby(s.gu_seoul).mean(); rs = oks.groupby(s.gu_seoul).mean()
    ct = pd.crosstab(s.gu_seoul, ok); chi = chi2_contingency(ct)
    ct2 = pd.crosstab(s.facility_subtype, ok); chi2 = chi2_contingency(ct2)
    for g in GU:
        sg = s[s.gu_seoul == g]
        gurows.append(dict(snapshot=k, gu=g, n=len(sg), coord_rate_all=round(ok[s.gu_seoul == g].mean() * 100, 1) if len(sg) else None,
                           coord_rate_strict=round(oks[s.gu_seoul == g].mean() * 100, 1) if len(sg) else None,
                           n_거점=int((sg.urban_regen_class == '지역거점').sum()), n_마을=int((sg.urban_regen_class == '마을단위').sum())))
    summ[k] = dict(rows=len(d), outside_seoul_excluded=int((d.scope_flag == '서울밖소재(분석제외)').sum()), analysis_rows=len(s), gu_missing=int(s.gu_seoul.isna().sum()),
                   coord_rate_before=round(before * 100, 2), coord_rate_after_all=round(ok.mean() * 100, 2), coord_rate_after_strict=round(oks.mean() * 100, 2),
                   hangang_filled=int((d.coord_method == 'borrowed_hangang_facility_map').sum()), coord_method=d.coord_method.value_counts().to_dict(),
                   min_gu=r.idxmin(), min_gu_rate=round(r.min() * 100, 1), n_gu_below85=int((r < .85).sum()), n_gu_below85_strict=int((rs < .85).sum()),
                   chi2_gu=dict(chi2=round(chi[0], 2), dof=int(chi[2]), p=float(f'{chi[1]:.4g}')), chi2_subtype=dict(chi2=round(chi2[0], 2), dof=int(chi2[2]), p=float(f'{chi2[1]:.4g}')),
                   coord_rate_by_subtype=(ok.groupby(s.facility_subtype).mean() * 100).round(1).to_dict(),
                   unresolved_blank_address=int(((s.inside_seoul != True) & (s.address.fillna('').str.strip() == '')).sum()), unresolved=int((s.inside_seoul != True).sum()),
                   counts_scope=d.scope_flag.value_counts().to_dict(),
                   urban_regen=s.groupby(['urban_regen_class', 'facility_subtype']).size().to_dict().__repr__(),
                   urban_regen_total=s.urban_regen_class.value_counts().to_dict(),
                   urban_regen_core=s[s.scope_flag == '핵심종목'].urban_regen_class.value_counts().to_dict())
pd.DataFrame(gurows).to_csv(HERE / 'coord_by_gu_공공체육시설.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(fill_log).to_csv(HERE / 'hangang_fill_log_공공체육시설.csv', index=False, encoding='utf-8-sig')
json.dump(summ, open(HERE / 'summary_공공체육시설.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1)); print(pd.DataFrame(fill_log).to_string())
