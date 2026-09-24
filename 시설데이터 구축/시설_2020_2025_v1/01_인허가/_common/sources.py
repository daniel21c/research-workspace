"""유형별 원천 정의(인허가 업종 slug, 서울 열린데이터광장 OA-ID, data.go.kr ID)."""
CAT = {  # slug: (업종명, OA-ID, data.go.kr id)
    'clinics': ('의원', 'OA-16480', '15045024'), 'hospitals': ('병원', 'OA-16479', '15045025'),
    'pharmacies': ('약국', 'OA-16484', '15045036'), 'postpartum_care': ('산후조리업', 'OA-16482', '15045027'),
    'over_the_counter_medicine_stores': ('안전상비의약품 판매업소', 'OA-16483', '15045034'),
    'optical_shops': ('안경업', 'OA-16490', '15045028'), 'animal_hospitals': ('동물병원', 'OA-16007', '15045050'),
    'fitness_centers': ('체력단련장업', 'OA-16142', '15045048'), 'martial_arts_dojo': ('체육도장업', 'OA-16141', '15045045'),
    'swimming_pools': ('수영장업', 'OA-16137', '15045047'), 'golf_practice_ranges': ('골프연습장업', 'OA-16131', '15045079'),
    'billiard_halls': ('당구장업', 'OA-16133', '15045107'), 'comprehensive_sports_facilities': ('종합체육시설업', 'OA-16138', '15045039'),
    'ice_rinks': ('빙상장업', 'OA-16136', '15045042'), 'performance_halls': ('공연장', 'OA-16021', '15045106'),
    'movie_theaters': ('영화상영관', 'OA-16053', '15045008'), 'large_scale_retail_stores': ('대규모점포', 'OA-16096', '15045013'),
    'livestock_retail': ('축산판매업', 'OA-16071', '15101549'), 'other_food_retailers': ('식품판매업(기타)', 'OA-16080', '15044979'),
    'instant_food_processors': ('즉석판매제조가공업', 'OA-16085', '15044977'), 'bakeries': ('제과점영업', 'OA-16084', '15044973'),
    'general_restaurants': ('일반음식점', 'OA-16094', '15045016'), 'rest_cafes': ('휴게음식점', 'OA-16095', '15006730'),
    'barber_shops': ('이용업', 'OA-16064', '15045038'), 'beauty_salons': ('미용업', 'OA-16063', '15045037'),
    'laundries': ('세탁업', 'OA-16065', '15044964'), 'public_baths': ('목욕장업', 'OA-16146', '15045082'),
    'oil_retailers': ('석유판매업', 'OA-16110', '15044961'),
}

def src(slug, kind='seoul_sheet', subtype=None):
    nm, oa, dg = CAT[slug]
    d = {'slug': slug, 'kind': kind, 'oa': oa,
         'dest_name': f'{slug}_seoul_{oa}.csv' if kind == 'seoul_sheet' else f'{slug}_localdata_6110000_ALL.csv',
         'dataset': f'지방행정 인허가 {nm} (data.seoul {oa}; data.go.kr {dg})'}
    if subtype:
        d['subtype'] = subtype
    return d
