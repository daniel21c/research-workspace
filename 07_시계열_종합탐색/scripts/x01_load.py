# -*- coding: utf-8 -*-
"""x01_load.py — 시계열 종합 탐색 공통 로더

확정 배포본만 읽어 구(25)·공식 생활권(116)·동(424) 단위 × 연도(2020·2025) 패널을 만든다.
읽기 전용: 다른 폴더의 파일은 읽기만 하고, 산출물은 07_시계열_종합탐색/output/tables/ 에만 쓴다.

패널 열(접두어):
  acc_{COV|MAI|PWATT}_{b}_{cat}   접근성 엔진 main (b ∈ none, dong424, lz116, ld, ku; cat = 종합 + 8개)
  sens_{tag}_COV_lz116_종합 등     민감도(T600, retail_without, snap, net2025[2020만])
  pop, hh, biz, emp                격자 마스터 합(인구 2019→2020행, 2024→2025행)
  fac_{cat_A}, fac_{시설}           시설 수(분석가능, role A·B)
  nat_{item}                       국가 최저기준 충족률(natstd_B)
  mob_*                            이동 지표(구: t02_long, 생활권: t08, 동: OD에서 직접)
"""
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "07_시계열_종합탐색"
OUT = HERE / "output" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

ACC = ROOT / "06_접근성분석/접근성분석_패키지/데이터"
CORE = ROOT / "00_공통_코어엔진/data"
KPA = ROOT / "04_불일치_시간변화_KPA/output/package_20260924/tables"
FAC = ACC / "입력/facility/facility_2020_2025_units.parquet"
GRID = ACC / "입력/grid/grid100_master.parquet"

YEARS = (2020, 2025)
POPYEAR = {2020: 2019, 2025: 2024}
CATS = ["종합", "교육", "보육·복지", "의료", "문화", "체육", "행정·안전", "소매", "생활서비스"]
BS = ["none", "dong424", "lz116", "ld", "ku"]
KEYFAC = ["어린이집", "유치원", "학교", "공공도서관", "의원", "약국", "노인 이용시설", "일상소매", "주민센터"]

UNIT_KEY = {"ku": "ku", "lz116": "lz116", "dong424": "dong424"}


def rcsv(p, **kw):
    return pd.read_csv(p, encoding="utf-8-sig", **kw)


def sha(p, n=16):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


# ---------- 1. 접근성 ----------
def load_access(tag, year, level):
    p = ACC / f"결과/{tag}/unit_access_{year}_100.csv"
    if not p.exists():
        return None
    d = rcsv(p)
    d = d[(d.unit_level == level) & d.b.isin(BS) & d.cat.isin(CATS)].copy()
    d["PWATT"] = d.PWATT_sec / 60.0
    w = d.pivot_table(index="unit_id", columns=["b", "cat"], values=["COV", "MAI", "PWATT", "pop_total", "pop_reach"])
    w.columns = [f"{m}_{b}_{c}" for m, b, c in w.columns]
    return w


def access_panel(level):
    rows = []
    for y in YEARS:
        w = load_access("main", y, level)
        w = w.add_prefix("acc_")
        for tag in ["sens_T600", "sens_retail_without", "sens_snap", "sens_net2025"]:
            s = load_access(tag, y, level)
            if s is None:
                continue
            keep = [c for c in s.columns if c.split("_")[0] in ("COV", "MAI", "PWATT") and ("_lz116_" in c or "_none_" in c or "_ld_" in c)]
            s = s[keep].add_prefix(f"{tag.replace('sens_', 'sens_')}_")
            w = w.join(s, how="left")
        w["year"] = y
        rows.append(w.reset_index())
    return pd.concat(rows, ignore_index=True)


# ---------- 2. 인구·격자 ----------
def pop_panel(level):
    g = pd.read_parquet(GRID)
    key = UNIT_KEY[level]
    rows = []
    for y in YEARS:
        py = POPYEAR[y]
        a = g.groupby(key).agg(pop=(f"pop_{py}", "sum"), hh=(f"hh_{py}", "sum"), biz=(f"biz_{py}", "sum"), emp=(f"emp_{py}", "sum"),
                               n_grid=("grid_cd", "size"), n_grid_pop=(f"pop_pos_{py}", "sum"))
        a["year"] = y
        rows.append(a.reset_index().rename(columns={key: "unit_id"}))
    return pd.concat(rows, ignore_index=True)


