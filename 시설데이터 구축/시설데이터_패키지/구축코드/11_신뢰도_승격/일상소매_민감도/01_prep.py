import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cmp_lib import prep_geo
g, d = prep_geo(force=True)
print(len(g), len(d), d[['pop2020','pop2025']].sum().to_dict(), g[['pop2020','pop2025']].sum().to_dict(), (g.pop2020>0).sum(), (g.pop2025>0).sum(), g.adm_dong_cd.nunique())
