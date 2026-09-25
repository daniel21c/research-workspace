# -*- coding: utf-8 -*-
"""03_교육교통공원상가/README.md 생성 — 모든 수치는 각 유형 qa_*.json에서 읽는다(손으로 적지 않음)."""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
T = [('school', '초·중·고·특수·각종학교'), ('kindergarten', '유치원'), ('childcare', '어린이집'), ('bus_stop', '버스정류소'),
     ('subway_station', '지하철역(고유 역)'), ('bike_station', '따릉이 대여소'), ('fire_station', '소방서·119안전센터·구조대'),
     ('community_center', '주민센터'), ('park', '공원(OSM)'), ('retail_daily', '일상소매(상가업소)'), ('clinic_sbiz', '[비교용] 의원·병원(상가업소)')]
Q = {t: json.load(open(H / t / f'qa_{t}.json', encoding='utf-8')) for t, _ in T}
f = lambda x: f'{x:,}' if isinstance(x, int) else ('' if x is None else str(x))
pct = lambda x: '' if x is None else f'{100 * x:.2f}%'
def g(q, s, k, d=None):
    return q.get(s, {}).get(k, d)
def grade(q, s):
    return '/'.join(sorted(g(q, s, 'grade', {}).keys()))

cmpstr = {}
q = Q['school']; cmpstr['school'] = f"교육통계 초중고특수각종 수(폐교 제외, 휴교 포함) {f(g(q,'2020_01','official_count_sen_excl_closed'))} / {f(g(q,'2025_01','official_count_sen_excl_closed'))}, 휴교 제외 {f(g(q,'2020_01','excluded_suspended_휴교'))}/{f(g(q,'2025_01','excluded_suspended_휴교'))}; 학구도 좌표 매칭 {f(g(q,'2020_01','matched_to_zone_pos'))}/{f(g(q,'2020_01','pos_rows_seoul'))}, {f(g(q,'2025_01','matched_to_zone_pos'))}/{f(g(q,'2025_01','pos_rows_seoul'))}"
q = Q['kindergarten']; cmpstr['kindergarten'] = f"서울교육통계 유치원(폐원 제외) {f(g(q,'2020_01','official_sen_kindergartens_excl_closed'))} / {f(g(q,'2025_01','official_sen_kindergartens_excl_closed'))} (차이 {f(g(q,'2020_01','diff_vs_sen'))} / {f(g(q,'2025_01','diff_vs_sen'))})"
q = Q['childcare']; cmpstr['childcare'] = f"보육통계(OA-15457) 연말 {f(g(q,'2020_01','official_total'))} / {f(g(q,'2025_01','official_total'))} → 역산 {g(q,'2020_01','diff_total_pct')}% / {g(q,'2025_01','diff_total_pct')}%"
q = Q['bus_stop']; cmpstr['bus_stop'] = f"2020 목록 {f(g(q,'2020_01','list_rows'))}행 중 좌표 {g(q,'2020_01','coord_from')}; 2025 가상정류장 {f(g(q,'2025_01','virtual_stops'))}; 공통 ARS {f(q['panel']['common_ids'])}"
q = Q['subway_station']; cmpstr['subway_station'] = f"노선-역 {f(g(q,'2020_01','line_station_rows'))} / {f(g(q,'2025_01','line_station_rows'))}, 환승역 {f(g(q,'2020_01','transfer_stations'))} / {f(g(q,'2025_01','transfer_stations'))}; 개통목록 매칭 {q['open_list_matched']}/{q['open_list_total']}; KRIC 현재판 서울주소 노선-역 {f(g(q,'2025_01','kric_current_rows_seoul_address'))}"
q = Q['bike_station']; cmpstr['bike_station'] = f"21.01판 {f(g(q,'2020_01','source_rows'))}행 중 설치>2019-12-31 제외 {f(g(q,'2020_01','installed_after_ref_excluded'))}; 공식 연말 대여소 수 대조 보류"
q = Q['fire_station']; cmpstr['fire_station'] = f"2025판 민감도 {f(q['sensitivity_2025_release_rows'])}행; 두 시점 공통 {f(q['panel']['common_ids'])}; 공식 통계 대조 보류"
q = Q['community_center']; cmpstr['community_center'] = f"SGIS 행정동 수 {f(q['official_dong_count']['2020_01'])} / {f(q['official_dong_count']['2025_01'])}; 점이 같은 이름 동에 속함 {f(g(q,'2020_01','point_in_same_named_dong_2025'))} / {f(g(q,'2025_01','point_in_same_named_dong_2025'))}"
q = Q['park']; c = q['compare_2025_osm_vs_official']; cmpstr['park'] = f"leisure=park {f(g(q,'2020_01','leisure_park_count'))} / {f(c['osm_leisure_park_count'])}개; 2025 공식 공원 {f(c['official_park_count'])}개·{c['official_union_km2']}km² vs OSM park {c['osm_leisure_park_union_km2']}km², 공식 면적 중 OSM(전체 태그) 피복 {pct(c['official_area_covered_share_osm_all'])}"
q = Q['retail_daily']; c = q['official_compare_nts100']; cmpstr['retail_daily'] = '; '.join(f"{k.split()[1]} 상가 {f(v['sbiz_201912'])}/{f(v['sbiz_202412'])} vs 국세청 {f(v['nts_2020_01'])}/{f(v['nts_2024_12'])}" for k, v in c.items() if k[:6] in ('G20404', 'G20405'))
q = Q['clinic_sbiz']; c = q['official_compare_nts100']; k0 = list(c)[0]; cmpstr['clinic_sbiz'] = f"의원 상가 {f(c[k0]['sbiz_201912'])}/{f(c[k0]['sbiz_202412'])} vs 국세청 의원계열 {f(c[k0]['nts_2020_01'])}/{f(c[k0]['nts_2024_12'])}"