# ---------- 3. 시설 ----------
def fac_panel(level):
    f = pd.read_parquet(FAC)
    f = f[f["분석가능"] & f.dong424.notna()].copy()
    key = UNIT_KEY[level]
    rows = []
    for y in YEARS:
        fy = f[f.year == y]
        a = fy[fy.cat_A != "control"].groupby([key, "cat_A"]).size().unstack(fill_value=0).add_prefix("fac_")
        a["fac_A_total"] = a.sum(axis=1)
        k = fy[fy["시설"].isin(KEYFAC)].groupby([key, "시설"]).size().unstack(fill_value=0).add_prefix("fac_")
        a = a.join(k, how="outer").fillna(0)
        a["year"] = y
        rows.append(a.reset_index().rename(columns={key: "unit_id"}))
    out = pd.concat(rows, ignore_index=True)
    return out


# ---------- 4. 국가 최저기준 ----------
def nat_panel(level):
    rows = []
    for y in YEARS:
        n = rcsv(ACC / f"결과/natstd_B/nat_standard_coverage_{y}_100.csv")
        n = n[n.unit_level == level]
        w = n.pivot_table(index="unit_id", columns="item", values="COV").add_prefix("nat_")
        w = w.rename(columns={"nat_종합(5개 단순평균)": "nat_종합"})
        w["year"] = y
        rows.append(w.reset_index())
    return pd.concat(rows, ignore_index=True)


# ---------- 5. 이동 ----------
def maps():
    lz = rcsv(CORE / "dong_to_official_livingzone_mapping_424.csv")
    l20 = rcsv(CORE / "dong_to_leiden_2020_mapping_424.csv")
    l25 = rcsv(CORE / "dong_to_leiden_2025_mapping_424.csv")
    m = lz[["Dong", "Ku", "ku_name", "ADM_NM", "life_zone_id", "life_zone_name"]].rename(
        columns={"Dong": "dong424", "Ku": "ku", "ADM_NM": "dong_name", "life_zone_id": "lz116"})
    m = m.merge(l20[["Dong", "global_community_id"]].rename(columns={"Dong": "dong424", "global_community_id": "ld2020"}), on="dong424")
    m = m.merge(l25[["Dong", "global_community_id"]].rename(columns={"Dong": "dong424", "global_community_id": "ld2025"}), on="dong424")
    # LD 소속 변화: 같은 LD 커뮤니티에 함께 묶인 동 집합이 두 해 사이 달라졌는가(Jaccard)
    def comembers(col):
        grp = m.groupby(col)["dong424"].apply(set)
        return m[col].map(grp)
    c20, c25 = comembers("ld2020"), comembers("ld2025")
    m["ld_jaccard"] = [len(a & b) / len(a | b) for a, b in zip(c20, c25)]
    m["ld_changed"] = m.ld_jaccard < 1.0
    # LZ vs LD 일치(2025): 동이 속한 LZ 생활권과 LD 커뮤니티의 동 구성이 같은가
    lzset = m.groupby("lz116")["dong424"].apply(set)
    m["lz_ld2025_same"] = [lzset[z] == c for z, c in zip(m.lz116, c25)]
    m["lz_ld2020_same"] = [lzset[z] == c for z, c in zip(m.lz116, c20)]
    return m


def mob_dong():
    m = maps()
    rows = []
    for y in YEARS:
        od = pd.read_parquet(CORE / f"od/od_daily_{y}01.parquet")
        ldcol = f"ld{y}"
        od = od.merge(m[["dong424", "lz116", ldcol, "ku"]].rename(columns={"dong424": "dong_O", "lz116": "lz_O", ldcol: "ld_O", "ku": "ku_O"}), on="dong_O")
        od = od.merge(m[["dong424", "lz116", ldcol, "ku"]].rename(columns={"dong424": "dong_D", "lz116": "lz_D", ldcol: "ld_D", "ku": "ku_D"}), on="dong_D")
        od["in_lz"] = od.lz_O == od.lz_D
        od["in_ld"] = od.ld_O == od.ld_D
        od["self"] = od.dong_O == od.dong_D
        od["in_ku"] = od.ku_O == od.ku_D
        g = od.groupby("dong_O").apply(lambda x: pd.Series({
            "mob_T": x.flow.sum(),
            "mob_N_lz": x.flow[x.in_lz].sum(), "mob_N_ld": x.flow[x.in_ld].sum(),
            "mob_a": x.flow[x.in_ld & ~x.in_lz].sum(), "mob_b": x.flow[x.in_lz & ~x.in_ld].sum(),
            "mob_self": x.flow[x["self"]].sum(), "mob_N_ku": x.flow[x.in_ku].sum()}), include_groups=False)
        g["mob_IFR_lz"] = g.mob_N_lz / g.mob_T
        g["mob_IFR_ld"] = g.mob_N_ld / g.mob_T
        g["mob_G"] = (g.mob_a - g.mob_b) / g.mob_T
        g["mob_D"] = (g.mob_a + g.mob_b) / g.mob_T
        g["mob_SR"] = g.mob_self / g.mob_T
        g["mob_KR"] = g.mob_N_ku / g.mob_T
        g["year"] = y
        rows.append(g.reset_index().rename(columns={"dong_O": "unit_id"}))
    return pd.concat(rows, ignore_index=True), m


