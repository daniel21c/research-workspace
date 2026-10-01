from pathlib import Path
S=Path(__file__).resolve().parent;Q=S/'접근성분석_패키지'
for n in ['a00_config.py','a06_engine.py','a06b_summary.py','a06c_delta.py','a08_ku_compare.py','a10_verify.py']:
 p=Q/'코드'/n;s=p.read_text(encoding='utf8').replace('33종','32종').replace('8개 카테고리','현재 설정 카테고리').replace('기능 카테고리 8개','기능 카테고리 7개').replace('시설 28종','시설 27종').replace('카테고리(8개 또는 통제)','카테고리(7개 또는 통제)').replace('체육 "규칙 없음"(취소·말소 포함) 민감도는 분석용 파일에 해당 행이 없어 계산하지 않았다.','체육시설업은 facility-v1.4에서 두 연도 전체 제외했다. 공공체육 대체 없음.')
 p.write_text(s,encoding='utf8')
p=Q/'코드/tests/test_release.py';s=p.read_text(encoding='utf8');mark="if __name__=='__main__':unittest.main()"
tests='''    def test_active_scope_excludes_sports_without_replacement(self):
        import a00_config as C
        import a06_engine as E
        self.assertEqual((len(C.CAT_A),sum(map(len,C.CAT_A.values()))),(7,27))
        self.assertNotIn('체육시설업',[f for fs in C.CAT_A.values() for f in fs])
        self.assertEqual(E.CAT_B_ORDER,['교육','돌봄','의료','편의'])
        self.assertEqual(C.CAT_A4['문화'],['문화'])
        self.assertFalse(C.ANALYSIS_SCOPE['public_sports_replacement'])

    def test_category_removal_preserves_reach_time_but_changes_mai(self):
        import a06_engine as E
        o=np.array([0]);d=np.array([1]);t=np.array([60.0]);units={'none':None}
        old=E.origin_access(o,d,t,np.array([0,255],dtype=np.uint16),units,K=8,T=900)['none']
        new=E.origin_access(o,d,t,np.array([0,127],dtype=np.uint16),units,K=7,T=900)['none']
        np.testing.assert_equal(new['r'],old['r'][:,:7]);np.testing.assert_equal(new['t'],old['t'][:,:7])
        self.assertTrue((old['m']==8).all());self.assertTrue((new['m']==7).all())

    def test_seven_category_composite_uses_seven_denominator(self):
        import a06_engine as E
        cats=list('ABCDEFG')
        frame=pd.DataFrame([dict(gi=0,pop=10,dong424=1,b='none',cat=c,r=int(i<6),m=1. if i<6 else np.nan,t=60. if i<6 else np.nan) for i,c in enumerate(cats)])
        with patch.object(E,'BOUNDS',['none']):out=E.aggregate(frame,'dong424',cats,900,False)
        row=out[out.cat.eq('종합')].iloc[0]
        self.assertAlmostEqual(row.COV,6/7);self.assertEqual(row.n_cat_mai,6);self.assertEqual(row.MAI,1)

'''
assert mark in s;p.write_text(s.replace(mark,tests+mark),encoding='utf8')
print('runtime code frozen; release tests14')
