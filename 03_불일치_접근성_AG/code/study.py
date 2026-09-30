"""AG v3 seven-category boundary-path study; read-only released inputs.
Run: python -B study.py --repository-root <research-root> --year 2020
No shared module is imported; all products are written below --output-root.
"""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import pyarrow.parquet as pq

CATS = ['교육','보육·복지','의료','문화','행정·안전','소매','생활서비스']
TYPES = {'교육':['유치원','학교','청소년수련시설'], '보육·복지':['어린이집','노인 이용시설','장애인 이용시설','가족센터(자치구 본소)'], '의료':['의원','약국','병원급','보건소·보건지소','응급의료기관','산후조리원'], '문화':['공공도서관','문화기반시설','등록공연장'], '행정·안전':['주민센터','소방서·119안전센터'], '소매':['일상소매','식료품소매(즉석판매·제과)','대규모점포(주요4업태)'], '생활서비스':['일반음식점','휴게음식점','미용업','이용업','세탁업','목욕장업']}
FAC_SHA='c0857567127210d823bb57cea01799f2cc46917ab636be84ab441556f97158cb'
CFG={'release':'AG-v3-7cat-20260929','size_tol':.20,'pp_factor':.95,'threshold_sec':900,'walk_kmh':4.,'grid_m':100,'random_paths':100,'random_seed':20261301,'gain_tolerance':1e-15,'years':[2020,2025], 'OD':'od-daily-v1; arrival 09-20 inclusive; HW/WH excluded; all days of week including weekends; masked=0; both endpoints 424; self included', 'MAI':'mean of category conditional means; paired delta on common valid categories','PP_precision':'shared boundary length from supplied geometry; adjacency CSV rounded lengths are not used'}

def verify_design(root):
    package=Path(__file__).resolve().parents[1]
    contract=json.loads((package/'design_contract.json').read_text('utf-8'))
    assert contract['version']=='AG-v3-7cat-design-20260929'
    assert sha(package/'design.md')==contract['design_sha256'],'Study design changed'
    common=package/contract['common_snapshot']
    assert '공통설계 상태: 적용완료' in common.read_text('utf-8-sig')
    assert sha(common)==contract['common_sha256'],'Common applied design changed'
    definition=package/contract['indicator_definition_snapshot']
    assert sha(definition)==contract['indicator_definition_sha256'],'Indicator definition changed'
    assert len(CATS)==7 and sum(map(len,TYPES.values()))==27
    return contract

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def js(p,obj):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')

def csv(p,rows): pd.DataFrame(rows).to_csv(p,index=False,encoding='utf-8-sig',float_format='%.12g',lineterminator='\n')

def input_paths(root,year):
    a=root/'06_접근성분석/접근성분석_패키지'; d=a/'데이터/입력'; c=root/'00_공통_코어엔진/data'
    return dict(geometry=c/'seoul_boundaries_all.gpkg', mapping=c/'dong_to_official_livingzone_mapping_424.csv', adjacency=d/'boundary/dong424_queen_adjacency.csv', grid=d/'grid/grid100_master.parquet', facility=root/'시설데이터 구축/시설데이터_패키지/데이터/서울시설_2020_2025_분석용.parquet', units=d/'facility/facility_2020_2025_units.parquet', source=d/'facility/facility_2020_2025_units.source.json', od=c/f'od/od_daily_{year}01.parquet', comparison=a/f'데이터/결과/main/unit_access_{year}_100.csv', ttm=d/f'ttm/ttm100_{year}', access_manifest=a/'데이터/manifest_sha256.csv', provenance=a/'데이터/release_provenance.json')