L = ['# 03_교육교통공원상가 — 서울 시설 2020_01 · 2025_01', '',
     '사양: `../00_SPEC.md`. 이 문서의 수치는 모두 `make_readme.py`가 각 유형 `qa_<유형>.json`에서 읽어 만든 것이다.', '',
     '## 유형별 요약', '',
     '| 유형 | 폴더 | 2020_01 행 | 좌표율 | 등급 | 2025_01 행 | 좌표율 | 등급 | 서울 밖(20/25) | 대조 |', '|---|---|---:|---:|---|---:|---:|---|---|---|']
for t, nm in T:
    q = Q[t]
    L.append(f"| {nm} | `{t}/` | {f(g(q,'2020_01','rows'))} | {pct(g(q,'2020_01','coord_rate'))} | {grade(q,'2020_01')} | {f(g(q,'2025_01','rows'))} | {pct(g(q,'2025_01','coord_rate'))} | {grade(q,'2025_01')} | {f(g(q,'2020_01','outside_seoul'))}/{f(g(q,'2025_01','outside_seoul'))} | {cmpstr[t]} |")
q = Q['park']['official_2025_01']
L += ['', f"공식 도시계획시설 공원(UQ153 2024.11.07, `park/facilities_park_official_2025_01.*`): {f(q['rows'])}개, 좌표율 {pct(q['coord_rate'])}, 서울 경계 내 합집합 면적 {q['union_area_in_seoul_km2']}km².", '']
L += ['## 파일 구성(각 유형 폴더)', '',
      '- `facilities_<유형>_2020_01.csv/.parquet`, `facilities_<유형>_2025_01.csv/.parquet` (UTF-8-BOM, 공통 열 + `sz_` 규모변수 + 유형 고유 열)',
      '- `qa_<유형>.json` (원천→최종 계수, 좌표율, 대조, 중복, 서울 밖, raw 파일 url·sha256)', '- `build_<유형>.py` (원본에서 재생성; 공통 함수 `../_lib/fac.py`)',
      '- `raw/` 원본과 `.metadata.json`, 지오코딩 캐시 `raw/geocoding/`(키 미포함)',
      '- 추가: `school/zones_es_*.gpkg`(초등 통학구역), `school/zones_ms_*.gpkg`(중학교 학구), `school/zones_link_*.csv`(학교-학구 연계), '
      '`subway_station/subway_line_station_*.csv`(노선-역 단위), `park/parks_osm_*.gpkg`·`park/parks_official_2025_01.gpkg`(폴리곤), '
      '`retail_daily/facilities_retail_daily_2020_01_sens202003.*`·`clinic_sbiz/..._sens202003.*`(2020.03판 민감도)', '']
