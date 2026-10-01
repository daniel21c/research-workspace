"""Release regressions: missing evidence, stale code, xb scope, fixed category support."""
import sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import a11_provenance as P
import a06c_delta as D
import a10_verify as V

class ReleaseTests(unittest.TestCase):
    def test_portable_v2_inputs_and_upstream_stale(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);repo=root/'repo';repo.mkdir()
            upstream=repo/'facility';upstream.write_text('source')
            source=root/'stage';(source/'데이터/입력').mkdir(parents=True)
            (source/'코드').mkdir();(source/'results').mkdir()
            inp=source/'데이터/입력/grid';inp.write_text('grid')
            code=source/'코드/engine.py';code.write_text('code')
            out=source/'results/out.csv';out.write_text('result')
            m={'catset':'B','checks':{k:True for k in P.required_checks({'catset':'B'})},
               'files_base':'run_meta_directory','files':[{'file':'out.csv','sha256':P.sha256(out)}],
               'provenance':{'schema':P.SCHEMA,'input_base':'package_inputs',
                  'inputs':P.inventory([inp],source/'데이터/입력'),
                  'code':P.inventory([code],source/'코드'),'upstream_inputs':P.inventory([upstream],repo)}}
            target=root/'published';shutil.copytree(source,target)
            kw=dict(package_root=target,code_dir=target/'코드',repo_root=repo)
            self.assertEqual(P.metadata_issues(m,target/'results/run_meta.json',**kw),([],[]))
            upstream.write_text('changed source')
            failures,unknown=P.metadata_issues(m,target/'results/run_meta.json',**kw)
            self.assertTrue(any(s.startswith('upstream stale/missing:') for s in failures));self.assertFalse(unknown)

    def test_union_dataset_files(self):
        from types import SimpleNamespace
        u=SimpleNamespace(children=[SimpleNamespace(files=['b','a']),SimpleNamespace(children=[SimpleNamespace(files=['a','c'])])])
        self.assertEqual(P.dataset_files(u),['a','b','c'])

    def test_empty_checks_not_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_text('x')
            m={'catset':'B','checks':{},'files':[{'file':'x','sha256':P.sha256(p)}],'files_base':'run_meta_directory'}
            fail,unknown=P.metadata_issues(m,Path(d)/'run_meta.json')
            self.assertFalse(fail);self.assertIn('no invariant checks recorded',unknown)

    def test_false_and_nonboolean_checks_fail(self):
        m={'catset':'B','checks':{k:True for k in P.required_checks({'catset':'B'})}}
        m['checks']['COV_in_0_1']=1
        self.assertTrue(any('COV_in_0_1' in s for s in P.metadata_issues(m,'x')[0]))

    def test_stale_code_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'engine.py';p.write_text('one')
            inv=P.inventory([p],d);self.assertEqual(P.check_inventory(inv,d),[])
            p.write_text('two')
            self.assertTrue(P.check_inventory(inv,d))

    def test_inventory_digest_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_text('x');inv=P.inventory([p],d)
            inv['files'][0]['sha256']='0'*64
            self.assertIn('empty or invalid fingerprint digest',P.check_inventory(inv,d))

    def test_xb_requires_explicit_sfca_scope(self):
        m={'catset':'A','boundary_year':{'ld_other':2020}}
        self.assertIn('xb must explicitly record skipped 2SFCA',P.metadata_issues(m,'x')[0])
        m['sfca_skipped']='not computed'
        self.assertNotIn('xb must explicitly record skipped 2SFCA',P.metadata_issues(m,'x')[0])

    def test_temporal_four_conditions(self):
        def table(aa,bb):
            rows=[(u,b,c,v) for u in [1,2] for b,vs in [('ld',aa),('lz116',bb)] for c,v in zip(['A','B'],vs)]
            t=pd.DataFrame(rows,columns=['unit_id','b','cat','MAI']).assign(unit_level='dong424')
            t.loc[(t.unit_id==2)&(t.b=='ld'),'MAI']=np.nan
            return t
        a=table([2,4],[1,2]);b=table([4,np.nan],[2,3])
        z=D.temporal_dmai_common4(a,b)
        self.assertAlmostEqual(z.loc[1,'change_common4'],1)
        self.assertAlmostEqual(z.loc[1,'change_pairwise'],0.5)
        self.assertEqual(z.loc[1,'n_common4'],1)
        self.assertEqual(z.loc[2,'n_common4'],0);self.assertTrue(pd.isna(z.loc[2,'change_common4']))

    def test_none_lz_common_categories(self):
        u=pd.DataFrame([(1,'none','A',4),(1,'none','B',2),(1,'lz116','A',3),(1,'lz116','B',np.nan)],columns=['unit_id','b','cat','MAI']).assign(unit_level='dong424')
        self.assertEqual(D.dong_delta(u,'MAI',pair=('none','lz116')).loc[1],1)

    def test_duplicate_input_rejected(self):
        u=pd.DataFrame([(1,'ld','A',4)]*2,columns=['unit_id','b','cat','MAI']).assign(unit_level='dong424')
        with self.assertRaises(ValueError):D.dong_delta(u,'MAI')

    def test_manifest_unlisted_and_duplicates(self):
        import csv
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'x';p.write_text('x');mf=root/'manifest.csv'
            row=dict(file='x',sha256=P.sha256(p),bytes=1)
            with mf.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerows([row,row])
            (root/'unlisted').write_text('y')
            n,bad=V.manifest_errors(root,mf)
            self.assertEqual(n,2);self.assertEqual(len(bad),2)

    def test_active_scope_excludes_sports_without_replacement(self):
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

if __name__=='__main__':unittest.main()