def lock_inputs(root,paths):
    files=[(k,p) for k,p in paths.items() if k!='ttm']+ [('ttm',p) for p in sorted(paths['ttm'].glob('ku=*/*.parquet'))]
    return [{'role':k,'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for k,p in files]

def load(root,year,paths):
    geom=gpd.read_file(paths['geometry'],layer='dong_424')[['Dong','geometry']].sort_values('Dong').reset_index(drop=True)
    assert len(geom)==424 and geom.Dong.is_unique and geom.crs.to_epsg()==5179
    z=pd.read_csv(paths['mapping']).sort_values('Dong').reset_index(drop=True)
    assert z.Dong.is_unique and np.array_equal(z.Dong,geom.Dong) and z.life_zone_id.nunique()==116
    assert z[['Dong','Ku','life_zone_id']].notna().all().all() and z.groupby('life_zone_id').Ku.nunique().max()==1
    gm=pd.read_parquet(paths['grid']); assert gm.grid_cd.is_unique and len(gm)==60528
    di={int(d):i for i,d in enumerate(z.Dong)}; gd=gm.dong424.map(di)
    assert gd.notna().all() and gm[['pop_2019','pop_2024']].notna().all().all()
    pop=gm[f'pop_{2019 if year==2020 else 2024}'].to_numpy(float); assert (pop>=0).all()
    ku=z.Ku.to_numpy(); lz=z.life_zone_id.to_numpy(np.int64); gd=gd.to_numpy(np.int64)
    assert np.array_equal(lz[gd],gm.lz116.to_numpy())
    adj=pd.read_csv(paths['adjacency']); assert not adj.duplicated(['i','j']).any()
    G=nx.Graph(); G.add_nodes_from(range(424)); S=np.zeros((424,424))
    for a,b,v in adj[['i','j','shared_len_m']].itertuples(index=False,name=None):
        assert a in di and b in di and v>=0
        i,j=di[a],di[b]
        if ku[i]==ku[j]:
            assert geom.geometry.iloc[i].touches(geom.geometry.iloc[j])
            G.add_edge(i,j)
            S[i,j]=geom.geometry.iloc[i].boundary.intersection(geom.geometry.iloc[j].boundary).length
    assert np.allclose(S,S.T,atol=1e-8)
    od=pd.read_parquet(paths['od']); assert not od.duplicated(['dong_O','dong_D']).any()
    assert od[['dong_O','dong_D','flow']].notna().all().all() and (od.flow>=0).all()
    assert set(od.dong_O)|set(od.dong_D)<=set(di)
    F=np.zeros((424,424)); np.add.at(F,(od.dong_O.map(di),od.dong_D.map(di)),od.flow)
    return dict(year=year,gm=gm,pop=pop,gd=gd,z=z,dongs=z.Dong.to_numpy(),di=di,nD=424,ku=ku,kus=np.unique(ku),LZ=lz,popd=np.bincount(gd,weights=pop,minlength=424),G=G,S=S,area=geom.area.to_numpy(),per=geom.length.to_numpy(),geom=geom,F=F,FT=F.sum(),Ws=F+F.T)

def pp(D,members):
    s=np.asarray(members); per=D['per'][s].sum()-D['S'][np.ix_(s,s)].sum()
    return 4*np.pi*D['area'][s].sum()/per**2

def qscore(W,lab):
    deg=W.sum(1)+np.diag(W); twice=deg.sum()
    return sum((W[np.ix_(lab==z,lab==z)].sum()+np.diag(W)[lab==z].sum())/twice-(deg[lab==z].sum()/twice)**2 for z in np.unique(lab))

def ifr(D,lab): return float(D['F'][lab[:,None]==lab[None,:]].sum()/D['FT'])

def comp(lab): return tuple(sorted(tuple(np.flatnonzero(lab==c)) for c in np.unique(lab)))
def chash(lab): return hashlib.sha256(repr(comp(lab)).encode()).hexdigest()

class Constraints:
    def __init__(self,D):
        self.D=D; self.nodes={int(k):np.flatnonzero(D['ku']==k) for k in D['kus']}; self.refs={}; self.pps={}
        for k,n in self.nodes.items():
            zones=np.unique(D['LZ'][n]); self.refs[k]=np.sort([D['popd'][n][D['LZ'][n]==z].sum() for z in zones]); self.pps[k]=np.mean([pp(D,n[D['LZ'][n]==z]) for z in zones])*.95
    def pops_ok(self,k,pops):
        p=np.sort(pops); return len(p)==len(self.refs[k]) and bool(np.all(p>0) and np.all(np.abs(p/self.refs[k]-1)<=.2))
    def check(self,lab,k):
        D=self.D; n=self.nodes[k]; zs=np.unique(lab[n]); members=[n[lab[n]==z] for z in zs]
        return self.pops_ok(k,[D['popd'][x].sum() for x in members]) and np.mean([pp(D,x) for x in members])>=self.pps[k] and all(nx.is_connected(D['G'].subgraph(x)) and set(np.flatnonzero(lab==z))==set(x) for x,z in zip(members,zs))

def legal(D,C,lab,k,exclude=None):
    nodes=C.nodes[int(k)]; zs=np.unique(lab[nodes]); out=[]
    zp={z:D['popd'][nodes[lab[nodes]==z]].sum() for z in zs}; zpp={z:pp(D,nodes[lab[nodes]==z]) for z in zs}
    for v in nodes:
        if exclude is not None and exclude[v]: continue
        a=lab[v]
        for b in sorted({lab[u] for u in D['G'][v] if lab[u]!=a}):
            na=nodes[(lab[nodes]==a)&(nodes!=v)]
            if not len(na) or not nx.is_connected(D['G'].subgraph(na)): continue
            pops=[zp[c] for c in zs if c not in (a,b)]+[zp[a]-D['popd'][v],zp[b]+D['popd'][v]]
            if not C.pops_ok(k,pops): continue
            nb=np.append(nodes[lab[nodes]==b],v)
            pps=[zpp[c] for c in zs if c not in (a,b)]+[pp(D,na),pp(D,nb)]
            if np.mean(pps)>=C.pps[k]: out.append((int(v),int(a),int(b)))
    return out

def make_paths(D,out):
    C=Constraints(D); lz=D['LZ']; assert all(C.check(lz,k) for k in D['kus'])
    Ws={}
    for k,n in C.nodes.items():
        f=D['F'][np.ix_(n,n)]; w=f+f.T; np.fill_diagonal(w,np.diag(f)); Ws[k]=w
    queues={}; moves=[]; ver=[]
    for k,n in C.nodes.items():
        lab=lz.copy(); queue=[]
        while True:
            q0=qscore(Ws[k],lab[n]); best=(1e-15,None)
            for v,a,b in legal(D,C,lab,k):
                l2=lab.copy(); l2[v]=b; gain=qscore(Ws[k],l2[n])-q0
                if gain>best[0]: best=(gain,(v,a,b))
            if best[1] is None: break
            v,a,b=best[1]; lab[v]=b; assert C.check(lab,k)
            queue.append(dict(ku=k,v=v,dong=int(D['dongs'][v]),from_z=a,to_z=b,dQ=best[0],gu_step=len(queue)+1))
        queues[k]=queue
    seq=[]
    while any(queues.values()):
        k=max((k for k in queues if queues[k]),key=lambda k:queues[k][0]['dQ']); seq.append(queues[k].pop(0))
    states=[]; labels=[]; moved_masks=[]; affs=[]
    def record(strategy,path,t,k,lab,moved,aff):
        states.append(dict(key=f'{strategy}|{path}|{t}',strategy=strategy,path=path,t=t,k=k,n_unique=int(moved.sum()),composition_hash=chash(lab)))
        labels.append(lab.copy()); moved_masks.append(moved.copy()); affs.append(sorted(aff))
    record('LZ',0,0,0,lz,np.zeros(424,bool),set())
    lab=lz.copy(); moved=np.zeros(424,bool); aff=set()
    for t,r in enumerate(seq,1):
        k,v,b=r['ku'],r['v'],r['to_z']; n=C.nodes[k]
        assert lab[v]==r['from_z'] and (v,int(lab[v]),b) in legal(D,C,lab,k)
        q0=qscore(Ws[k],lab[n]); aff|={int(lab[v]),b}; lab[v]=b; moved[v]=True
        err=abs(qscore(Ws[k],lab[n])-q0-r['dQ']); assert err<1e-12 and C.check(lab,k)
        ver.append(dict(order=t,from_legal_constraints=True,dQ_absdiff=err)); moves.append(dict(strategy='MOD',path=0,t=t,**r)); record('MOD',0,t,t,lab,moved,aff)
    print(f"{D['year']} MOD {len(seq)} moves; replay passed",flush=True)
    lab=lz.copy(); moved=np.zeros(424,bool); aff=set(); ki=0
    while True:
        best=(1e-15,None)
        for k in D['kus']:
            for v,a,b in legal(D,C,lab,k,moved):
                gain=(D['Ws'][v,lab==b].sum()-D['Ws'][v,(lab==a)&(np.arange(424)!=v)].sum())/D['FT']
                if gain>best[0]: best=(gain,(v,a,b,int(k)))
        if best[1] is None: break
        v,a,b,k=best[1]; oldifr=ifr(D,lab); aff|={a,b}; lab[v]=b; moved[v]=True; ki+=1
        assert C.check(lab,k) and abs(ifr(D,lab)-oldifr-best[0])<1e-12
        moves.append(dict(strategy='IFR',path=0,t=ki,ku=k,v=v,dong=int(D['dongs'][v]),from_z=a,to_z=b,dIFR=best[0])); record('IFR',0,ki,ki,lab,moved,aff)
    print(f"{D['year']} IFR {ki} moves",flush=True)
    rng=np.random.default_rng(CFG['random_seed']); noops=0
    for path in range(CFG['random_paths']):
        lab=lz.copy(); moved=np.zeros(424,bool); aff=set(); kr=0
        for t,r in enumerate(seq,1):
            k=r['ku']; lm=legal(D,C,lab,k,moved)
            if lm:
                v,a,b=lm[int(rng.integers(len(lm)))]; aff|={a,b}; lab[v]=b; moved[v]=True; kr+=1; assert C.check(lab,k)
                moves.append(dict(strategy='RAND',path=path,t=t,ku=k,v=v,dong=int(D['dongs'][v]),from_z=a,to_z=b))
            else: noops+=1
            record('RAND',path,t,kr,lab,moved,aff)
    csv(out/'moves.csv',moves); csv(out/'path_replay.csv',ver)
    np.savez_compressed(out/'path_labels.npz',labels=np.array(labels),moved=np.array(moved_masks),keys=np.array([s['key'] for s in states]),dongs=D['dongs'])
    js(out/'path_affected_zones.json',affs)
    # independent weighted undirected modularity, including self loops
    maxq=0.; maxpp=0.
    for si in [0,len(seq)]:
        lab=labels[si]
        for k,n in C.nodes.items():
            G=nx.from_numpy_array(Ws[k]); groups=[set(np.flatnonzero(lab[n]==z)) for z in np.unique(lab[n])]
            maxq=max(maxq,abs(nx.algorithms.community.modularity(G,groups,weight='weight')-qscore(Ws[k],lab[n])))
        for z in np.unique(lab):
            ids=np.flatnonzero(lab==z); geom=D['geom'].iloc[ids].geometry.union_all(); p=4*np.pi*geom.area/geom.length**2
            maxpp=max(maxpp,abs(p-pp(D,ids)))
    assert maxq<1e-12 and maxpp<1e-8
    return states,labels,moved_masks,affs,dict(K_mod=len(seq),K_ifr=ki,noops=noops,modularity_networkx_max_error=maxq,pp_geometry_max_error=maxpp)

class Accessibility:
    def __init__(self,D,paths,out):
        self.D=D; gm=D['gm']; self.pos=np.flatnonzero(D['pop']>0); self.p=D['pop'][self.pos]; self.gd=D['gd'][self.pos]
        self.ng=len(gm); self.n=len(self.pos); mapper=np.full(self.ng,-1,int); mapper[self.pos]=np.arange(self.n)
        f=pd.read_parquet(paths['units'],columns=['year','시설','분석가능','role','cat_A','grid100_cd'])
        assert len(f)==584766 and '체육시설업' not in set(f['시설'])
        f=f[(f.year==D['year'])&f['분석가능'].astype(bool)&f['role'].ne('control')&f.cat_A.isin(CATS)].copy()
        assert set(f['시설'])=={v for vv in TYPES.values() for v in vv}
        expected={t:c for c,ts in TYPES.items() for t in ts}; assert f['시설'].map(expected).eq(f.cat_A).all()
        code=pd.Series(np.arange(self.ng),index=gm.grid_cd); gi=f.grid100_cd.map(code)
        self.info={'facility_selected_rows':len(f),'facility_outside_grid_rows':int(gi.isna().sum()),'facility_types':f['시설'].nunique(),'categories':7,'population':self.p.sum(),'positive_origins':self.n,'grid_rows':self.ng}
        mask=np.zeros(self.ng,np.uint8)
        ok=gi.notna(); np.bitwise_or.at(mask,gi[ok].to_numpy(int),np.left_shift(1,f.loc[ok,'cat_A'].map({c:i for i,c in enumerate(CATS)}).to_numpy()).astype(np.uint8))
        self.mask=mask; counts=np.array([int(x).bit_count() for x in mask],np.uint8)
        self.info['facility_cells']=int((mask>0).sum()); self.info['facility_cells_by_category']={c:int(((mask>>j)&1).sum()) for j,c in enumerate(CATS)}
        es=[]; sample_o=[]; sample_d=[]; chosen=set(np.linspace(0,self.n-1,60,dtype=int).tolist()); ttmrows=0; filtered=0; dup=0
        for pth in sorted(paths['ttm'].glob('ku=*/*.parquet')):
            x=pq.read_table(pth,columns=['o_grid','d_grid','t_sec']).to_pandas(); ttmrows+=len(x)
            assert x[['o_grid','d_grid','t_sec']].notna().all().all() and (x.t_sec>=0).all()
            o=x.o_grid.map(code); d=x.d_grid.map(code); assert o.notna().all() and d.notna().all()
            o=o.to_numpy(int); d=d.to_numpy(int); sel=(x.t_sec.to_numpy()<=900)&(D['pop'][o]>0)&(mask[d]>0)
            o=mapper[o[sel]]; d=d[sel]; filtered+=len(o)
            # uniqueness within stored partition; no effect on binary max if duplicate
            dup+=len(o)-len(np.unique(o.astype(np.int64)*self.ng+d))
            if not len(o): continue
            sam=np.isin(o,list(chosen)); sample_o.extend(o[sam]); sample_d.extend(d[sam])
            pairs=o.astype(np.int64)*424+D['gd'][d]; ids,inv=np.unique(pairs,return_inverse=True)
            vals=np.zeros((len(ids),7),np.uint8)
            for j in range(7): np.maximum.at(vals[:,j],inv,np.where((mask[d]>>j)&1,counts[d],0))
            es.append((ids,vals))
        ids=np.concatenate([x[0] for x in es]); vals=np.concatenate([x[1] for x in es]); keys,inv=np.unique(ids,return_inverse=True)
        em=np.zeros((len(keys),7),np.uint8)
        for j in range(7): np.maximum.at(em[:,j],inv,vals[:,j])
        self.eo=keys//424; self.ed=keys%424; self.em=em; self.sample_o=np.array(sample_o,int); self.sample_d=np.array(sample_d,int); self.counts=counts
        self.info.update(ttm_stored_rows=ttmrows,usable_pairs=filtered,duplicates_within_partition=dup,compressed_origin_destination_dong_pairs=len(keys))
        assert dup==0
        self.none=self.matrix(None); self.rn=self.none>0; self.base=self.matrix(D['LZ']); self.x0=(self.rn&~(self.base>0)).any(1)
        # Derived, non-identifying aggregate evaluation inputs, not copied to collaborator package.
        np.savez_compressed(out/'evaluation_cells.npz',grid_cd=gm.grid_cd.to_numpy(str)[self.pos],population=self.p,dong=D['dongs'][self.gd],no_boundary_category_mask=np.sum(self.rn*(1<<np.arange(7)),axis=1).astype(np.uint8),LZ_omission=self.x0)
        self.validation=[]
        for name,lab in [('none',None),('LZ',D['LZ'])]:
            mat=self.none if lab is None else self.base
            for o in chosen:
                ds=self.sample_d[self.sample_o==o]
                if lab is not None: ds=ds[lab[D['gd'][ds]]==lab[self.gd[o]]]
                direct=np.array([max([int(counts[d]) for d in ds if (int(mask[d])>>j)&1],default=0) for j in range(7)])
                assert np.array_equal(direct,mat[o])
            self.validation.append({'check':'raw_pairs_vs_compressed','plan':name,'origins':len(chosen),'equal':True})
        shared=pd.read_csv(paths['comparison']); differences=[]
        for name,mat in [('none',self.none),('lz116',self.base)]:
            sub=shared[(shared.unit_level=='seoul')&(shared.b==name)]
            assert len(sub)==8, (name,shared.b.unique())
            res=self.metrics(mat)
            for j,c in enumerate(CATS+['종합']):
                row=sub[sub.cat==c].iloc[0]; cov=res['cov'][j] if j<7 else res['COV15']; mai=res['mai'][j] if j<7 else res['MAI15']
                differences.extend([abs(cov-row.COV),abs(mai-row.MAI)])
        assert max(differences)<5.1e-7
        self.validation.append({'check':'independent_seoul_COV_MAI_vs_shared_rounded_output','values':len(differences),'max_abs_error':max(differences),'tolerance':5.1e-7})

    def matrix(self,lab):
        mat=np.zeros((self.n,7),np.uint8)
        ok=np.ones(len(self.eo),bool) if lab is None else lab[self.gd[self.eo]]==lab[self.ed]
        for j in range(7): np.maximum.at(mat[:,j],self.eo[ok],self.em[ok,j])
        return mat

    def metrics(self,mat):
        r=mat>0; reach=(self.p[:,None]*r).sum(0); num=(self.p[:,None]*mat).sum(0); cov=reach/self.p.sum()
        mai=np.divide(num,reach,out=np.full(7,np.nan),where=reach>0)
        return dict(cov=cov,mai=mai,reach=reach,COV15=float(cov.mean()),MAI15=float(np.nanmean(mai)))

    def verify_reassigned(self,lab):
        mat=self.matrix(lab); origins=np.unique(self.sample_o)
        for o in origins:
            ds=self.sample_d[self.sample_o==o]; ds=ds[lab[self.D['gd'][ds]]==lab[self.gd[o]]]
            direct=np.array([max([int(self.counts[d]) for d in ds if (int(self.mask[d])>>j)&1],default=0) for j in range(7)])
            assert np.array_equal(direct,mat[o])
        self.validation.append({'check':'raw_pairs_vs_compressed','plan':'MOD endpoint','origins':len(origins),'equal':True})

    def evaluate(self,states,labels,moved,affs,out):
        cache={}; rows=[]; spaces=[]; cats=[]; xkeep=[]; xkeys=[]; previous=self.x0; steps=[]
        base=self.metrics(self.base); errors=[]
        for ix,(s,lab,mm,aff) in enumerate(zip(states,labels,moved,affs)):
            h=s['composition_hash']
            if h not in cache:
                mat=self.matrix(lab); r=mat>0; assert np.all(~r|self.rn)
                xc=self.rn&~r; x=xc.any(1); a=self.metrics(mat); L=float(self.p[x].sum())
                new=x&~self.x0; resolved=~x&self.x0; both=x&self.x0; neither=~x&~self.x0
                a.update(L_unique=L,dL_unique=L-float(self.p[self.x0].sum()),new_excl=float(self.p[new].sum()),resolved=float(self.p[resolved].sum()),both_excl=float(self.p[both].sum()),neither_excl=float(self.p[neither].sum()))
                common=np.isfinite(a['mai'])&np.isfinite(base['mai']); a['dMAI_common']=float(np.mean(a['mai'][common]-base['mai'][common])) if common.any() else np.nan
                a['dMAI_n_common']=int(common.sum()); dd=np.stack([np.bincount(self.gd,weights=self.p*mask,minlength=424) for mask in [new,resolved,both,neither]],axis=1)
                cache[h]=(a,dd,x,xc)
            a,dd,x,xc=cache[h]
            row=dict(s,IFR=ifr(self.D,lab),**{k:v for k,v in a.items() if k not in ['cov','mai','reach']}); rows.append(row)
            err=abs(a['dL_unique']-(a['new_excl']-a['resolved'])); errors.append(err); assert err<.5
            assert abs(sum(a[k] for k in ['new_excl','resolved','both_excl','neither_excl'])-self.p.sum())<.5
            if s['strategy'] in ['LZ','MOD','IFR']:
                space=np.where(mm,0,np.where(np.isin(lab,aff)|np.isin(self.D['LZ'],aff),1,2)); st=[]
                for j,name in enumerate(['moved','affected_other','rest']):
                    b=dd[space==j].sum(0); st.append(b)
                    spaces.append(dict(key=s['key'],strategy=s['strategy'],k=s['k'],space=name,n_dong=int((space==j).sum()),population=float(self.D['popd'][space==j].sum()),new_excl=b[0],resolved=b[1],both_excl=b[2],neither_excl=b[3],net=b[0]-b[1]))
                assert np.allclose(np.array(st).sum(0),dd.sum(0),atol=.1)
                for j,c in enumerate(CATS): cats.append(dict(key=s['key'],strategy=s['strategy'],k=s['k'],category=c,COV=a['cov'][j],MAI=a['mai'][j],pop_reach=a['reach'][j],omitted_population=float(self.p[xc[:,j]].sum())))
            if s['strategy'] in ['LZ','MOD']:
                xkeep.append(x); xkeys.append(s['key'])
                if s['strategy']=='MOD':
                    steps.append(dict(k=s['k'],new_vs_prev=float(self.p[x&~previous].sum()),resolved_vs_prev=float(self.p[~x&previous].sum()),net_vs_prev=float(self.p[x].sum()-self.p[previous].sum())))
                previous=x
            if ix%300==0: print(f"{self.D['year']} evaluated {ix}/{len(states)}; unique {len(cache)}",flush=True)
        csv(out/'states.csv',rows); csv(out/'decomposition_space.csv',spaces); csv(out/'category_metrics.csv',cats); csv(out/'mod_stepwise.csv',steps)
        np.savez_compressed(out/'mod_cell_omission.npz',keys=np.array(xkeys),omitted=np.array(xkeep),grid_cd=self.D['gm'].grid_cd.to_numpy(str)[self.pos])
        R=pd.DataFrame(rows); krows=[]; trows=[]; mod=R[R.strategy=='MOD'].set_index('k'); rnd=R[R.strategy=='RAND']
        for k in sorted(mod.index):
            rs=rnd[rnd.k==k].sort_values('t').drop_duplicates('path'); vals=rs.dL_unique
            krows.append(dict(k=int(k),mod_dL=float(mod.loc[k,'dL_unique']),n_paths_total=100,n_paths_reaching_k=len(vals),rand_median=float(vals.median()) if len(vals) else np.nan,rand_p025=float(vals.quantile(.025)) if len(vals) else np.nan,share_rand_below_mod=float((vals<mod.loc[k,'dL_unique']).mean()) if len(vals) else np.nan,conditional_on_reaching=len(vals)<100))
            vals2=rnd[rnd.t==k].dL_unique
            trows.append(dict(t=int(k),mod_dL=float(mod.loc[k,'dL_unique']),rand_median=float(vals2.median()),rand_p025=float(vals2.quantile(.025)),mean_actual_k=float(rnd[rnd.t==k].k.mean())))
        csv(out/'random_k_comparison.csv',krows); csv(out/'random_t_comparison.csv',trows)
        self.validation.extend([{'check':'subset_union_transition_partition_all_states','states':len(rows),'max_identity_error':max(errors),'passed':True},{'check':'spatial_partition_sum','deterministic_states':len(spaces)//3,'passed':True},{'check':'MAI_bounds','min':float(pd.DataFrame(cats).MAI.min()),'max':float(pd.DataFrame(cats).MAI.max()),'passed':bool(pd.DataFrame(cats).MAI.between(1,7).all())}])
        assert all(v.get('passed',True) for v in self.validation)
        return R,dict(unique_evaluations=len(cache),LZ_L=float(self.p[self.x0].sum()),unbounded_any_unreachable_population=float(self.p[(~self.rn).any(1)].sum()),**self.info)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); ap.add_argument('--output-root',type=Path,default=Path(__file__).resolve().parents[1]); ap.add_argument('--year',type=int,choices=[2020,2025]); ap.add_argument('--check-inputs',action='store_true'); args=ap.parse_args()
    root=args.repository_root.resolve(); output=args.output_root.resolve(); output.mkdir(parents=True,exist_ok=True)
    design=verify_design(root)
    years=[args.year] if args.year else CFG['years']
    for year in years:
        t0=time.time(); paths=input_paths(root,year); out=output/'results'/str(year); out.mkdir(parents=True,exist_ok=True)
        lock=lock_inputs(root,paths); assert next(x for x in lock if x['role']=='facility')['sha256']==FAC_SHA
        source=json.loads(paths['source'].read_text('utf-8')); assert source['source_sha256']==FAC_SHA and source['units_sha256']==sha(paths['units']) and source['analysis_scope']['A_K']==7
        if args.check_inputs:
            saved=json.loads((out/'input_lock.json').read_text('utf-8')); assert saved==lock; print(year,'input lock verified',len(lock),flush=True); continue
        assert not (out/'summary.json').exists(),'Completed output exists; use a fresh --output-root, never silently overwrite'
        js(out/'input_lock.json',lock); js(output/'configuration.json',dict(CFG,design=design))
        env={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','pyarrow','geopandas','networkx','matplotlib']},'code_sha256':sha(__file__)}; js(out/'execution_environment.json',env)
        js(out/'execution_manifest.json',{'design':design,'code_sha256':sha(__file__),'configuration':CFG,'year':year,'input_lock_sha256':sha(out/'input_lock.json'),'execution':'full path construction and all service states; released upstream inputs read only'})
        D=load(root,year,paths); states,labels,moved,affs,pmeta=make_paths(D,out)
        ev=Accessibility(D,paths,out); ev.verify_reassigned(labels[pmeta['K_mod']]); R,ameta=ev.evaluate(states,labels,moved,affs,out)
        assert lock==lock_inputs(root,paths),'Input changed during run'
        assert design==verify_design(root),'Design changed during run'
        summary=dict(year=year,**pmeta,**ameta,OD_total=D['FT'],OD_self=float(np.trace(D['F'])),IFR_initial=ifr(D,D['LZ']),MOD_end=R[R.strategy=='MOD'].iloc[-1].to_dict(),IFR_end=R[R.strategy=='IFR'].iloc[-1].to_dict(),MOD_min=R[R.strategy=='MOD'].sort_values(['dL_unique','k']).iloc[0].to_dict(),input_hashes_unchanged=True,seconds=time.time()-t0)
        js(out/'verification.json',ev.validation); js(out/'summary.json',summary); print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)

if __name__=='__main__': main()
