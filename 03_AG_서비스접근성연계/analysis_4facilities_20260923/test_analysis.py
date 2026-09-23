import tempfile
from pathlib import Path
import unittest
import struct
import zlib
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point,Polygon
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import run_analysis as A

class TestAnalysis(unittest.TestCase):
    def test_dense_signed_delta_and_offsets(self):
        c=A.pbf_classes();b=c['PrimitiveBlock'](granularity=100,lat_offset=300,lon_offset=-200);d=c['DenseNodes'](id=[100,-10,3],lon=[100,-20,5],lat=[-30,5,-1])
        ids,x,y=A.decode_dense(d,b)
        np.testing.assert_array_equal(ids,[100,90,93]);np.testing.assert_allclose(x,[9800e-9,7800e-9,8300e-9]);np.testing.assert_allclose(y,[-2700e-9,-2200e-9,-2300e-9])
    def test_pbf_zlib_roundtrip(self):
        c=A.pbf_classes();h=c['HeaderBlock'](required_features=['OsmSchema-V0.6'],osmosis_replication_timestamp=123)
        raw=h.SerializeToString();b=c['Blob'](zlib_data=zlib.compress(raw),raw_size=len(raw)).SerializeToString();bh=c['BlobHeader'](type='OSMHeader',datasize=len(b)).SerializeToString()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tiny.pbf';p.write_bytes(struct.pack('!I',len(bh))+bh+b);r=list(A.read_blocks(p));self.assertEqual(r[0][1].osmosis_replication_timestamp,123)
    def test_foot_permissions(self):
        self.assertIsNone(A.foot_direction({'highway':'motorway'}));self.assertIsNone(A.foot_direction({'highway':'residential','access':'private'}));self.assertEqual(A.foot_direction({'highway':'residential','access':'private','foot':'yes'}),0)
        self.assertEqual(A.foot_direction({'highway':'footway','oneway:foot':'-1'}),-1);self.assertEqual(A.foot_direction({'highway':'residential','oneway':'yes'}),0)
        self.assertIsNone(A.foot_direction({'highway':'path','foot:conditional':'yes @ daylight'}));self.assertTrue(A.blocked_node({'barrier':'wall'}));self.assertFalse(A.blocked_node({'barrier':'gate','foot':'yes'}))
    def test_topology_not_geometric_intersection(self):
        c=A.pbf_classes();b=c['PrimitiveBlock']();b.stringtable.s.extend([b'',b'highway',b'footway',b'barrier',b'wall',b'oneway:foot',b'yes',b'access',b'private',b'foot'])
        ns=b.primitivegroup.add()
        for nid,x,y in [(1,127,37.5),(2,127.002,37.5),(3,127.001,37.499),(4,127.001,37.501),(5,127.003,37.5),(6,127.003,37.501),(7,127.004,37.501)]:
            n=ns.nodes.add(id=nid,lon=round(x*1e7),lat=round(y*1e7))
            if nid==5:n.keys.extend([3]);n.vals.extend([4])
        ws=b.primitivegroup.add()
        for wid,refs,oneway in [(10,[1,2],False),(11,[3,4],False),(12,[2,5],False),(13,[2,4],True)]:
            w=ws.ways.add(id=wid);w.keys.extend([1]);w.vals.extend([2]);w.refs.extend(np.diff([0]+refs).tolist())
            if oneway:w.keys.extend([5]);w.vals.extend([6])
        for wid,nid,explicit_foot in [(14,6,False),(15,7,True)]:
            w=ws.ways.add(id=wid);w.keys.extend([1,7]);w.vals.extend([2,8]);w.refs.extend([4,nid-4])
            if explicit_foot:w.keys.extend([9]);w.vals.extend([6])
        # Segments1-2 and3-4 cross geometrically; graph only joins them via
        # explicit one-way2->4. Reverse4->2 must not exist; barrier5 excluded.
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tiny.pbf'
            payload=b.SerializeToString();blob=c['Blob'](raw=payload).SerializeToString();h=c['BlobHeader'](type='OSMData',datasize=len(blob)).SerializeToString();p.write_bytes(struct.pack('!I',len(h))+h+blob)
            graph,xy,meta=A.build_network(p,(126,37,128,38));self.assertEqual(meta['nodes'],5);self.assertEqual(meta['blocked_nodes'],1)
            distances=dijkstra(graph,indices=3,directed=True);self.assertTrue(np.isinf(distances[0]));self.assertTrue(np.isfinite(distances[2]));self.assertTrue(np.isfinite(dijkstra(graph,indices=0,directed=True)[3]))
            self.assertTrue(np.isfinite(distances[4]));self.assertEqual(A.validate_pbf_references(p,(126,37,128,38))['missing_references'],0)
    def test_orphan_references_fail_closed(self):
        c=A.pbf_classes();b=c['PrimitiveBlock']();b.stringtable.s.extend([b'',b'highway',b'footway'])
        b.primitivegroup.add().nodes.add(id=1,lon=1270000000,lat=375000000)
        w=b.primitivegroup.add().ways.add(id=10);w.keys.extend([1]);w.vals.extend([2]);w.refs.extend([1,998])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'orphan.pbf';payload=b.SerializeToString();blob=c['Blob'](raw=payload).SerializeToString();h=c['BlobHeader'](type='OSMData',datasize=len(blob)).SerializeToString();p.write_bytes(struct.pack('!I',len(h))+h+blob)
            with self.assertRaisesRegex(ValueError,'Orphan'):A.validate_pbf_references(p,(126,37,128,38))
    def test_node_after_way_fails_closed(self):
        c=A.pbf_classes();b=c['PrimitiveBlock']();b.stringtable.s.extend([b'',b'highway',b'footway'])
        w=b.primitivegroup.add().ways.add(id=10);w.keys.extend([1]);w.vals.extend([2]);w.refs.extend([1,1])
        b.primitivegroup.add().nodes.add(id=1,lon=1270000000,lat=375000000)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'order.pbf';payload=b.SerializeToString();blob=c['Blob'](raw=payload).SerializeToString();h=c['BlobHeader'](type='OSMData',datasize=len(blob)).SerializeToString();p.write_bytes(struct.pack('!I',len(h))+h+blob)
            with self.assertRaisesRegex(ValueError,'node-after-way'):A.build_network(p,(126,37,128,38))
    def test_metrics_ties_threshold_and_internal(self):
        r=A.metrics_for_distances(np.array([600.,600.,1001.]),np.array([True,False,True]),1000)
        self.assertEqual(r['opportunities'],2);self.assertEqual(r['internal_opportunities'],1);self.assertEqual(r['nearest_tie_count'],2);self.assertEqual((r['nir_lower'],r['nir_upper']),(0,1))
        self.assertEqual(A.metrics_for_distances(np.array([1000.]),np.array([False]),1000)['covered'],1)
    def test_unknown_never_removed_from_denominator(self):
        rows=[]
        for pop,ds in [(9.,np.array([100.])),(1.,np.array([np.inf]))]:
            rows.append({'year':2020,'pop':pop,'origin_network_available':int(np.isfinite(ds[0])),'origin_zone_available':1,**A.metrics_for_distances(ds,np.array([True]),1000)})
        r=A.aggregate(pd.DataFrame(rows),['year']).iloc[0];self.assertEqual(r.population,10);self.assertEqual(r.covered,.9);self.assertEqual(r.nearest_m_eligible_population,9)
    def test_polygon_ties_and_gaps(self):
        b=gpd.GeoDataFrame({'zone':['a','b']},geometry=[Polygon([(0,0),(1,0),(1,1),(0,1)]),Polygon([(1,0),(2,0),(2,1),(1,1)])],crs=5179)
        p=gpd.GeoDataFrame(geometry=[Point(.5,.5),Point(1,.5),Point(3,.5)],crs=5179);a,n=A.assign_zones(p,b);self.assertEqual(a.tolist(),['a','','']);self.assertEqual(n.tolist(),[1,2,0])
    def test_4kmh_thresholds(self):
        self.assertAlmostEqual(4*1000/60*10,666.6666666666666);self.assertAlmostEqual(4*1000/60*15,1000)
    def test_regional_pairs_follow_origin_ids(self):
        common={'year':2025,'category':'LIBRARY_PUBLIC','snap_cap_m':100,'threshold_minutes':15,'origin_zone_available':1,'covered':1}
        rows=[{**common,'origin_id':'a','zone':'LZ-A','pop':9,'boundary':'LZ_original','internal_covered':1},
              {**common,'origin_id':'b','zone':'LZ-B','pop':1,'boundary':'LZ_original','internal_covered':0},
              {**common,'origin_id':'b','zone':'UNRELATED-X','pop':1,'boundary':'LD','internal_covered':1},
              {**common,'origin_id':'a','zone':'UNRELATED-Y','pop':9,'boundary':'LD','internal_covered':0}]
        result=A.regional_library_pairs(pd.DataFrame(rows)).set_index('LZ_original_zone')
        self.assertEqual(result.loc['LZ-A','population'],9)
        self.assertEqual(result.loc['LZ-A','LD_minus_LZ_same_origins'],-1)
        self.assertEqual(result.loc['LZ-B','LD_minus_LZ_same_origins'],1)

if __name__=='__main__':unittest.main()
