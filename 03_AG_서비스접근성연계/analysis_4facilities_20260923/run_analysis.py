"""Reproducible fixed-reference pedestrian-network scenario; no API or service."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
import zlib
import numpy as np
import pandas as pd
import geopandas as gpd
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
import config as C

def log(s):
    print(time.strftime('%H:%M:%S'), s, flush=True)

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_json(path, obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def verify_unit_suite():
    import io,unittest
    output=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName('test_analysis')
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    (C.RESULTS/'unit_test_output.txt').write_text(output.getvalue(),encoding='utf-8')
    assert result.wasSuccessful(),output.getvalue()
    return result.testsRun

def finalize_manifests():
    from importlib.metadata import version
    packages=['numpy','pandas','geopandas','shapely','pyproj','pyogrio','scipy','pyarrow','protobuf','openpyxl','matplotlib']
    write_json(C.RESULTS/'environment_versions.json',{p:version(p) for p in packages})
    write_json(C.RESULTS/'code_manifest.json',[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(C.HERE.iterdir()) if p.is_file() and p.suffix in ('.py','.md','.txt')])
    write_json(C.RESULTS/'output_manifest.json',[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(C.RESULTS.iterdir()) if p.is_file() and p.name!='output_manifest.json'])

def pbf_classes():
    """Minimal wire schema, independently declared from OSM-binary field numbers.

    Unknown metadata/relations are ignored. Historical/deletion files fail closed.
    https://github.com/openstreetmap/OSM-binary/tree/master/osmpbf
    """
    fd=descriptor_pb2.FileDescriptorProto(name='analysis_osm.proto',package='A',syntax='proto2')
    F=descriptor_pb2.FieldDescriptorProto
    specs={
      'BlobHeader':[('type',1,F.TYPE_STRING,False,None),('datasize',3,F.TYPE_INT32,False,None)],
      'Blob':[('raw',1,F.TYPE_BYTES,False,None),('raw_size',2,F.TYPE_INT32,False,None),('zlib_data',3,F.TYPE_BYTES,False,None)],
      'HeaderBlock':[('required_features',4,F.TYPE_STRING,True,None),('writingprogram',16,F.TYPE_STRING,False,None),('source',17,F.TYPE_STRING,False,None),('osmosis_replication_timestamp',32,F.TYPE_INT64,False,None)],
      'StringTable':[('s',1,F.TYPE_BYTES,True,None)],
      'Node':[('id',1,F.TYPE_SINT64,False,None),('keys',2,F.TYPE_UINT32,True,None),('vals',3,F.TYPE_UINT32,True,None),('lat',8,F.TYPE_SINT64,False,None),('lon',9,F.TYPE_SINT64,False,None)],
      'DenseNodes':[('id',1,F.TYPE_SINT64,True,None),('lat',8,F.TYPE_SINT64,True,None),('lon',9,F.TYPE_SINT64,True,None),('keys_vals',10,F.TYPE_INT32,True,None)],
      'Way':[('id',1,F.TYPE_INT64,False,None),('keys',2,F.TYPE_UINT32,True,None),('vals',3,F.TYPE_UINT32,True,None),('refs',8,F.TYPE_SINT64,True,None)],
      'PrimitiveGroup':[('nodes',1,F.TYPE_MESSAGE,True,'Node'),('dense',2,F.TYPE_MESSAGE,False,'DenseNodes'),('ways',3,F.TYPE_MESSAGE,True,'Way')],
      'PrimitiveBlock':[('stringtable',1,F.TYPE_MESSAGE,False,'StringTable'),('primitivegroup',2,F.TYPE_MESSAGE,True,'PrimitiveGroup'),('granularity',17,F.TYPE_INT32,False,None),('lat_offset',19,F.TYPE_INT64,False,None),('lon_offset',20,F.TYPE_INT64,False,None)]}
    for name,fields in specs.items():
        m=fd.message_type.add(name=name)
        for name,num,typ,rep,ref in fields:
            f=m.field.add(name=name,number=num,type=typ,label=F.LABEL_REPEATED if rep else F.LABEL_OPTIONAL)
            if ref: f.type_name='.A.'+ref
            if rep and typ not in (F.TYPE_STRING,F.TYPE_BYTES,F.TYPE_MESSAGE): f.options.packed=True
            if name=='granularity': f.default_value='100'
    pool=descriptor_pool.DescriptorPool();pool.Add(fd)
    return {n:message_factory.GetMessageClass(pool.FindMessageTypeByName('A.'+n)) for n in specs}

def read_blocks(path):
    cls=pbf_classes()
    with open(path,'rb') as f:
        while prefix:=f.read(4):
            if len(prefix)!=4: raise ValueError('Truncated PBF prefix')
            size=struct.unpack('!I',prefix)[0]
            if size>65536: raise ValueError('Invalid PBF header size')
            h=cls['BlobHeader'].FromString(f.read(size))
            if h.datasize>32*1024*1024: raise ValueError('Oversize PBF blob')
            b=cls['Blob'].FromString(f.read(h.datasize))
            raw=b.raw if b.HasField('raw') else zlib.decompress(b.zlib_data)
            if b.HasField('raw_size') and len(raw)!=b.raw_size: raise ValueError('PBF size mismatch')
            if h.type=='OSMHeader': yield h.type,cls['HeaderBlock'].FromString(raw)
            elif h.type=='OSMData': yield h.type,cls['PrimitiveBlock'].FromString(raw)

DENIED={'no','private','agricultural','forestry','delivery','use_sidepath'}
ALLOWED_HIGHWAYS={'primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','road','living_street','service','track','path','steps','pedestrian','footway'}

def foot_direction(tags):
    """Return +1/-1/0 (bidirectional), or None. Conditional restrictions excluded."""
    if tags.get('area')=='yes' or any(k in tags for k in ('foot:conditional','access:conditional')): return None
    if tags.get('highway') not in ALLOWED_HIGHWAYS: return None
    access=tags.get('foot',tags.get('access',''))
    if access in DENIED: return None
    if tags.get('construction') or tags.get('highway') in {'construction','proposed'}: return None
    one=tags.get('oneway:foot','no')
    if one in {'yes','1','true'}: return 1
    if one=='-1': return -1
    return 0

def blocked_node(tags):
    access=tags.get('foot',tags.get('access',''))
    if access in DENIED: return True
    if access in {'yes','designated','permissive'}: return False
    return tags.get('barrier') in {'yes','wall','fence','gate','locked_gate','turnstile'} or tags.get('locked')=='yes'

def decode_dense(dense,block):
    ids=np.cumsum(np.asarray(dense.id,dtype=np.int64))
    lon=(np.cumsum(np.asarray(dense.lon,dtype=np.int64))*block.granularity+block.lon_offset)*1e-9
    lat=(np.cumsum(np.asarray(dense.lat,dtype=np.int64))*block.granularity+block.lat_offset)*1e-9
    return ids,lon,lat

def build_network(pbf,bbox):
    started=time.monotonic(); nodes={}; blocked=set();edges={}; ways=Counter();header={};nblocks=0;seen_ways=False;partial_ways=0
    for typ,b in read_blocks(pbf):
        if time.monotonic()-started>C.MAX_RUNTIME_SECONDS: raise TimeoutError('PBF runtime bound exceeded')
        if typ=='OSMHeader':
            if set(b.required_features)-{'OsmSchema-V0.6','DenseNodes'}: raise ValueError('Unsupported required PBF feature')
            header={'required_features':list(b.required_features),'writingprogram':b.writingprogram,'source':b.source,'replication_timestamp':b.osmosis_replication_timestamp,'replication_date_utc':datetime.fromtimestamp(b.osmosis_replication_timestamp,timezone.utc).isoformat() if b.osmosis_replication_timestamp else None}
            continue
        nblocks+=1
        st=[s.decode('utf-8') for s in b.stringtable.s]
        for group in b.primitivegroup:
            if seen_ways and (group.HasField('dense') or len(group.nodes)):
                raise ValueError('Unsupported node-after-way ordering; two-pass parser required')
            if group.HasField('dense'):
                ids,lon,lat=decode_dense(group.dense,b)
                keep=(lon>=bbox[0])&(lon<=bbox[2])&(lat>=bbox[1])&(lat<=bbox[3])
                chosen=np.flatnonzero(keep)
                for i in chosen: nodes[int(ids[i])]=(float(lon[i]),float(lat[i]))
                if len(chosen) and group.dense.keys_vals:
                    kv=group.dense.keys_vals;pos=0
                    for i,node in enumerate(ids):
                        tags={}
                        while kv[pos]!=0:
                            if keep[i]: tags[st[kv[pos]]]=st[kv[pos+1]]
                            pos+=2
                        pos+=1
                        if keep[i] and blocked_node(tags): blocked.add(int(node))
            for node in group.nodes:
                lon=(node.lon*b.granularity+b.lon_offset)*1e-9;lat=(node.lat*b.granularity+b.lat_offset)*1e-9
                if bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]:
                    nodes[node.id]=(lon,lat)
                    if blocked_node(dict(zip((st[k] for k in node.keys),(st[v] for v in node.vals)))): blocked.add(node.id)
            for way in group.ways:
                seen_ways=True
                tags=dict(zip((st[k] for k in way.keys),(st[v] for v in way.vals)));direct=foot_direction(tags)
                if direct is None: continue
                refs=np.cumsum(np.asarray(way.refs,dtype=np.int64));used=False
                kept=sum(int(n) in nodes for n in refs)
                if 0<kept<len(refs):partial_ways+=1
                for u,v in zip(refs[:-1],refs[1:]):
                    u=int(u);v=int(v)
                    if u==v or u not in nodes or v not in nodes or u in blocked or v in blocked: continue
                    if direct>=0: edges[(u,v)]=1
                    if direct<=0: edges[(v,u)]=1
                    used=True
                if used: ways[tags['highway']]+=1
        if nblocks%500==0: log(f'PBF blocks={nblocks}, bbox nodes={len(nodes):,}, directed edges={len(edges):,}')
    used=sorted({v for e in edges for v in e});idx={v:i for i,v in enumerate(used)}
    ll=np.array([nodes[v] for v in used]);x,y=Transformer.from_crs(4326,C.METRIC_CRS,always_xy=True).transform(ll[:,0],ll[:,1]);xy=np.column_stack([x,y])
    uv=np.array([(idx[u],idx[v]) for u,v in edges],dtype=np.int32);length=np.linalg.norm(xy[uv[:,0]]-xy[uv[:,1]],axis=1)
    graph=csr_matrix((length,(uv[:,0],uv[:,1])),shape=(len(used),len(used)))
    components,labels=connected_components(graph,directed=True,connection='weak')
    meta={**header,'bbox':list(bbox),'nodes':len(used),'directed_edges':len(uv),'blocked_nodes':len(blocked),'highway_way_counts':dict(ways),'weak_components':components,'largest_component_nodes':int(np.bincount(labels).max()),'walking_speed_kmh':C.SPEED_KMH,'metric':'projected length / constant speed','fixed_network_both_years':True,'node_before_way_order_verified':True,'partially_clipped_ways':partial_ways,'elapsed_seconds':time.monotonic()-started}
    return graph,xy,meta

def assign_zones(points,zones):
    """Strictly unique covered polygon; ambiguity and noncoverage never guessed."""
    pairs=gpd.sjoin(points[['geometry']],zones[['zone','geometry']],how='left',predicate='intersects')
    values=pairs.groupby(level=0)['zone'].agg(lambda s:sorted(set(s.dropna())))
    return pd.Series([v[0] if len(v)==1 else '' for v in values],index=points.index),pd.Series([len(v) for v in values],index=points.index)

def validate_population_grid(origins):
    grid=gpd.read_file(C.GRID).to_crs(C.METRIC_CRS).set_index('gid')
    assert grid.index.is_unique and origins.start_gid.is_unique
    missing=~origins.start_gid.isin(grid.index)
    assert not missing.any(),'Population origin IDs absent from reference grid'
    aligned=grid.loc[origins.start_gid].reset_index(drop=True)
    distance=origins.geometry.reset_index(drop=True).distance(aligned.geometry.centroid)
    area=aligned.geometry.area
    checks={'origin_count':len(origins),'reference_grid_count':len(grid),'population':float(origins['pop'].sum()),'missing_grid_ids':int(missing.sum()),'max_origin_centroid_difference_m':float(distance.max()),'min_cell_area_m2':float(area.min()),'max_cell_area_m2':float(area.max()),'population_reference_year_status':'UNVERIFIED_FIXED_REFERENCE'}
    assert (distance<1e-5).all() and np.isclose(area,250**2,atol=.1,rtol=0).all()
    return checks

def validate_pbf_references(pbf,bbox):
    """Audit missing references separately from intentional bbox clipping.

    Retain compact global node-ID arrays, but validate only allowed ways touching
    the routing bbox. An out-of-bbox node exists in the file; an orphan does not.
    No coordinate-derived crossing is added and no graph result is modified.
    """
    node_chunks=[];inside=set();ref_chunks=[];way_count=0;seen_ways=False
    for typ,b in read_blocks(pbf):
        if typ!='OSMData':continue
        st=[s.decode('utf-8') for s in b.stringtable.s]
        for group in b.primitivegroup:
            if seen_ways and (group.HasField('dense') or len(group.nodes)):
                raise ValueError('Node after way in reference audit')
            if group.HasField('dense'):
                ids,lon,lat=decode_dense(group.dense,b);node_chunks.append(ids)
                keep=(lon>=bbox[0])&(lon<=bbox[2])&(lat>=bbox[1])&(lat<=bbox[3])
                inside.update(int(v) for v in ids[keep])
            if group.nodes:
                node_chunks.append(np.array([n.id for n in group.nodes],dtype=np.int64))
                for n in group.nodes:
                    lon=(n.lon*b.granularity+b.lon_offset)*1e-9;lat=(n.lat*b.granularity+b.lat_offset)*1e-9
                    if bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]:inside.add(n.id)
            for way in group.ways:
                seen_ways=True
                tags=dict(zip((st[k] for k in way.keys),(st[v] for v in way.vals)))
                if foot_direction(tags) is None:continue
                refs=np.cumsum(np.asarray(way.refs,dtype=np.int64))
                if any(int(n) in inside for n in refs):ref_chunks.append(refs);way_count+=1
    node_ids=np.unique(np.concatenate(node_chunks)) if node_chunks else np.array([],dtype=np.int64)
    refs=np.unique(np.concatenate(ref_chunks)) if ref_chunks else np.array([],dtype=np.int64)
    missing=np.setdiff1d(refs,node_ids,assume_unique=True)
    result={'global_unique_node_ids':len(node_ids),'relevant_allowed_ways':way_count,'relevant_unique_references':len(refs),'missing_references':len(missing),'node_before_way_order_verified':True}
    if len(missing):raise ValueError(f'Orphan node references in bbox-relevant ways: {missing[:10].tolist()}')
    return result

def load_boundaries():
    out={};orig=gpd.read_file(C.OFFICIAL).to_crs(C.METRIC_CRS)
    orig['zone']=orig['label_1'].astype(str);out['LZ_original']=orig[['zone','geometry']]
    p=C.CORE/'seoul_boundaries_all.gpkg'
    for y in C.YEARS:
        b=gpd.read_file(p,layer=f'leiden_community_{y}_116').to_crs(C.METRIC_CRS)
        b['zone']=b['ku_name'].astype(str)+'::'+b['community'].astype(str);out[f'LD_{y}']=b[['zone','geometry']]
    b=gpd.read_file(p,layer='official_livingzone_116').to_crs(C.METRIC_CRS)
    b['zone']=b['community_name'].astype(str);out['LZ_dong_sensitivity']=b[['zone','geometry']]
    return out

def metrics_for_distances(dist,internal,threshold_m):
    reachable=np.isfinite(dist)
    nearest=float(dist.min()) if reachable.any() else np.inf
    ties=np.isclose(dist,nearest,rtol=0,atol=1e-6)&reachable
    in_dist=dist[internal]
    nearest_in=float(in_dist.min()) if len(in_dist) else np.inf
    return {'covered':int(nearest<=threshold_m+1e-9),'opportunities':int((dist<=threshold_m+1e-9).sum()),'internal_covered':int(nearest_in<=threshold_m+1e-9),'internal_opportunities':int((in_dist<=threshold_m+1e-9).sum()),'nearest_m':nearest,'internal_nearest_m':nearest_in,'nearest_tie_count':int(ties.sum()),'nir_lower':int(ties.any() and internal[ties].all()),'nir_upper':int(ties.any() and internal[ties].any()),'nearest_available':int(reachable.any())}

def aggregate(frame,keys):
    rows=[]
    for key,g in frame.groupby(keys,dropna=False,sort=True):
        if not isinstance(key,tuple): key=(key,)
        r=dict(zip(keys,key));w=g['pop'].to_numpy();den=w.sum();r.update(population=den,origins=len(g))
        for field in ['covered','opportunities','internal_covered','internal_opportunities','nir_lower','nir_upper','nearest_available','origin_network_available','origin_zone_available','coverage_upper_origin_unknown','internal_coverage_upper_assignment_unknown','nir_unresolved']:
            if field not in g:continue
            r[field]=float(np.dot(w,g[field])/den) if den else np.nan
        r['coverage_penalty']=r['covered']-r['internal_covered']
        r['opportunity_penalty']=r['opportunities']-r['internal_opportunities']
        r['nearest_tie_population']=float(w[g.nearest_tie_count.to_numpy()>1].sum())
        for field in ['nearest_m','internal_nearest_m']:
            ok=np.isfinite(g[field]);r[field+'_eligible_population']=float(w[ok].sum())
            r[field+'_conditional_mean_minutes']=float(np.dot(w[ok],g.loc[ok,field])/w[ok].sum()/ (C.SPEED_KMH*1000/60)) if ok.any() else np.nan
        rows.append(r)
    return pd.DataFrame(rows)

def common_mapped_sensitivity(rows):
    """Identical origin cohort for LZ and LD; never replace full-city results."""
    z=rows.loc[rows.boundary.isin(['LZ_original','LD'])].copy()
    keys=['origin_id','year','category','snap_cap_m','threshold_minutes']
    ok=z.groupby(keys)[['origin_zone_available','origin_network_available']].transform('min').eq(1).all(axis=1)
    return aggregate(z.loc[ok],['year','category','boundary','snap_cap_m','threshold_minutes'])

def regional_library_pairs(rows):
    """Compare the same origins, grouped by original LZ, never match LZ/LD names."""
    z=rows.loc[(rows.year==2025)&rows.category.eq('LIBRARY_PUBLIC')&(rows.snap_cap_m==100)&(rows.threshold_minutes==15)]
    a=z.loc[z.boundary.eq('LZ_original'),['origin_id','zone','pop','covered','internal_covered']].rename(columns={'internal_covered':'lz_internal'})
    b=z.loc[z.boundary.eq('LD'),['origin_id','internal_covered','origin_zone_available']].rename(columns={'internal_covered':'ld_internal'})
    paired=a.merge(b,on='origin_id',validate='one_to_one');out=[]
    for zone,g in paired.groupby('zone'):
        pop=g['pop'].sum();w=g['pop']/pop
        out.append({'LZ_original_zone':zone,'population':pop,'origins':len(g),'covered':float((w*g.covered).sum()),'LZ_internal_covered':float((w*g.lz_internal).sum()),'LD_internal_covered_same_origins':float((w*g.ld_internal).sum()),'LD_minus_LZ_same_origins':float((w*(g.ld_internal-g.lz_internal)).sum()),'LD_unmapped_origin_population':float(g.loc[g.origin_zone_available.eq(0),'pop'].sum())})
    return pd.DataFrame(out).sort_values(['LZ_internal_covered','population'],ascending=[True,False])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');args=ap.parse_args()
    started=time.monotonic();C.RESULTS.mkdir(exist_ok=True)
    unit_count=verify_unit_suite() if not args.audit_only else None
    baseline_paths=[C.ORIGINS,C.GRID,C.PBF,C.CORE/'seoul_boundaries_all.gpkg',C.FACILITIES/'build_seoul_4facilities_clean_2020_2025.py',*C.FACILITIES.glob('seoul_facilities_*_clean.*'),*C.OFFICIAL.parent.glob(C.OFFICIAL.stem+'.*'),*C.GU.parent.glob(C.GU.stem+'.*')]
    baseline_hashes={str(p):sha256(p) for p in baseline_paths}
    from facility_audit import audit
    provenance,inputs=audit();log('Facility provenance audit finished')
    if args.audit_only: return
    origins=gpd.read_file(C.ORIGINS).to_crs(C.METRIC_CRS).reset_index(drop=True)
    assert origins.start_gid.is_unique and origins['pop'].gt(0).all()
    write_json(C.RESULTS/'population_grid_validation.json',validate_population_grid(origins))
    bounds=load_boundaries();fac={};zone_diagnostics=[]
    for key,b in bounds.items():
        assert b.zone.is_unique and b.geometry.is_valid.all() and not b.geometry.is_empty.any()
        origins[key],n=assign_zones(origins,b)
        zone_diagnostics.append({'entity':'origins','boundary':key,'count':len(origins),'unmapped':int((n==0).sum()),'ambiguous':int((n>1).sum()),'unmapped_population':float(origins.loc[n==0,'pop'].sum()),'ambiguous_population':float(origins.loc[n>1,'pop'].sum())})
    for y in C.YEARS:
        f=pd.read_parquet(C.FACILITIES/f'seoul_facilities_{y}_01_clean.parquet').sort_values('facility_id').reset_index(drop=True)
        lineage=pd.read_parquet(C.RESULTS/'facility_lineage.parquet')
        public_ids=set(lineage.loc[(lineage.year==y)&lineage.establishment.isin(['국립','공립']),'facility_id'])
        keep=~f.facility_category.eq('SCHOOL_BASIC')|f.facility_id.isin(public_ids)
        log(f'{y} school public-only analysis filter: {sum(f.facility_category.eq("SCHOOL_BASIC")&keep)} retained, {sum(~keep)} private excluded')
        f=f.loc[keep].reset_index(drop=True)
        f=gpd.GeoDataFrame(f,geometry=gpd.points_from_xy(f.longitude,f.latitude),crs=4326).to_crs(C.METRIC_CRS)
        for key,b in bounds.items():
            f[key],n=assign_zones(f,b)
            zone_diagnostics.append({'entity':f'facilities_{y}','boundary':key,'count':len(f),'unmapped':int((n==0).sum()),'ambiguous':int((n>1).sum())})
        fac[y]=f
    pd.DataFrame(zone_diagnostics).to_csv(C.RESULTS/'boundary_diagnostics.csv',index=False,encoding='utf-8-sig')
    graph,xy,network=build_network(C.PBF,C.NETWORK_BBOX);log(f'Network built: {graph.shape[0]:,} nodes')
    network['reference_audit']=validate_pbf_references(C.PBF,C.NETWORK_BBOX)
    write_json(C.RESULTS/'network_inventory.json',network)
    tree=cKDTree(xy);od,on=tree.query(np.column_stack([origins.geometry.x,origins.geometry.y]));origins['snap_m']=od;origins['node']=on
    for y,f in fac.items():
        fd,fn=tree.query(np.column_stack([f.geometry.x,f.geometry.y]));f['snap_m']=fd;f['node']=fn
    snaps=[]
    for cap in C.SNAP_CAPS_M:
        snaps.append({'kind':'origins','year':'fixed','cap_m':cap,'total':len(origins),'accepted':int((od<=cap).sum()),'accepted_population':float(origins.loc[od<=cap,'pop'].sum()),'total_population':float(origins['pop'].sum()),'max_snap_m':float(od.max())})
        for y,f in fac.items():
            for cat,g in f.groupby('facility_category'):
                snaps.append({'kind':cat,'year':y,'cap_m':cap,'total':len(g),'accepted':int((g.snap_m<=cap).sum()),'max_snap_m':float(g.snap_m.max())})
    pd.DataFrame(snaps).to_csv(C.RESULTS/'network_snap_diagnostics.csv',index=False,encoding='utf-8-sig')
    # One bounded SSSP per origin, distances to all facility points via their
    # nearest network node plus the two explicitly straight connectors.
    # Full network distance gives exact nearest within this declared graph model.
    records=[];arrs={}
    for y,f in fac.items():
        for cat in C.CATEGORIES:
            g=f[f.facility_category.eq(cat)]
            arrs[(y,cat)]=(g,g.node.to_numpy(),g.snap_m.to_numpy())
    for i,o in origins.iterrows():
        if time.monotonic()-started>C.MAX_RUNTIME_SECONDS:
            pd.DataFrame.from_records(records).to_parquet(C.RESULTS/'origin_metrics_INCOMPLETE.parquet',index=False)
            raise TimeoutError('Analysis runtime bound exceeded; partial rows explicitly marked INCOMPLETE; originals untouched')
        distances=dijkstra(graph,directed=True,indices=int(o.node)) if o.snap_m<=max(C.SNAP_CAPS_M) else None
        for (y,cat),(f,fn,fd) in arrs.items():
            for cap in C.SNAP_CAPS_M:
                ds=distances[fn]+fd+o.snap_m if distances is not None and o.snap_m<=cap else np.full(len(f),np.inf)
                ds=np.where(fd<=cap,ds,np.inf)
                for boundary,key in [('LZ_original','LZ_original'),('LD',f'LD_{y}'),('LZ_dong_sensitivity','LZ_dong_sensitivity')]:
                    internal=(f[key].to_numpy()==o[key]) & (o[key]!='')
                    for minute in C.THRESHOLDS_MIN:
                        r=metrics_for_distances(ds,internal,C.SPEED_KMH*1000/60*minute)
                        nearest_ties=np.isclose(ds,r['nearest_m'],atol=1e-6,rtol=0)&np.isfinite(ds)
                        missing_dest=f[key].to_numpy()==''
                        unknown_nir=(not r['nearest_available']) or o[key]=='' or bool((nearest_ties&missing_dest).any())
                        if unknown_nir:r['nir_upper']=1
                        r['nir_unresolved']=int(unknown_nir)
                        r['coverage_upper_origin_unknown']=int(r['covered'] or o.snap_m>cap)
                        r['internal_coverage_upper_assignment_unknown']=int(r['internal_covered'] or o.snap_m>cap or (o[key]=='' and r['covered']) or bool((missing_dest&(ds<=C.SPEED_KMH*1000/60*minute+1e-9)).any()))
                        records.append({'origin_id':o.start_gid,'pop':o['pop'],'year':y,'category':cat,'boundary':boundary,'zone':o[key] or 'UNMAPPED_OR_AMBIGUOUS','snap_cap_m':cap,'threshold_minutes':minute,'origin_network_available':int(o.snap_m<=cap),'origin_zone_available':int(o[key]!=''),**r})
        if i%250==0: log(f'Routed origins {i}/{len(origins)}; elapsed {time.monotonic()-started:.1f}s')
        if (i+1)%1000==0:pd.DataFrame.from_records(records).to_parquet(C.RESULTS/'origin_metrics_INCOMPLETE.parquet',index=False)
    rows=pd.DataFrame.from_records(records);rows.to_parquet(C.RESULTS/'origin_metrics.parquet',index=False)
    keys=['year','category','boundary','snap_cap_m','threshold_minutes']
    city=aggregate(rows,keys);city.to_csv(C.RESULTS/'city_metrics.csv',index=False,encoding='utf-8-sig')
    zones=aggregate(rows,keys+['zone']);zones.to_csv(C.RESULTS/'zone_metrics.csv',index=False,encoding='utf-8-sig')
    common=common_mapped_sensitivity(rows);common.to_csv(C.RESULTS/'common_mapped_city_metrics.csv',index=False,encoding='utf-8-sig')
    regional=regional_library_pairs(rows);regional.to_csv(C.RESULTS/'library_2025_paired_by_LZ.csv',index=False,encoding='utf-8-sig')
    change=city.pivot(index=keys[1:],columns='year',values=['covered','internal_covered','opportunities','internal_opportunities','nir_lower','nir_upper'])
    change.columns=[f'{m}_{y}' for m,y in change.columns]
    for m in ['covered','internal_covered','opportunities','internal_opportunities','nir_lower','nir_upper']:change[m+'_change_2025_minus_2020']=change[m+'_2025']-change[m+'_2020']
    change.reset_index().to_csv(C.RESULTS/'temporal_changes.csv',index=False,encoding='utf-8-sig')
    den=origins[['start_gid','pop','snap_m']+list(bounds)].copy();den.to_csv(C.RESULTS/'denominator_diagnostics.csv',index=False,encoding='utf-8-sig')
    monotonic=rows.pivot(index=['origin_id','year','category','boundary','snap_cap_m'],columns='threshold_minutes',values='internal_covered')
    checks={'population_positive':bool(origins['pop'].gt(0).all()),'common_city_denominator':bool(city.population.nunique()==1),'baseline_boundary_invariant':bool(city.groupby(['year','category','snap_cap_m','threshold_minutes']).covered.nunique().eq(1).all()),'internal_coverage_le_baseline':bool((rows.internal_covered<=rows.covered).all()),'internal_opportunity_le_baseline':bool((rows.internal_opportunities<=rows.opportunities).all()),'nir_bounds_ordered':bool((rows.nir_lower<=rows.nir_upper).all()),'threshold_monotonic':bool((monotonic[10]<=monotonic[15]).all()),'expected_origin_metric_rows':len(rows)==len(origins)*len(C.YEARS)*4*2*3*2,'no_invalid_boundary_geometry':True,'primary_inputs_unchanged':all(sha256(p)==h for p,h in baseline_hashes.items())}
    cap_monotonic=rows.pivot(index=['origin_id','year','category','boundary','threshold_minutes'],columns='snap_cap_m',values='internal_covered')
    checks.update({'unit_tests_11_passed':unit_count==11,'pbf_relevant_references_complete':network['reference_audit']['missing_references']==0,'snap_cap_monotonic':bool((cap_monotonic[100]<=cap_monotonic[200]).all()),'matched_cohort_common_denominator':bool(common.groupby(['year','category','snap_cap_m','threshold_minutes']).population.nunique().eq(1).all()),'regional_same_origin_population_preserved':float(regional.population.sum())==float(origins['pop'].sum())})
    write_json(C.RESULTS/'qa_checks.json',checks)
    assert all(checks.values()),checks
    (C.RESULTS/'origin_metrics_INCOMPLETE.parquet').unlink(missing_ok=True)
    for p in [C.ORIGINS,C.GRID,C.PBF,C.CORE/'seoul_boundaries_all.gpkg',*C.OFFICIAL.parent.glob(C.OFFICIAL.stem+'.*')]:inputs.add(p)
    manifest=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(inputs)]
    write_json(C.RESULTS/'input_manifest.json',manifest)
    import scipy,shapely,pyproj,google.protobuf
    write_json(C.RESULTS/'runtime.json',{'python':sys.version,'pandas':pd.__version__,'geopandas':gpd.__version__,'scipy':scipy.__version__,'shapely':shapely.__version__,'pyproj':pyproj.__version__,'protobuf':google.protobuf.__version__,'elapsed_seconds':time.monotonic()-started,'origin_count':len(origins),'population':float(origins['pop'].sum()),'origin_output_rows':len(rows),'scenario':'fixed population reference with unverified year; fixed OSM network; facility snapshots as supplied'})
    figures(city)
    write_report()
    (C.RESULTS/'execution_notes.txt').write_text('Full pipeline executed from run_analysis.py, including deterministic unit tests, provenance, network reference audit, routing, cohort/regional summaries, report and manifests. Original inputs were read only.\n',encoding='utf-8')
    finalize_manifests()
    log('Complete: all deterministic output invariants passed')

def figures(city):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'LZ_original':'#1565c0','LD':'#d16c20'}
    fig,axes=plt.subplots(1,2,figsize=(12,4),sharey=True)
    for ax,y in zip(axes,C.YEARS):
        for j,b in enumerate(colors):
            g=city[(city.year==y)&(city.boundary==b)&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('category').reindex(C.CATEGORIES)
            ax.bar(np.arange(4)+(j-.5)*.32,g.internal_covered*100,width=.32,label=b,color=colors[b])
        base=city[(city.year==y)&(city.boundary=='LZ_original')&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('category').reindex(C.CATEGORIES)
        ax.plot(np.arange(4),base.covered*100,'ko',label='Unrestricted baseline');ax.set_xticks(range(4),['Retail','Clinic','School','Library']);ax.set_title(f'{y}-labelled facility input');ax.set_ylim(0,105);ax.set_ylabel('Population coverage (%)')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,bbox_to_anchor=(.5,.01),fontsize=8)
    fig.suptitle('15-minute fixed-network scenario; 100 m connector cap');fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(C.RESULTS/'coverage_comparison.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for y,marker in [(2020,'o'),(2025,'s')]:
        for b in colors:
            g=city[(city.year==y)&(city.boundary==b)&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('category').reindex(C.CATEGORIES)
            ax.plot(range(4),g.coverage_penalty*100,marker=marker,label=f'{y} {b}',color=colors[b],linestyle='-' if y==2025 else '--')
    ax.set_xticks(range(4),['Retail','Clinic','School','Library']);ax.set_ylabel('Baseline minus internal coverage (percentage points)');ax.set_title('Endpoint boundary constraint penalty (not path containment)');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(C.RESULTS/'boundary_penalty.png',dpi=180);plt.close(fig)

def write_report():
    """Derive every numerical report table from saved machine-readable results."""
    city=pd.read_csv(C.RESULTS/'city_metrics.csv')
    runtime=json.loads((C.RESULTS/'runtime.json').read_text('utf-8'))
    network=json.loads((C.RESULTS/'network_inventory.json').read_text('utf-8'))
    qa=json.loads((C.RESULTS/'qa_checks.json').read_text('utf-8'))
    bd=pd.read_csv(C.RESULTS/'boundary_diagnostics.csv')
    snaps=pd.read_csv(C.RESULTS/'network_snap_diagnostics.csv')
    labels=dict(zip(C.CATEGORIES,['일상 소매','1차 의료','국·공립 초중고','공공 도서관']))
    lines=['# 서울4종 시설 접근성: 실제 계산 결과','',
      '**실제 OSM 보행망을 이용해 두 시설스냅샷과 공식 LZ/연도별 LD를 새로 계산했다.** 아래 수치는 고정 참조인구·고정 보행망·연결가정에 대한 결과다. 서울연구원 특정 연구의 동일 재현 또는 실제 두 시점의 주민 접근성 변화로 확정하지 않는다.','',
      '**먼저 자료시점의 한계:** 이하2020/2025는 제공 파일의 연도 표기다. 특히2020 소매는2019 표시 보존본의 대구 ZIP 안에 서울 CSV가 있고,26,494개 중21,570개 ID에2022 문자열이 있다. 상위 접두사 MA010120241도3,861개다. 이를 개업연도로 단정하지는 않는다. 별도 검증으로2026-09-23 공공데이터포털 현행 공식 다운로드와 로컬 ZIP의293,466,529byte·SHA256 동일성은 확인했다. 다만 이 파일이2019 당시 내용을 정확히 나타내는지와 ID시점 의미는 아직 미확정이다. 공식 현행파일·보존 원천행의 일치가 과거시점 유효성을 입증하지 않으므로 아래를 실제2020→2025 변화로 인용하면 안 된다.','',
      f'- 수요:250m셀 중심점 {runtime["origin_count"]:,}개, 고정 인구합 **{runtime["population"]:,.0f}명**. 인구 기준연도는 미확인.',
      f'- 네트워크:OSM **{network["replication_date_utc"]}**, {network["nodes"]:,}노드·{network["directed_edges"]:,}방향선분. 두 시점 공통.',
      '- 시설:소매26,494→29,063, 의료17,058→18,604, 국·공립학교960→963, 도서관180→212. 원본학교의 사립348/347개는 제외.',
      '- 주가정:4km/h, 도보10/15분, 양끝 최근접노드 직선연결 각각100m이내. 200m상한은 민감도.',
      f'- 저장 출발점 결과 {runtime["origin_output_rows"]:,}행. 자동검증조건 {sum(qa.values())}/{len(qa)} 통과. 주계산시간 {runtime["elapsed_seconds"]/60:.1f}분(후속 감사·그림 확인 시간 제외).','',
      '## 15분 주분석:확인된 서비스 인구 비율','',
      '공통 도시분모를 사용한다. 미스냅 출발점·미배정 경계를 확인된 도달/내부서비스에 넣지 않았으며 이는 실제 미서비스 확정이 아니다. 범위와 부분상한은 아래에 별도 제시한다.','',
      '|시설시점|시설|무제한 Coverage(%)|공식LZ 내부(%)|LD 내부(%)|LD−LZ(%p)|',
      '|---|---|---:|---:|---:|---:|']
    for y in C.YEARS:
        for cat in C.CATEGORIES:
            g=city[(city.year==y)&(city.category==cat)&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('boundary');a=g.loc['LZ_original'];b=g.loc['LD']
            lines.append(f'|{y}|{labels[cat]}|{a.covered*100:.3f}|{a.internal_covered*100:.3f}|{b.internal_covered*100:.3f}|{(b.internal_covered-a.internal_covered)*100:+.3f}|')
    lines+=['','## 10분 주분석: 확인된 서비스 인구 비율','','|시설시점|시설|무제한 Coverage(%)|공식 LZ 내부(%)|LD 내부(%)|LD−LZ(%p)|','|---|---|---:|---:|---:|---:|']
    for y in C.YEARS:
        for cat in C.CATEGORIES:
            g=city[(city.year==y)&(city.category==cat)&(city.snap_cap_m==100)&(city.threshold_minutes==10)].set_index('boundary');a=g.loc['LZ_original'];b=g.loc['LD']
            lines.append(f'|{y}|{labels[cat]}|{a.covered*100:.3f}|{a.internal_covered*100:.3f}|{b.internal_covered*100:.3f}|{(b.internal_covered-a.internal_covered)*100:+.3f}|')
    lines+=['','## 15분 누적기회와 최근린 끝점 내부성','',
      '기회는 인구가중 시설개수이며 서비스 수용량이 아니다. NIR은 최근린 시설의 끝점 내부성으로, 최소도달시간과 다른 값이다. 동률·미확정 위치/경로를 하한~상한에 반영했다.','',
      '|시점|시설|무제한 기회|LZ내부 기회|LD내부 기회|LZ NIR(%)|LD NIR(%)|',
      '|---|---|---:|---:|---:|---:|---:|']
    for y in C.YEARS:
        for cat in C.CATEGORIES:
            g=city[(city.year==y)&(city.category==cat)&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('boundary');a=g.loc['LZ_original'];b=g.loc['LD']
            lines.append(f'|{y}|{labels[cat]}|{a.opportunities:.2f}|{a.internal_opportunities:.2f}|{b.internal_opportunities:.2f}|{a.nir_lower*100:.2f}~{a.nir_upper*100:.2f}|{b.nir_lower*100:.2f}~{b.nir_upper*100:.2f}|')
    lines+=['','## 최근린 조건부 평균시간','','15분 밖의 가장 가까운 시설도 포함한다. 아래 시간의 분모는 각 경계·시설별 유한경로 인구(`*_eligible_population`)이며 도시 전체 인구분모의 Coverage와 직접 같지 않다.','','|시점|시설|무제한(분)|LZ 내부(분)|LD 내부(분)|','|---|---|---:|---:|---:|']
    for y in C.YEARS:
        for cat in C.CATEGORIES:
            g=city[(city.year==y)&(city.category==cat)&(city.snap_cap_m==100)&(city.threshold_minutes==15)].set_index('boundary');a=g.loc['LZ_original'];b=g.loc['LD']
            lines.append(f'|{y}|{labels[cat]}|{a.nearest_m_conditional_mean_minutes:.2f}|{a.internal_nearest_m_conditional_mean_minutes:.2f}|{b.internal_nearest_m_conditional_mean_minutes:.2f}|')
    lines+=['','## 연결 및 경계 미확정 범위','',
      '|연결상한|수요점 연결수|연결 인구|전체분모 대비(%)|','|---|---:|---:|---:|']
    for _,r in snaps[snaps.kind.eq('origins')].iterrows():
        lines.append(f'|{r.cap_m:.0f}m|{r.accepted:,.0f}|{r.accepted_population:,.0f}|{r.accepted_population/r.total_population*100:.4f}|')
    lines+=['','|경계|미배정 출발점|모호배정 출발점|미배정 인구|모호배정 인구|','|---|---:|---:|---:|---:|']
    for _,r in bd[bd.entity.eq('origins')].iterrows():lines.append(f'|{r.boundary}|{r.unmapped}|{r.ambiguous}|{r.unmapped_population:,.0f}|{r.ambiguous_population:,.0f}|')
    lines+=['','`city_metrics.csv`의 `origin_network_available`, `origin_zone_available`, `nearest_available`, `nir_unresolved`가 각각 확인 가능한 비율을 공개한다. `coverage_upper_origin_unknown`은 미스냅 출발인구를 모두 도달 가능으로 처리한 부분상한, `internal_coverage_upper_assignment_unknown`은 미배정 경계의 잠재내부도달을 더한 부분상한이다. 버려진 시설/누락망/도외시설까지 포함하는 현실 전체상한은100%이며 이 부분상한을 통계적 신뢰구간으로 사용하지 않는다.','',
      '경계 미배정 차이에 대한 별도 민감도로, 같은 연결상한에서 원점이 LZ·해당연도 LD에 모두 유일하게 배정되고 보행망에 연결된 **동일 출발점 교집합**을 비교한 `common_mapped_city_metrics.csv`도 제공한다. 이 표는 줄어든 인구분모를 공개하며 주분석의 도시 전체분모를 대신하지 않는다. 목적지 미배정까지 해소한 표는 아니다.','',
      '## 민감도·시계열 해석','',
      '|시점|시설|100→200m LZ내부 변화(%p)|100→200m LD내부 변화(%p)|원본→동재구성 LZ 변화(%p)|','|---|---|---:|---:|---:|']
    for y in C.YEARS:
        for cat in C.CATEGORIES:
            g=city[(city.year==y)&(city.category==cat)&(city.threshold_minutes==15)].set_index(['boundary','snap_cap_m'])
            da=g.loc[('LZ_original',200),'internal_covered']-g.loc[('LZ_original',100),'internal_covered'];db=g.loc[('LD',200),'internal_covered']-g.loc[('LD',100),'internal_covered'];dc=g.loc[('LZ_dong_sensitivity',100),'internal_covered']-g.loc[('LZ_original',100),'internal_covered']
            lines.append(f'|{y}|{labels[cat]}|{da*100:+.3f}|{db*100:+.3f}|{dc*100:+.3f}|')
    lines+=['','경계별 차이는 시설유형마다 읽어야 하며 LD의 일반적 우월성을 의미하지 않는다. LD의2020→2025 차이는 시설과 경계가 동시에 바뀐 결과로 시설증가의 단독효과가 아니다. 최근린 조건부시간·10분 결과·116개 구획 결과·시계열 차이는 원자료표에 모두 남겨 두었다.','',
      '## 지역 진단 예:2025 표기 도서관의 LZ 내부 Coverage 하위 구획','',
      '원본 LZ 기준 내부15분 Coverage가 낮은5개 구획이다(동률이면 인구가 큰 순). LD열은 **그 LZ에 속한 동일 출발점 인구**에서 각 출발점의 LD 내부 목적지를 계산한 값이다. LZ·LD 구획명을 대응시킨 비교가 아니며 작은 인구분모와 미배정 영향을 함께 읽어야 한다.','',
      '|원본 LZ|인구분모(명)|출발점 수|무제한(%)|LZ 내부(%)|동일 원점 LD 내부(%)|','|---|---:|---:|---:|---:|---:|']
    regional=pd.read_csv(C.RESULTS/'library_2025_paired_by_LZ.csv')
    for _,r in regional.loc[regional.LZ_original_zone.ne('UNMAPPED_OR_AMBIGUOUS')].head(5).iterrows():
        lines.append(f'|{r.LZ_original_zone}|{r.population:,.0f}|{r.origins:.0f}|{r.covered*100:.3f}|{r.LZ_internal_covered*100:.3f}|{r.LD_internal_covered_same_origins*100:.3f}|')
    lines+=['',
      '## 원천 감사와 연구 활용 범위','',
      '- 총94,229행 CSV/Parquet의 모든 문자열이 같고 좌표 표현차는 최대1.42×10⁻¹⁴도다. 모두 서울 실제 자치구 폴리곤 엄격한 내부에 위치했다.',
      '- 소매55,557행의 원천ZIP 서울CSV에서 ID·명칭·주소·분류·좌표 전수일치. 날짜가 붙은 보존본과의 일치이며 과거주소/영업시점의 외부 독립인증은 아니다.',
      '- 소매 두 보존 ZIP 모두2026-09-23 공식 포털 현행 다운로드와byte수·SHA256 전부일치:2020표기293,466,529byte,2025표기331,029,189byte. HTTP/응답파일명/해시는`external_source_verification.json`에 보존했다. 현행 공식파일의 출처 인증과 역사내용의 시점 인증을 구분한다.',
      '- 의료35,662행의 원천ID·명칭·업종·기준일 조건 일치. 원천TM좌표34,839행, 보존 지오코딩 명부 대조823행으로 나뉜다. 전자는 원좌표 일치, 후자는 명부의 이름·주소·유형·최종좌표 일치이며 API·현장 정확성 인증은 아니다.',
      '- 학교2,618행·도서관392행 명부 이름/주소 전수일치. 학교의2019/2024년10월 명부와2026 좌표카탈로그를 구분했다. 과거이전·개폐교·동명이칭과 정확한 기준일 위치는 전수확인하지 않았다.',
      '- 공공학교도 전인구 가중 공간접근성으로 학령인구·학군·입학자격·정원을 반영하지 않는다. 의료 진료과/수용력과 도서관 규모/운영시간도 미반영이다.',
      '- 목적지 끝점만 내부로 제한하며 최단경로의 생활권 경계 통과를 허용한다. 경로 전체 내부성으로 해석하면 안 된다.',
      '- 도로보도·횡단·사유지 출입구·고도·시간조건은 현장확인하지 않았다. 최근접노드 직선연결 가정과스냅제외가 있으므로 결과는 조건부망 시나리오다.',
      '- 분석에 필요한 실제 계산·분모·원천행 계보가 확보된 상태다. 이 사실이 논문심사 통과·인과결론·완전한 역사복원을 뜻하지 않는다.','',
      '## 재현 산출물','',
      '[재실행 명령/파일 안내](README.md), [수식·방법·1차문헌](METHODS.md), [도시결과](results/city_metrics.csv), [구획결과](results/zone_metrics.csv), [감사표](results/facility_provenance.csv), [입력해시](results/input_manifest.json), [검증](results/qa_checks.json).','',
      '![15분 Coverage](results/coverage_comparison.png)','',
      '![경계 제한 손실](results/boundary_penalty.png)','']
    (C.HERE/'ANALYSIS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    main()