L += ['## 유형별 메모', '']
for t, nm in T:
    q = Q[t]; L += [f'### {nm} (`{t}`)', '']
    for n in q.get('notes', []):
        L += ['```text', n, '```', '']
    extra = {k: v for k, v in q.items() if k not in ('notes', 'raw_files', 'generated_utc', 'type', '2020_01', '2025_01')}
    for s in ['2020_01', '2025_01']:
        d = q.get(s, {})
        keep = {k: v for k, v in d.items() if k in ('rows', 'coord_method', 'subtype', 'dup_facility_id', 'dup_exact_xy', 'by_level', 'by_type_vs_official',
                                                   'flag_id_issued_after_ref', 'flag_nonbulk_id', 'unresolved_names', 'excluded_suspended', 'closed_sub_included',
                                                   'removed_open_after_ref', 'by_subtype_area_km2', 'sum_students', 'sum_classes', 'sum_capacity', 'sum_children',
                                                   'names_only_in_main', 'names_only_in_alt', 'point_in_other_dong', 'installed_after_ref_excluded')}
        L += [f'- {s}: `' + json.dumps(keep, ensure_ascii=False) + '`']
    for k, v in extra.items():
        L += [f'- {k}: `' + json.dumps(v, ensure_ascii=False, default=str)[:1500] + '`']
    L += ['']
L += ['## 실패·보류·주의', '',
      f"- 주민센터: 2019.06판 주소 중 {f(g(Q['community_center'],'2020_01','coord_method',{}).get('unresolved',0))}건, 2024.07판 {f(g(Q['community_center'],'2025_01','coord_method',{}).get('unresolved',0))}건은 폐지·변경된 도로명주소로 정확 일치 지오코딩 실패 → unresolved로 남김. 허용창 안의 판이 없어 −6개월/−5개월 판 사용(C).",
      f"- 어린이집: 역산(B)은 보육통계보다 {g(Q['childcare'],'2020_01','diff_total_pct')}% / {g(Q['childcare'],'2025_01','diff_total_pct')}% 많음(가정·법인단체 과다: 폐지일 입력 지연 추정). 정원·현원은 현재값.",
      '- 따릉이 2020: 설치시기 역산이라 2020년 중 철거·재설치 대여소 누락 가능. 공식 연말 대여소 수 대조 보류.',
      '- 소방: 연도판 기준월 미표기(reference_month_delta 비움). 공식 통계 대조 보류.',
      '- 지하철: 개통일은 원천에 없고 조사된 신규역 목록으로 역산(B). GTX-A 삼성은 미개통으로 두 시점 모두 제외. 좌표는 현재판(역 위치 불변 가정). 서울 경계 밖 역은 제외.',
      '- 공원: 북한산국립공원이 2020에는 way(leisure=nature_reserve+boundary=national_park), 2025에는 relation(boundary=national_park)으로 태그·객체가 바뀌어 facility_id가 다름. 국립공원·도시자연공원 등 산지형 녹지를 뺀 비교는 leisure=park 기준 권장. 공식 공원 면적 대비 OSM 피복률이 낮은 것은 도시자연공원·근린공원 산지부가 OSM에서 natural=wood 등으로만 표현되기 때문으로 보임(미검증).',
      '- 일상소매·의원(상가업소) 2019.12·2020.03은 2025-11 재작성본(모든 번호가 기준일 이후 발급, flag_id_issued_after_ref 전부 True) → grade B. 소진공 원 배포본을 받으면 교체.',
      '- 학교: 2019하 교육통계는 주소가 없어 2020상 주소 연결, 학급수 기준이 인가(2019)→편성(2024)으로 바뀜(sz_class_basis).',
      '- `school/zones_es_2020_01.gpkg-journal`은 첫 시도(네트워크 드라이브 sqlite 잠금 오류) 때 남은 빈 파일로 삭제 금지 규칙 때문에 남겨 둠 — 무시해도 됨.', '']
(H / 'README.md').write_text('\n'.join(L), encoding='utf-8')
print('ok', len(L))
