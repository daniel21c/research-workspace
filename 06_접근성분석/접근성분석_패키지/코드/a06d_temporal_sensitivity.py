"""Optional four-condition category-support sensitivity; never edits paper inputs."""
import argparse,json
from pathlib import Path
import pandas as pd
import a00_config as C
import a06c_delta as D
import a11_provenance as P

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cases=[('moving_ld_moving_net','main','main',('ld','lz116'),('ld','lz116')),
           ('moving_ld_net2025','xb_net2025','xb_main',('ld','lz116'),('ld','lz116')),
           ('fixed_ld2020_net2025','xb_net2025','xb_main',('ld','lz116'),('ld_other','lz116')),
           ('fixed_ld2025_net2025','xb_net2025','xb_main',('ld_other','lz116'),('ld','lz116')),
           ('moving_ld_snap','sens_snap','sens_snap',('ld','lz116'),('ld','lz116'))]
    records=[]
    for name,t0,t1,p0,p1 in cases:
        f0=C.OUT/t0/'unit_access_2020_100.csv';f1=C.OUT/t1/'unit_access_2025_100.csv'
        a=pd.read_csv(f0);b=pd.read_csv(f1)
        z=D.temporal_dmai_common4(a,b,pair0=p0,pair1=p1)
        dst=out/(name+'.csv');z.to_csv(dst,encoding='utf-8-sig')
        changed=z.difference.abs()>1e-12
        signs=(z.change_common4*z.change_pairwise)<0
        records.append(dict(case=name,pair0=p0,pair1=p1,n=len(z),changed=int(changed.sum()),sign_changes=int(signs.sum()),undefined=int(z.change_common4.isna().sum()),inputs=P.inventory([f0,f1],C.ROOT),output_sha256=P.sha256(dst)))
    (out/'verification.json').write_text(json.dumps({'definition':'mean of category-specific (LD-LZ) time differences over common support of all four cells; sensitivity only','cases':records},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('inputs','output_sha256')} for r in records],ensure_ascii=False))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=C.OUT/'temporal_common4');run(ap.parse_args().out)