def mob_ku():
    t = rcsv(KPA / "t02_gu_metrics_long.csv")
    t = t.rename(columns={"ku_code": "unit_id"})
    t = t[["unit_id", "year", "T", "a", "b", "IFR_lz", "IFR_ld", "G", "D", "SR"]].rename(columns=lambda c: c if c in ("unit_id", "year") else f"mob_{c}")
    return t


def mob_lz():
    t = rcsv(KPA / "t08_lz116_metrics.csv").rename(columns={"lz_O": "unit_id"})
    t = t[["unit_id", "year", "T", "a", "b", "IFR_lz", "IFR_ld", "G", "D", "SR"]].rename(columns=lambda c: c if c in ("unit_id", "year") else f"mob_{c}")
    return t


# ---------- 6. 결합 ----------
def build(level):
    a = access_panel(level)
    p = pop_panel(level)
    f = fac_panel(level)
    n = nat_panel(level)
    a["unit_id"] = a.unit_id.astype(int); p["unit_id"] = p.unit_id.astype(int); f["unit_id"] = f.unit_id.astype(int); n["unit_id"] = n.unit_id.astype(int)
    df = a.merge(p, on=["unit_id", "year"], how="left").merge(f, on=["unit_id", "year"], how="left").merge(n, on=["unit_id", "year"], how="left")
    if level == "ku":
        mob = mob_ku()
    elif level == "lz116":
        mob = mob_lz()
    else:
        mob, m = mob_dong()
        df = df.merge(m[["dong424", "ku", "ku_name", "dong_name", "lz116", "ld2020", "ld2025", "ld_jaccard", "ld_changed", "lz_ld2020_same", "lz_ld2025_same"]]
                      .rename(columns={"dong424": "unit_id"}), on="unit_id", how="left")
    df = df.merge(mob, on=["unit_id", "year"], how="left")
    fac_cols = [c for c in df.columns if c.startswith("fac_")]
    df[fac_cols] = df[fac_cols].fillna(0)
    return df


def names(level):
    m = maps()
    if level == "ku":
        return m.drop_duplicates("ku")[["ku", "ku_name"]].rename(columns={"ku": "unit_id", "ku_name": "name"})
    if level == "lz116":
        return m.drop_duplicates("lz116")[["lz116", "life_zone_name", "ku", "ku_name"]].rename(columns={"lz116": "unit_id", "life_zone_name": "name"})
    return m[["dong424", "dong_name"]].rename(columns={"dong424": "unit_id", "dong_name": "name"})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    src = {
        "access_main_2020": ACC / "결과/main/unit_access_2020_100.csv", "access_main_2025": ACC / "결과/main/unit_access_2025_100.csv",
        "access_net2025": ACC / "결과/sens_net2025/unit_access_2020_100.csv",
        "natstd_2020": ACC / "결과/natstd_B/nat_standard_coverage_2020_100.csv", "natstd_2025": ACC / "결과/natstd_B/nat_standard_coverage_2025_100.csv",
        "grid100_master": GRID, "facility_units": FAC,
        "od_2020": CORE / "od/od_daily_202001.parquet", "od_2025": CORE / "od/od_daily_202501.parquet",
        "map_lz": CORE / "dong_to_official_livingzone_mapping_424.csv", "map_ld2020": CORE / "dong_to_leiden_2020_mapping_424.csv", "map_ld2025": CORE / "dong_to_leiden_2025_mapping_424.csv",
        "kpa_t02_long": KPA / "t02_gu_metrics_long.csv", "kpa_t08_lz": KPA / "t08_lz116_metrics.csv", "kpa_t06_selection": KPA / "t06_selection.csv", "kpa_t09_ari": KPA / "t09_ari_ld20_ld25.csv",
    }
    manifest = {k: {"path": str(v.relative_to(ROOT)), "sha256_16": sha(v)} for k, v in src.items()}
    (OUT / "sources_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    for level in ["ku", "lz116", "dong424"]:
        df = build(level)
        nm = names(level)
        df = nm.merge(df, on="unit_id", how="right") if level != "dong424" else df
        df.to_csv(OUT / f"panel_{level}.csv", index=False, encoding="utf-8-sig")
        print(level, df.shape, "결측 접근성:", df["acc_COV_lz116_종합"].isna().sum())
    print("완료")
