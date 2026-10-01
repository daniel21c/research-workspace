"""Research 2: frozen release inputs -> district benchmarking, tables, figures.
No boundary generation and no writes outside --output. Python 3.12.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, sys, time
from pathlib import Path
import importlib.metadata as metadata
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

PACKAGE=Path(__file__).resolve().parents[1]
SEED=20260929

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def dump(obj,path):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')

def table(df,path):
    df.to_csv(path,index=False,encoding='utf-8-sig',float_format='%.12g')

def overlap(a,b,weights=None,details=False):
    """Maximize total intersection; sum intersection / sum union (not mean IoU)."""
    av=np.unique(a); bv=np.unique(b)
    w=np.ones(len(a)) if weights is None else np.asarray(weights)
    x=np.zeros((len(av),len(bv)))
    np.add.at(x,(np.searchsorted(av,a),np.searchsorted(bv,b)),w)
    ri,ci=linear_sum_assignment(-x)
    s=x[ri,ci].sum(); n=w.sum()
    score=s/(2*n-s)
    j=x/(x.sum(1)[:,None]+x.sum(0)[None,:]-x)
    best=j.argmax(axis=1)  # sorted IDs -> smallest ID on equal Jaccard
    legacy=x[np.arange(len(av)),best].sum()/n
    out=dict(iou_1to1=float(score),matched_share=float(s/n),jaccard_maxmatch_share=float(legacy),ari=float(adjusted_rand_score(a,b)))
    if details:
        out['pairs']=[dict(lz=int(av[i]),ld=int(bv[k]),intersection=float(x[i,k]),union=float(x[i].sum()+x[:,k].sum()-x[i,k]),iou=float(j[i,k])) for i,k in zip(ri,ci)]
    return out

def q_matrix(f,labels,drop_loops=False):
    f=np.array(f,copy=True)
    if drop_loops: np.fill_diagonal(f,0)
    total=f.sum()
    if total<=0: raise ValueError('No positive within-district flow')
    q=0.
    for c in np.unique(labels):
        m=labels==c
        inside=f[np.ix_(m,m)].sum()
        strength=f[m,:].sum()+f[:,m].sum()
        q+=inside/total-(strength/(2*total))**2
    return float(q)

def q_networkx(f,labels):
    """Independent undirected graph implementation, including one loop edge f_ii."""
    graph=nx.Graph(); graph.add_nodes_from(range(len(f)))
    for i in range(len(f)):
        if f[i,i]>0: graph.add_edge(i,i,weight=float(f[i,i]))
        for j in range(i+1,len(f)):
            w=f[i,j]+f[j,i]
            if w>0: graph.add_edge(i,j,weight=float(w))
    groups=[set(np.flatnonzero(labels==c)) for c in np.unique(labels)]
    return nx.community.modularity(graph,groups,weight='weight',resolution=1)

def flow_stats(f,lz,ld,origins=None,drop_loops=False,within_district=None):
    w=np.array(f,copy=True)
    if drop_loops: np.fill_diagonal(w,0)
    if origins is None: origins=np.arange(len(w))
    o=np.asarray(origins)
    a=lz[o,None]==lz[None,:]; b=ld[o,None]==ld[None,:]
    sub=w[o,:]
    den=sub.sum() if within_district is None else w[np.ix_(o,within_district)].sum()
    z=sub[a].sum(); d=sub[b].sum(); both=sub[a&b].sum()
    zo=sub[a&~b].sum(); do=sub[b&~a].sum()
    return dict(total_flow=float(den),internal_lz=float(z),internal_ld=float(d),both_flow=float(both),lz_only_flow=float(zo),ld_only_flow=float(do),neither_flow=float(den-both-zo-do),ifr_lz=float(z/den),ifr_ld=float(d/den),g=float((d-z)/den),d_flow=float((zo+do)/den),lz_only=float(zo/den),ld_only=float(do/den))

def spatial_graph(geom):
    graph=nx.Graph(); graph.add_nodes_from(range(len(geom)))
    for i in range(len(geom)):
        for j in range(i+1,len(geom)):
            if geom[i].touches(geom[j]): graph.add_edge(i,j)
    return graph

def random_connected_labels(graph,k,rng):
    """Random edge-priority Kruskal tree, then uniformly cut k-1 tree edges.
    A reproducible connected reference generator, NOT uniform partition sampling.
    """
    edges=sorted(graph.edges()); perm=rng.permutation(len(edges))
    uf=nx.utils.UnionFind(graph.nodes); tree=[]
    for ix in perm:
        i,j=edges[ix]
        if uf[i]!=uf[j]: uf.union(i,j); tree.append((i,j))
    assert len(tree)==len(graph)-1
    cuts=set(rng.choice(len(tree),size=k-1,replace=False).tolist())
    cut=nx.Graph();cut.add_nodes_from(graph.nodes)
    cut.add_edges_from(e for j,e in enumerate(tree) if j not in cuts)
    labels=np.zeros(len(graph),int)
    for c,nodes in enumerate(sorted(nx.connected_components(cut),key=lambda z:min(z))): labels[list(nodes)]=c
    assert len(np.unique(labels))==k
    return labels

def analyze(input_dir,output,null_draws=1000):
    start=time.perf_counter()
    cfg_path=PACKAGE/'analysis_config.json'
    cfg=json.loads(cfg_path.read_text(encoding='utf-8'))
    assert cfg['shared_design_status']=='applied'
    assert sha(PACKAGE/cfg['design_path'])==cfg['design_sha256'], 'Design changed: revise and freeze the contract first.'
    assert (cfg['primary_year'],cfg['years'],cfg['n_dong'],cfg['n_district'],cfg['n_zones'])==(2025,[2020,2025],424,25,116)
    assert cfg['seed']==SEED and cfg['null_draws_per_district']==null_draws and cfg['bootstrap_draws']==5000
    assert cfg['self_loops'] and cfg['facility_accessibility']['used_in_analysis'] is False
    output.mkdir(parents=True,exist_ok=True)
    for sub in ['tables','figures','audit']: (output/sub).mkdir(exist_ok=True)
    checks=[]
    def check(name,condition,detail):
        checks.append(dict(check=name,passed=bool(condition),detail=detail))
        if not condition: raise AssertionError(f'{name}: {detail}')
    check('design_contract_hash',sha(PACKAGE/cfg['design_path'])==cfg['design_sha256'],cfg['design_version'])
    fa=cfg['facility_accessibility']
    check('seven_category_metadata_not_used',(fa['category_count'],fa['analysis_types'],fa['total_types'],fa['sfca_items'],fa['used_in_analysis'])==(7,27,32,34,False),'facility-v1.4/access-v3.3 metadata; no accessibility outcomes imported')
    for r in cfg['shared_sources']:
        check('contract_'+Path(r['package_path']).name,sha(PACKAGE/r['package_path'])==r['sha256'],r['role'])
    sources=json.loads((PACKAGE/'audit/source_manifest.json').read_text(encoding='utf-8'))
    for r in sources:
        if r['role']=='analysis input':
            p=input_dir/Path(r['package_path']).name
            check('hash_'+p.name,sha(p)==r['sha256'],sha(p))
    gpkg=input_dir/'seoul_boundaries_all.gpkg'
    d=gpd.read_file(gpkg,layer='dong_424').sort_values('Dong').reset_index(drop=True)
    check('dong_schema',set(['Dong','Ku','life_zone_id','leiden_2020','leiden_2025'])<=set(d.columns),d.columns.tolist())
    check('dong_424_unique',len(d)==424 and d.Dong.nunique()==424,int(d.Dong.nunique()))
    check('geometry',str(d.crs)=='EPSG:5179' and d.geometry.is_valid.all() and not d.geometry.is_empty.any(),'EPSG:5179; valid nonempty')
    check('districts_25',d.Ku.nunique()==25,int(d.Ku.nunique()))
    ids=d.Dong.to_numpy(); index={v:i for i,v in enumerate(ids)}; lz=d.life_zone_id.to_numpy()
    official=pd.read_csv(input_dir/'dong_to_official_livingzone_mapping_424.csv').sort_values('Dong')
    check('official_mapping',np.array_equal(ids,official.Dong) and np.array_equal(lz,official.life_zone_id),'424 key-sorted rows match GPKG')
    area=d.geometry.area.to_numpy()
    layer=gpd.read_file(gpkg,layer='official_livingzone_116_dongbased')
    check('official_same_area',d.geometry.union_all().symmetric_difference(layer.geometry.union_all()).area<1e-4,'union symmetric difference < 1e-4 m2')
    check('official_dissolve',len(layer)==116 and all(d.loc[d.life_zone_id==int(r.life_zone_id)].geometry.union_all().symmetric_difference(r.geometry).area<1e-4 for r in layer.itertuples()),'116 original same-area dong-based zones')
    adjacency=spatial_graph(d.geometry.to_list())
    districts=[]; city=[]; pairs=[]; zones=[]; contiguous=[]; datainfo=[]; sensitivities=[]; null_summary=[]; null_rows=[]; flows={}; stats_by_year={}
    for year in cfg['years']:
        mapping=pd.read_csv(input_dir/f'dong_to_leiden_{year}_mapping_424.csv').sort_values('Dong')
        ld=d[f'leiden_{year}'].to_numpy()
        check(f'ld_{year}_mapping',np.array_equal(ids,mapping.Dong) and np.array_equal(ld,mapping.global_community_id),'CSV/GPKG identical keyed 424 labels')
        for label,name in [(lz,'LZ'),(ld,'LD')]:
            check(f'{year}_{name}_116',len(np.unique(label))==116,len(np.unique(label)))
            check(f'{year}_{name}_single_district',pd.DataFrame({'label':label,'ku':d.Ku}).groupby('label').ku.nunique().eq(1).all(),'global labels never span districts')
        od=pd.read_parquet(input_dir/f'od_daily_{year}01.parquet')
        check(f'{year}_od_schema',set(od.columns)=={'dong_O','dong_D','flow','n_rows','n_masked'},od.columns.tolist())
        check(f'{year}_od_unique',not od.duplicated(['dong_O','dong_D']).any(),len(od))
        check(f'{year}_od_codes',set(od.dong_O)==set(ids) and set(od.dong_D)==set(ids),'424 origins and destinations, no unknowns')
        check(f'{year}_od_values',np.isfinite(od.flow).all() and od.flow.ge(0).all() and od.n_rows.ge(od.n_masked).all() and od.n_masked.ge(0).all(),'finite nonnegative flows, valid row/mask counts')
        f=np.zeros((424,424)); f[od.dong_O.map(index),od.dong_D.map(index)]=od.flow
        flows[year]=f
        c=flow_stats(f,lz,ld); c.update(year=year,**overlap(lz,ld)); city.append(c); stats_by_year[year]=c
        datainfo.append(dict(year=year,od_pairs=len(od),selected_rows=int(od.n_rows.sum()),masked_rows=int(od.n_masked.sum()),total_flow=float(f.sum()),within_dong_flow=float(np.trace(f)),within_district_flow=float(f[(d.Ku.to_numpy()[:,None]==d.Ku.to_numpy()[None,:])].sum()),minimum_membership=float(mapping.membership_prob.min())))
        # Truly separate record-wise classification, avoiding dense-array masks.
        lzmap=dict(zip(ids,lz)); ldmap=dict(zip(ids,ld))
        zmask=od.dong_O.map(lzmap).eq(od.dong_D.map(lzmap)); dmask=od.dong_O.map(ldmap).eq(od.dong_D.map(ldmap))
        independent=[od.loc[zmask,'flow'].sum()/od.flow.sum(),od.loc[dmask,'flow'].sum()/od.flow.sum(),od.loc[zmask^dmask,'flow'].sum()/od.flow.sum()]
        check(f'{year}_independent_ifr_xor',np.allclose(independent,[c['ifr_lz'],c['ifr_ld'],c['d_flow']],atol=1e-12,rtol=0),independent)
        check(f'{year}_decomposition',abs(c['g']-(c['ld_only']-c['lz_only']))<1e-12 and c['d_flow']+1e-12>=abs(c['g']),'G=LD-only-LZ-only; D_flow>=abs(G)')
        for ku,sub in d.groupby('Ku',sort=True):
            ix=sub.index.to_numpy(); ff=f[np.ix_(ix,ix)]; a=lz[ix]; b=ld[ix]
            check(f'{year}_{ku}_count',len(np.unique(a))==len(np.unique(b)),len(np.unique(a)))
            m=overlap(a,b,details=True); am=overlap(a,b,area[ix])
            row=dict(year=year,ku=int(ku),ku_name=sub.ku_name.iloc[0],n_dong=len(ix),n_zones=len(np.unique(a)),**flow_stats(f,lz,ld,ix))
            row.update({k:v for k,v in m.items() if k!='pairs'});row['area_iou']=am['iou_1to1']
            row.update(q_lz=q_matrix(ff,a),q_ld=q_matrix(ff,b));row['delta_q']=row['q_ld']-row['q_lz']
            check(f'{year}_{ku}_independent_Q',max(abs(row['q_lz']-q_networkx(ff,a)),abs(row['q_ld']-q_networkx(ff,b)))<1e-12,'numpy group-strength formula versus NetworkX undirected weighted graph')
            districts.append(row)
            for p in m['pairs']: pairs.append(dict(year=year,ku=int(ku),ku_name=row['ku_name'],**p))
            sens=flow_stats(f,lz,ld,ix,drop_loops=True)
            ingu=flow_stats(f,lz,ld,ix,within_district=ix)
            sensitivities.append(dict(year=year,ku=int(ku),ku_name=row['ku_name'],g=row['g'],g_no_loop=sens['g'],d_flow_no_loop=sens['d_flow'],g_within_ku_den=ingu['g'],delta_q=row['delta_q'],delta_q_no_loop=q_matrix(ff,b,True)-q_matrix(ff,a,True),iou=row['iou_1to1'],area_iou=row['area_iou']))
            if year==2025:
                local=nx.relabel_nodes(adjacency.subgraph(ix),{v:i for i,v in enumerate(ix)},copy=True)
                check(f'queen_{ku}_connected',nx.is_connected(local),'touches includes point adjacency')
                rng=np.random.default_rng(SEED+int(ku)); vals=[]
                for draw in range(null_draws):
                    labels=random_connected_labels(local,len(np.unique(a)),rng)
                    v=overlap(a,labels)['iou_1to1'];vals.append(v)
                    null_rows.append(dict(ku=int(ku),draw=draw,iou=v))
                vals=np.asarray(vals)
                null_summary.append(dict(ku=int(ku),ku_name=row['ku_name'],observed=row['iou_1to1'],q05=float(np.quantile(vals,.05)),q50=float(np.median(vals)),q95=float(np.quantile(vals,.95)),upper_tail_fraction=float((1+(vals>=row['iou_1to1']-1e-12).sum())/(len(vals)+1)),draws=len(vals)))
        for labels,name in [(lz,'LZ'),(ld,'LD')]:
            for zone in np.unique(labels):
                ix=np.flatnonzero(labels==zone); sub=d.iloc[ix]
                den=f[ix,:].sum(); num=f[np.ix_(ix,ix)].sum(); geom=sub.geometry.union_all()
                components=nx.number_connected_components(adjacency.subgraph(ix))
                parts=1 if geom.geom_type=='Polygon' else len(geom.geoms)
                contiguous.append(dict(year=year,partition=name,zone=int(zone),ku=int(sub.Ku.iloc[0]),queen_components=components,polygon_parts=parts))
                zones.append(dict(year=year,partition=name,zone=int(zone),ku=int(sub.Ku.iloc[0]),ku_name=sub.ku_name.iloc[0],n_dong=len(ix),area_km2=float(area[ix].sum()/1e6),total_flow=float(den),internal_flow=float(num),ifr=float(num/den),queen_components=components,polygon_parts=parts))
        for partition,key in [('LZ','internal_lz'),('LD','internal_ld')]:
            part=[r for r in zones if r['year']==year and r['partition']==partition]
            weighted=sum(r['internal_flow'] for r in part)/sum(r['total_flow'] for r in part)
            check(f'{year}_{partition}_ratio_of_sums',abs(weighted-c['ifr_'+partition.lower()])<1e-12,'116 zone numerator/denominator sums equal city')
    district=pd.DataFrame(districts); main=district[district.year==2025].copy()
    # Primary joint signal is explicitly descriptive, not a mandatory redesign list.
    main['review_signal']=['정합' if np.isclose(r.iou_1to1,1) else ('이동포착 증가·경계 검토' if r.g>1e-12 and r.delta_q>1e-12 else '상충·맥락 검토') for r in main.itertuples()]
    corr=[];rng=np.random.default_rng(SEED)
    for y in ['g','delta_q','d_flow']:
        a=main.iou_1to1.to_numpy();b=main[y].to_numpy(); boots=[]
        for _ in range(cfg['bootstrap_draws']):
            ix=rng.integers(0,len(a),len(a)); rho=spearmanr(a[ix],b[ix]).statistic
            if np.isfinite(rho): boots.append(rho)
        corr.append(dict(x='iou_1to1',y=y,n=len(a),rho=float(spearmanr(a,b).statistic),lo=float(np.quantile(boots,.025)),hi=float(np.quantile(boots,.975)),bootstrap_draws=len(boots)))
    transfer=flow_stats(flows[2020],lz,d.leiden_2025.to_numpy());transfer.update(od_year=2020,partition_year=2025,role='retrospective transfer, not future validation or temporal attribution')
    outputs={'T1_input_overview':pd.DataFrame(datainfo),'T2_city_summary':pd.DataFrame(city),'T3_district_2025':main,'T4_matched_zone_pairs':pd.DataFrame(pairs),'T5_zone_metrics':pd.DataFrame(zones),'T6_sensitivity':pd.DataFrame(sensitivities),'T7_connected_reference_2025':pd.DataFrame(null_summary),'T8_correlations_2025':pd.DataFrame(corr),'A1_district_2020':district[district.year==2020],'A2_fixed2025_on2020':pd.DataFrame([transfer]),'A3_contiguity':pd.DataFrame(contiguous),'A4_reference_draws':pd.DataFrame(null_rows)}
    for name,df in outputs.items():table(df,output/'tables'/f'{name}.csv')
    make_figures(d,main,outputs,output/'figures')
    summary=dict(primary_year=2025,city=stats_by_year[2025],other_wave=stats_by_year[2020],n_identical_districts=int(main.iou_1to1.eq(1).sum()),identical_districts=main.loc[main.iou_1to1.eq(1),'ku_name'].tolist(),median_iou=float(main.iou_1to1.median()),range_iou=[float(main.iou_1to1.min()),float(main.iou_1to1.max())],positive_g=int(main.g.gt(1e-12).sum()),negative_g=int(main.g.lt(-1e-12).sum()),zero_g=int(main.g.abs().le(1e-12).sum()),lowest_iou=main.nsmallest(5,'iou_1to1')[['ku_name','iou_1to1','g','d_flow','delta_q']].to_dict('records'),largest_d_flow=main.nlargest(5,'d_flow')[['ku_name','d_flow','g','iou_1to1']].to_dict('records'),signals=main.review_signal.value_counts().to_dict(),reference_above95=int(sum(r['observed']>r['q95'] for r in null_summary)),correlations=corr,transfer=transfer)
    dump(summary,output/'summary.json');dump(checks,output/'audit/checks.json')
    run=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={m:metadata.version(m) for m in ['numpy','pandas','geopandas','shapely','pyarrow','scipy','scikit-learn','networkx','matplotlib']},seed=SEED,null_draws=null_draws,elapsed_seconds=time.perf_counter()-start,input_hashes={p.name:sha(p) for p in input_dir.iterdir() if p.is_file()},code_hash=sha(__file__),validation_checks=len(checks),validation_passed=sum(c['passed'] for c in checks),output_hashes={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='execution.json'})
    run.update(design_version=cfg['design_version'],design_sha256=cfg['design_sha256'],configuration_sha256=sha(cfg_path),code_version=cfg['code_version'],analytical_releases=cfg['analytical_releases'],shared_design_status=cfg['shared_design_status'],facility_accessibility_used=False,common_category_count=fa['category_count'])
    dump(run,output/'audit/execution.json')
    print(json.dumps(summary,ensure_ascii=False,indent=2)); print(f'CHECKS {len(checks)}/{len(checks)}; {run["elapsed_seconds"]:.1f}s')

def make_figures(d,main,outs,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    font_candidates=[Path('C:/Windows/Fonts/malgun.ttf'),Path('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')]
    for p in font_candidates:
        if p.exists():fm.fontManager.addfont(str(p));plt.rcParams['font.family']=fm.FontProperties(fname=str(p)).get_name();break
    plt.rcParams.update({'font.size':9,'axes.unicode_minus':False,'figure.dpi':150,'savefig.dpi':220})
    def save(fig,name):
        fig.savefig(out/f'{name}.png',bbox_inches='tight',facecolor='white',metadata={'Software':'Research2'});plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,5))
    for ax,label,title in [(axs[0],'life_zone_id','공식 생활권: 동 기반 116권역'),(axs[1],'leiden_2025','이동 기반 구획: 2025년 116권역')]:
        d.dissolve(label).plot(ax=ax,column=label if label in d.dissolve(label).columns else None,color='#dae8f0',edgecolor='#24546b',linewidth=.45)
        d.dissolve('Ku').boundary.plot(ax=ax,color='#303c49',linewidth=.9);ax.set_title(title,pad=10);ax.axis('off')
    save(fig,'F1_boundaries_2025')
    km=d.dissolve('Ku').reset_index()[['Ku','geometry']].merge(main,left_on='Ku',right_on='ku',validate='one_to_one')
    fig,axs=plt.subplots(1,3,figsize=(12,4.4))
    for ax,col,title,cmap in [(axs[0],'iou_1to1','1:1 동 기준 IoU','Blues'),(axs[1],'g','IFR 차이 G (LD - LZ)','RdBu'),(axs[2],'d_flow','통행 불일치 D_flow','Oranges')]:
        lim=max(abs(km[col].min()),abs(km[col].max()))
        kw={'vmin':-lim,'vmax':lim} if col=='g' else {'vmin':0,'vmax':1 if col=='iou_1to1' else km[col].max()}
        km.plot(ax=ax,column=col,cmap=cmap,edgecolor='white',linewidth=.5,legend=True,legend_kwds={'shrink':.65},**kw);ax.set_title(title);ax.axis('off')
    save(fig,'F2_district_diagnostics')
    a=main.sort_values('d_flow'); y=np.arange(len(a))
    fig,axs=plt.subplots(1,2,figsize=(10,7.4),sharey=True)
    axs[0].scatter(a.ifr_lz*100,y,label='공식',c='#546e7a',marker='s',s=25);axs[0].scatter(a.ifr_ld*100,y,label='Leiden',c='#c46936',s=25)
    for n,r in enumerate(a.itertuples()):axs[0].plot([r.ifr_lz*100,r.ifr_ld*100],[n,n],color='#9da8aa',zorder=0)
    axs[0].set_yticks(y,a.ku_name);axs[0].set_xlabel('IFR (%)');axs[0].legend(frameon=False)
    axs[1].barh(y,-a.lz_only*100,color='#54799a',label='공식만 내부');axs[1].barh(y,a.ld_only*100,color='#d89055',label='Leiden만 내부');axs[1].axvline(0,color='black',lw=.6);axs[1].set_xlabel('출발 통행 대비 비중 (%); 두 막대 길이 합 = D_flow');axs[1].legend(frameon=False)
    fig.tight_layout();save(fig,'F3_ifr_and_disagreement')
    fig,axs=plt.subplots(1,3,figsize=(11,3.7))
    for ax,col,title in zip(axs,['g','delta_q','d_flow'],['G','ΔQ','D_flow']):
        ax.scatter(main.iou_1to1,main[col],c='#246b85',s=28)
        row=outs['T8_correlations_2025'].set_index('y').loc[col]
        ax.set_title(f'{title}: ρ = {row.rho:.3f}');ax.set_xlabel('1:1 동 기준 IoU');ax.set_ylabel(title);ax.axhline(0,c='#777777',lw=.5)
    fig.tight_layout();save(fig,'F4_overlap_flow_associations')
    a=outs['T7_connected_reference_2025'].sort_values('observed');y=np.arange(len(a))
    fig,ax=plt.subplots(figsize=(9,6.8));ax.hlines(y,a.q05,a.q95,color='#b8cbd6',lw=5,label='연결 참조 분할 5–95%');ax.scatter(a.q50,y,marker='|',c='#40637c');ax.scatter(a.observed,y,c='#bc652d',s=25,label='관측 Leiden');ax.set_yticks(y,a.ku_name);ax.set_xlabel('공식 생활권과의 1:1 동 기준 IoU');ax.legend(loc='lower right',frameon=False);fig.tight_layout();save(fig,'F5_connected_reference')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input-dir',type=Path,default=PACKAGE/'inputs');parser.add_argument('--output',type=Path,default=PACKAGE/'results');parser.add_argument('--null-draws',type=int,default=1000)
    args=parser.parse_args();analyze(args.input_dir,args.output,args.null_draws)
