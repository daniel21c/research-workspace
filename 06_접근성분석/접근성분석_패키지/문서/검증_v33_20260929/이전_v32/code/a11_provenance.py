"""Portable, non-circular fingerprints. Historical metadata are never backfilled.

Run fingerprints cover the exact a06 runtime code and inputs consumed by that run.
Release inventories additionally cover upstream source evidence and analysis helpers.
"""
from pathlib import Path
import hashlib,json,datetime,importlib.metadata,platform,sys
import a00_config as C

SCHEMA = 'access-run-provenance/2'
RELEASE = 'access-engine-v3.2-facility-v1.3-20260929'
RUNTIME_CODE = ('a00_config.py', 'a06_engine.py', 'a11_provenance.py')

def sha256(p):
    with Path(p).open('rb') as f:
        h=hashlib.sha256()
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        return h.hexdigest()

def digest(records):
    return hashlib.sha256(json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def inventory(paths, base):
    base = Path(base).resolve()
    rows = []
    for p in sorted(set(Path(x).resolve() for x in paths), key=lambda x:x.as_posix()):
        rows.append(dict(file=p.relative_to(base).as_posix(),bytes=p.stat().st_size,sha256=sha256(p)))
    return dict(sha256=digest(rows),files=rows)

def check_inventory(value, base):
    errors=[]
    rows=value.get('files',[])
    if not rows or value.get('sha256') != digest(rows):
        errors.append('empty or invalid fingerprint digest')
    seen=set();base=Path(base).resolve()
    for r in rows:
        rel=r.get('file','');p=(base/rel).resolve()
        if rel in seen or not p.is_relative_to(base):
            errors.append('duplicate or outside root: '+rel);continue
        seen.add(rel)
        if not p.is_file() or p.stat().st_size != r.get('bytes') or sha256(p) != r.get('sha256'):
            errors.append('stale/missing: '+rel)
    return errors

def runtime_environment():
    versions={}
    for name in ['numpy','pandas','pyarrow','scipy','geopandas','shapely','pyproj','duckdb','osmium','matplotlib']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    return {'python':sys.version,'platform':platform.platform(),'packages':versions}

def dataset_files(dataset):
    """Arrow filesystem and union datasets expose different public interfaces."""
    if hasattr(dataset,'files'):return sorted(set(dataset.files))
    if hasattr(dataset,'children'):
        return sorted({p for child in dataset.children for p in dataset_files(child)})
    raise TypeError('Dataset does not expose auditable input files')


def capture_run(args, ttm_files):
    net=args.year if args.net_year is None else args.net_year
    paths=[C.DATA/'grid'/f'grid{args.grid}_master.parquet',C.UNITS_PARQUET,C.UNITS_SOURCE_JSON]
    paths += [Path(p) for p in ttm_files if args.ku is None or f'ku={args.ku}' in Path(p).parts]
    if args.snap:paths.append(C.DATA/'ttm'/f'snap{args.grid}_{net}.parquet')
    code=Path(__file__).resolve().parent
    return dict(schema=SCHEMA,release=RELEASE,recorded_at=datetime.datetime.now().astimezone().isoformat(),
                code_base='package_code',input_base='package_inputs',
                code=inventory([code/n for n in RUNTIME_CODE],code),inputs=inventory(paths,C.DATA),upstream_inputs=inventory([C.FACILITY_PARQUET],C.BASE),
                environment=runtime_environment())

def required_checks(m):
    if m.get('catset')=='B':
        return {'origins_complete','COV_in_0_1','reach_in_0_1','pop_total_same_all_levels'}
    req={'pop_total_same_all_b','COV_in_0_1','MAI_in_1_K','PWATT_le_T','r_b_le_r_none','r_ku_ge_r_dong'}
    if m.get('sfca'):
        req|={'sfca_nonneg','sfca_conservation_global','sfca_conservation_unit'}
    return req

def metadata_issues(m, meta_path, package_root=None, code_dir=None, repo_root=None):
    """Return (failures, unverified). Missing historic evidence is unverified, never PASS."""
    failures=[];unverified=[]
    checks=m.get('checks')
    if not isinstance(checks,dict) or not checks:
        unverified.append('no invariant checks recorded')
    else:
        for key in sorted(required_checks(m)):
            if key not in checks:unverified.append('check not recorded: '+key)
            elif checks[key] is not True:failures.append('check failed/non-boolean: '+key)
    package_root=Path(package_root or C.ROOT)
    base=Path(meta_path).parent if m.get('files_base')=='run_meta_directory' else package_root
    files=m.get('files',[])
    if not files:failures.append('no output files')
    for r in files:
        p=base/r['file']
        if not p.is_file() or sha256(p)!=r.get('sha256'):failures.append('output stale/missing: '+r['file'])
    prov=m.get('provenance')
    if prov is None:unverified.append('historical run: code/input fingerprints not recorded')
    elif prov.get('schema') not in (SCHEMA,'access-run-provenance/1'):failures.append('unknown provenance schema')
    else:
        failures += ['code '+x for x in check_inventory(prov.get('code',{}),code_dir or Path(__file__).parent)]
        ibase=package_root/'데이터/입력' if prov.get('input_base')=='package_inputs' else (repo_root or C.BASE)
        failures += ['input '+x for x in check_inventory(prov.get('inputs',{}),ibase)]
        if prov.get('schema')==SCHEMA:
            failures += ['upstream '+x for x in check_inventory(prov.get('upstream_inputs',{}),repo_root or C.BASE)]
    if m.get('boundary_year',{}).get('ld_other'):
        if not m.get('sfca_skipped'):failures.append('xb must explicitly record skipped 2SFCA')
        if m.get('sfca'):failures.append('xb unexpectedly contains 2SFCA')
    return failures,unverified
