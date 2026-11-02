"""Every number used anywhere (data/results.json), the reusable data tables (data/*.csv, data/*.csv.gz) and the page
data (data/site.json).

Definitions:
  * town: a GeoNames cities1000 place (1,000 or more people, plus a few smaller administrative seats that GeoNames keeps,
    such as the capitals of tiny island territories);
  * city of 100,000+ and city of a million: Natural Earth populated places with pop_max at or above the threshold;
  * coast: the outline of the Natural Earth 1:50m land (lakes are land; the Caspian Sea is sea);
  * world land: Natural Earth land outside Antarctica, area weighted (Antarctica is reported on its own because its
    research stations are not in the gazetteer, so every Antarctic distance is to a town on another continent);
  * mainland: the connected land mass of a continent (8-connected cells of the 0.1 degree grid, joined across 180 degrees),
    found from a reference point; Europe and Asia share the Eurasian mass and are split by Natural Earth country, with
    Russia east of 60 E in Asia;
  * most remote point of a country: the point inside its Natural Earth 1:10m outline farthest from any town, in that
    country or not. Found on the 0.1 degree grid and refined on a 0.01 degree grid inside the outline.
All maxima are refined to 0.01 degrees (about 1 km), so positions are good to about a kilometre and distances to a
kilometre or two. Distances are great-circle distances on a sphere of radius 6,371 km."""
import numpy as np, pandas as pd
import shapely
from shapely.geometry import shape
from scipy.spatial import cKDTree
from scipy import ndimage
from common import *

G = dict(np.load(f"{WORK}/grid.npz"))
T = pd.read_pickle(f"{WORK}/towns.pkl"); C = pd.read_pickle(f"{WORK}/cities.pkl")
CT = pd.read_pickle(f"{WORK}/countries_meta.pkl"); CG = pd.read_pickle(f"{WORK}/countries_geom.pkl")
CHK = jload(f"{WORK}/checks.json")
CO = np.load(f"{WORK}/coast.npy")
lat, lon = GRID_LAT[G["J"]], GRID_LON[G["I"]]
A = G["area"].astype(float); cont = G["cont"]; cid = G["cid"]
D = {k: G["d_" + k].astype(float) for k in MKEYS}
ANT = cont == CONTINENTS.index("Antarctica")
WL = ~ANT                                                     # world land outside Antarctica
C1, C2 = C[C["pop"] >= 1e5].reset_index(drop=True), C[C["pop"] >= 1e6].reset_index(drop=True)
TREE = {"town": cKDTree(unit(T.lat, T.lon)), "c100k": cKDTree(unit(C1.lat, C1.lon)), "c1m": cKDTree(unit(C2.lat, C2.lon)), "coast": cKDTree(unit(CO[:, 1], CO[:, 0]))}
ISO2NAME = {r.iso2: r.name for r in CT.itertuples() if r.kind in ("country", "territory", "antarctica")}
ISO2NAME.update({"SJ": "Svalbard (Norway)", "TF": "French Southern Lands", "GS": "South Georgia", "XK": "Kosovo", "PS": "Palestine", "EH": "Western Sahara",
                 "BQ": "Caribbean Netherlands", "GF": "French Guiana", "GP": "Guadeloupe", "MQ": "Martinique", "RE": "Reunion", "YT": "Mayotte",
                 "TK": "Tokelau", "CX": "Christmas Island", "CC": "Cocos Islands", "NO": "Norway", "FR": "France", "SH": "Saint Helena"})
LANDU = shapely.union_all([shape(f["geometry"]) for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]]); shapely.prepare(LANDU)
pc = lambda a, b: round(100 * float(a) / float(b), 2) if b else None
R = {}


def near(la, lo):
    """Distances (km) from one point to the nearest town, cities and coast, with the nearest town and cities named."""
    u = unit([la], [lo]); out = {}
    for k in MKEYS:
        d, i = TREE[k].query(u); out[k] = round(float(chord_km(d[0])), 1); out[k + "_i"] = int(i[0])
    t = T.iloc[out["town_i"]]; out["town_name"] = t["name"]; out["town_cc"] = t.country; out["town_country"] = ISO2NAME.get(t.country, t.country)
    out["town_lat"], out["town_lon"] = round(float(t.lat), 4), round(float(t.lon), 4)
    for k, df in (("c100k", C1), ("c1m", C2)):
        c = df.iloc[out[k + "_i"]]; out[k + "_name"] = c["name"]; out[k + "_country"] = c.country; out[k + "_pop"] = int(c["pop"])
        out[k + "_lat"], out[k + "_lon"] = round(float(c.lat), 3), round(float(c.lon), 3)
    for k in MKEYS: out.pop(k + "_i")
    return out


def dists(key, la, lo):
    d, _ = TREE[key].query(unit(la, lo), workers=-1)
    return chord_km(d)


def refine(seeds, key, geom=None, half=RES, step=FINE):
    """Best point for `key` on a fine grid around each seed (lat, lon), kept inside geom (prepared) or on land."""
    best = (-1, None, None)
    off = np.arange(-half, half + step / 2, step)
    for la0, lo0 in seeds:
        la, lo = np.meshgrid(la0 + off, lo0 + off, indexing="ij"); la, lo = la.ravel(), lo.ravel()
        ok = (np.abs(la) < 90) & (np.abs(lo) <= 180)
        la, lo = la[ok], lo[ok]
        ins = shapely.contains_xy(geom if geom is not None else LANDU, lo, la)
        if not ins.any(): continue
        la, lo = la[ins], lo[ins]; d = dists(key, la, lo); k = int(np.argmax(d))
        if d[k] > best[0]: best = (float(d[k]), float(la[k]), float(lo[k]))
    return best


def point(key, mask, geom=None, nseed=6):
    """Most remote point for `key` among grid cells in mask, refined. Returns a dict with all four distances."""
    ix = np.where(mask)[0]
    if not len(ix): return None
    top = ix[np.argsort(-D[key][ix])[:nseed]]
    d, la, lo = refine([(lat[i], lon[i]) for i in top], key, geom)
    if la is None:
        i = top[0]; d, la, lo = float(D[key][i]), float(lat[i]), float(lon[i])
    o = {"lat": round(la, 3), "lon": round(lo, 3), "d": round(d, 1), "grid_d": round(float(D[key][top[0]]), 1)}
    o.update(near(la, lo)); o["country"] = country_at(la, lo)
    return o


CGEOM = {r.k: r.geom for r in CG.itertuples()}
for g in CGEOM.values(): shapely.prepare(g)
_ctree = None


def country_at(la, lo):
    for k, g in CGEOM.items():
        if shapely.contains_xy(g, lo, la): return CT.name[k]
    j, i = int((90 - la) / RES), int((lo + 180) / RES)
    for r in range(0, 6):
        w = CIDR[max(0, j - r):j + r + 1, max(0, i - r):i + r + 1]; w = w[w >= 0]
        if len(w): return CT.name[int(np.bincount(w).argmax())]
    return None


# ---------- source ----------
R["source"] = {"towns": CHK["towns"], "towns_rows": CHK["towns_rows"], "towns_south_60": CHK["towns_south_of_60s"], "commit": CHK["commit"],
               "ne_places": CHK["ne_places"], "c100k": CHK["c100k"], "c1m": CHK["c1m"], "coast_points": CHK["coast_points"],
               "land_cells": CHK["land_cells"], "edge_cells_exact": CHK["edge_cells_exact"], "land_agree_pct": CHK["land_raster_agree_pct"],
               "res": RES, "fine": FINE, "radius_km": RE_KM, "n_countries": None, "n_territories": None,
               "town_countries": int(T.country.nunique())}
assert R["source"]["towns_south_60"] == 0      # no town in Antarctica: the reason it is treated separately

# ---------- land and shares ----------
land_all, land_w, land_ant = A.sum(), A[WL].sum(), A[ANT].sum()
R["land"] = {"km2": round(land_all), "world_km2": round(land_w), "ant_km2": round(land_ant), "world_m": round(land_w / 1e6, 1), "ant_pct_of_all": pc(land_ant, land_all)}
SH = {}
for k in MKEYS:
    s = {}
    for t in (10, 25, 50, 100, 250, 500, 1000, 2000):
        s[str(t)] = pc(A[WL & (D[k] > t)].sum(), land_w)
        s[f"{t}_km2"] = round(float(A[WL & (D[k] > t)].sum()))
        s[f"ant_{t}"] = pc(A[ANT & (D[k] > t)].sum(), land_ant)
    s["median"] = round(float(np.interp(.5, np.cumsum(A[WL][np.argsort(D[k][WL])]) / land_w, np.sort(D[k][WL]))), 1)
    s["mean"] = round(float((D[k][WL] * A[WL]).sum() / land_w), 1)
    s["ant_median"] = round(float(np.interp(.5, np.cumsum(A[ANT][np.argsort(D[k][ANT])]) / land_ant, np.sort(D[k][ANT]))), 1)
    s["ant_min"] = round(float(D[k][ANT].min()), 1)
    SH[k] = s
R["share"] = SH
sh = SH["town"]
sh["100_m"] = round(sh["100_km2"] / 1e6, 1); sh["500_m"] = round(sh["500_km2"] / 1e6, 2)
sh["within10"] = round(100 - sh["10"], 1); sh["within25"] = round(100 - sh["25"], 1)
# cumulative curves for the chart: share of world land within d km, d from 1 to 6,000 km on a log-spaced ladder
dd = np.unique(np.r_[np.round(np.geomspace(1, 6000, 160)), [10, 25, 50, 100, 250, 500, 1000]]).astype(int)
srt = {k: np.argsort(D[k][WL]) for k in MKEYS}
R["cum"] = {"d": dd.tolist(), **{k: np.round(100 * np.interp(dd, D[k][WL][srt[k]], np.cumsum(A[WL][srt[k]])) / land_w, 2).tolist() for k in MKEYS}}
# latitude bands, 5 degrees, world land outside Antarctica: share beyond 100 km of a town
bands = []
for b in range(-60, 85, 5):
    m = WL & (lat >= b) & (lat < b + 5)
    if A[m].sum() < 1e4: continue
    bands.append({"b": b, "km2": round(float(A[m].sum())), "far100": pc(A[m & (D["town"] > 100)].sum(), A[m].sum()), "far500": pc(A[m & (D["town"] > 500)].sum(), A[m].sum()),
                  "far1m_1000": pc(A[m & (D["c1m"] > 1000)].sum(), A[m].sum())})
R["bands"] = bands
north60 = WL & (lat >= 60)
R["north"] = {"far100_share_north60": pc(A[north60 & (D["town"] > 100)].sum(), A[WL & (D["town"] > 100)].sum()),
              "north60_land_pct": pc(A[north60].sum(), land_w),
              "far500_share_north60": pc(A[north60 & (D["town"] > 500)].sum(), A[WL & (D["town"] > 500)].sum())}

# ---------- land masses: continents' mainlands and the big islands ----------
COMP = G["pid"]                                          # Natural Earth 1:50m land polygon of each cell
comp_area = pd.Series(A).groupby(COMP).sum()
PIDR = np.full((NY, NX), -1, np.int32); PIDR[G["J"], G["I"]] = COMP
CIDR = np.full((NY, NX), -1, np.int32); CIDR[G["J"], G["I"]] = cid
def comp_at(la, lo):
    v = PIDR[int((90 - la) / RES), int((lo + 180) / RES)]
    assert v >= 0, (la, lo); return v
MAIN = {"Africa": (5, 20), "Asia": (50, 90), "Europe": (50, 90), "North America": (45, -100), "South America": (-10, -60),
        "Australia and Oceania": (-25, 134), "Antarctica": (-80, 0)}
MAINNAME = {"Africa": "mainland Africa", "Asia": "mainland Asia", "Europe": "mainland Europe", "North America": "mainland North America",
            "South America": "mainland South America", "Australia and Oceania": "mainland Australia", "Antarctica": "Antarctica"}
cont_rows = []
for ci, cn in enumerate(CONTINENTS):
    cmp = comp_at(*MAIN[cn]); m = (COMP == cmp) & (cont == ci)
    row = {"continent": cn, "mainland": MAINNAME[cn], "km2": round(float(A[m].sum())), "all_km2": round(float(A[cont == ci].sum()))}
    for k in MKEYS:
        row[k] = point(k, m)
    row["any"] = point("town", cont == ci)            # including islands
    row["far100"] = pc(A[m & (D["town"] > 100)].sum(), A[m].sum())
    cont_rows.append(row)
R["continents"] = {r["continent"]: r for r in cont_rows}; R["continents_list"] = cont_rows
CN = R["continents"]
assert 15e6 < CN["Africa"]["km2"] < 32e6 and 7e6 < CN["Australia and Oceania"]["km2"] < 8.2e6 and 15e6 < CN["South America"]["km2"] < 19e6

ISL = [("Greenland", (72, -40)), ("New Guinea", (-5, 142)), ("Borneo", (1, 114)), ("Madagascar", (-19, 47)), ("Baffin Island", (68, -70)),
       ("Sumatra", (0, 102)), ("Honshu", (36.5, 138.5)), ("Victoria Island", (71, -110)), ("Great Britain", (54, -2)), ("Ellesmere Island", (80, -80)),
       ("Sulawesi", (-2, 121)), ("South Island, New Zealand", (-44, 170.5)), ("Iceland", (65, -18)), ("Ireland", (53, -8)), ("Tasmania", (-42, 146.5))]
isl = []
for nm, ref in ISL:
    cmp = comp_at(*ref); m = COMP == cmp
    p = point("town", m); p.update({"island": nm, "km2": round(float(A[m].sum())), "far100": pc(A[m & (D["town"] > 100)].sum(), A[m].sum())})
    isl.append(p)
R["islands"] = sorted(isl, key=lambda r: -r["d"])
IS = {r["island"]: r for r in isl}
assert 1.9e6 < IS["Greenland"]["km2"] < 2.3e6 and 1.8e5 < IS["Great Britain"]["km2"] < 2.6e5 and 1.6e5 < IS["Ellesmere Island"]["km2"] < 3e5 \
    and 3.4e5 < IS["Baffin Island"]["km2"] < 5.6e5 and 5e4 < IS["Tasmania"]["km2"] < 9e4 and IS["Iceland"]["km2"] < 1.2e5

# ---------- global maxima ----------
GL = {}
for k in MKEYS:
    GL[k] = {"world": point(k, WL), "ant": point(k, ANT)}
R["global"] = GL
# the most remote scraps of land outside Antarctica (one per 300 km), by distance to a town
o = np.argsort(-D["town"]); seen = []
for ix in o:
    if ANT[ix]: continue
    if any(gc_km(lat[ix], lon[ix], a, b) < 300 for a, b in seen): continue
    seen.append((lat[ix], lon[ix]))
    if len(seen) >= 12: break
scraps = []
for la0, lo0 in seen:
    m = WL & (np.abs(lat - la0) < 3) & (gc_km(lat, lon, la0, lo0) < 150)
    p = point("town", m); p["comp_km2"] = round(float(comp_area[COMP[np.where(m)[0][0]]])); scraps.append(p)
R["scraps"] = sorted(scraps, key=lambda r: -r["d"])
SC = R["scraps"]
# named after checking positions: Marion Island (Prince Edward Islands, South Africa) and the Crozet Islands (France)
assert -47.2 < SC[0]["lat"] < -46.6 and 37.4 < SC[0]["lon"] < 38.1 and SC[0]["country"] == "South Africa"
assert -46.6 < SC[1]["lat"] < -45.9 and 50 < SC[1]["lon"] < 52.5 and SC[1]["country"] == "French Southern Lands"
SC[0]["place"] = "Marion Island (Prince Edward Islands)"; SC[1]["place"] = "the Crozet Islands"
for p in SC[2:]:
    if 82.9 < p["lat"] < 83.3 and -70.5 < p["lon"] < -69.3: p["place"] = "Cape Columbia, the northern tip of Ellesmere Island"
    elif p["country"] == "Greenland" and p["lat"] > 82.5: p["place"] = "the north coast of Greenland"
    elif p["country"] == "Russia" and 79.8 < p["lat"] < 82 and 44 < p["lon"] < 66: p["place"] = "Franz Josef Land"
    elif p["country"] == "United States" and 51 < p["lat"] < 53 and (p["lon"] > 172 or p["lon"] < -165): p["place"] = "the western Aleutian Islands"
assert sum("place" in p for p in SC) >= 6, [(p["lat"], p["lon"], p["country"]) for p in SC]
assert GL["town"]["world"]["d"] == SC[0]["d"]

# ---------- Antarctica ----------
an = GL["town"]["ant"]
R["antarctica"] = {"km2": round(land_ant), "min_town": SH["town"]["ant_min"], "median_town": SH["town"]["ant_median"],
                   "far1000_pct": SH["town"]["ant_1000"], "far2000_pct": SH["town"]["ant_2000"], "max": an, "coast_pole": GL["coast"]["ant"],
                   "far500_pct": SH["town"]["ant_500"]}
assert R["antarctica"]["min_town"] > 500

# ---------- the far-from-the-sea pole (Eurasia) and the famous candidates ----------
ep = GL["coast"]["world"]
ref = near(*EURASIA_POLE)
R["eurasia"] = {"ours": ep, "ref_lat": EURASIA_POLE[0], "ref_lon": EURASIA_POLE[1], "ref_coast": ref["coast"], "ref_town": ref["town"], "ref_town_name": ref["town_name"],
                "ref_town_country": ref["town_country"], "sep_km": round(float(gc_km(ep["lat"], ep["lon"], *EURASIA_POLE)), 1),
                "ref_c1m": ref["c1m"], "ref_c1m_name": ref["c1m_name"], "ours_town": ep["town"], "ours_town_name": ep["town_name"]}
assert ep["country"] == "China" and R["eurasia"]["sep_km"] < 250 and ep["d"] > R["eurasia"]["ref_coast"]
cand = []
for nm, how, arg, key in CANDIDATES:
    if how == "box":
        x0, y0, x1, y1 = arg; m = WL & (lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1)
    elif how == "iso":
        ks = CT.index[CT.iso == arg].tolist(); m = np.isin(cid, ks)
    else:
        (x0, y0, x1, y1), iso = arg; ks = CT.index[CT.iso == iso].tolist(); m = np.isin(cid, ks) & (lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1)
    if nm.startswith("Australian"): m = m & (COMP == comp_at(-25, 134))
    if nm.startswith("Siberia"): m = m & (COMP == comp_at(50, 90))
    p = point(key, m); p["name"] = nm; p["far100"] = pc(A[m & (D["town"] > 100)].sum(), A[m].sum()); p["km2"] = round(float(A[m].sum()))
    cand.append(p)
R["candidates"] = cand
CA = {c["name"]: c for c in cand}
R["cand"] = {c["name"].split(" (")[0].split("'s ")[-1].replace("'", ""): c for c in cand}
R["isl"] = {p["island"].split(",")[0]: p for p in R["islands"]}

# ---------- countries and territories ----------
crow = []
for r in CT.itertuples():
    if r.kind in ("skip", "antarctica"): continue
    g = CGEOM[r.k]; m = cid == r.k
    p = None
    if m.sum() >= 3:
        p = point("town", m, geom=g, nseed=8)
        if p is not None and p["lat"] is None: p = None
    if p is None or not shapely.contains_xy(g, p["lon"], p["lat"]):      # small places: a fine grid over the outline
        x0, y0, x1, y1 = g.bounds; st = max(.002, min(.02, np.sqrt((x1 - x0) * (y1 - y0) / 4e5)))
        lo_, la_ = np.meshgrid(np.arange(x0, x1 + st, st), np.arange(y0, y1 + st, st)); lo_, la_ = lo_.ravel(), la_.ravel()
        ins = shapely.contains_xy(g, lo_, la_)
        if not ins.any():
            c = g.representative_point(); lo_, la_ = np.array([c.x]), np.array([c.y])
        else: lo_, la_ = lo_[ins], la_[ins]
        d = dists("town", la_, lo_); i = int(np.argmax(d))
        p = {"lat": round(float(la_[i]), 3), "lon": round(float(lo_[i]), 3), "d": round(float(d[i]), 1), "grid_d": None}
        p.update(near(float(la_[i]), float(lo_[i]))); p["country"] = r.name
    mp = max(g.geoms, key=lambda q: q.area) if g.geom_type == "MultiPolygon" else g
    q = None
    if mp is not g and m.sum() >= 3:
        shapely.prepare(mp); mm = m.copy(); mm[m] = shapely.contains_xy(mp, lon[m], lat[m])
        if mm.sum() >= 3: q = point("town", mm, geom=mp, nseed=8)
    p["main"] = {k: q[k] for k in ("lat", "lon", "d", "town_name", "town_country")} if q is not None and q["lat"] is not None else {k: p[k] for k in ("lat", "lon", "d", "town_name", "town_country")}
    p["main_d"] = p["main"]["d"]
    a = float(A[m].sum())
    p.update({"name": r.name, "iso": r.iso, "kind": r.kind, "continent": r.continent if isinstance(r.continent, str) else "Open ocean islands",
              "sov": r.sov, "km2": round(a), "far100": pc(A[m & (D["town"] > 100)].sum(), a) if a else None,
              "far25": pc(A[m & (D["town"] > 25)].sum(), a) if a else None,
              "mean_town": round(float((D["town"][m] * A[m]).sum() / a), 1) if a else None,
              "abroad": p["town_cc"] != r.iso2})
    crow.append(p)
CR = pd.DataFrame(crow)
assert CR.name.is_unique
R["source"]["n_countries"] = int((CR.kind == "country").sum()); R["source"]["n_territories"] = int((CR.kind == "territory").sum())
cc = CR[CR.kind == "country"].sort_values("d", ascending=False)
R["countries_top"] = [{"name": x.name, "d": x.d, "lat": x.lat, "lon": x.lon, "town": x.town_name, "town_country": x.town_country} for x in cc.head(25).itertuples()]
cm = cc[cc.km2 >= 1e5].sort_values("main_d", ascending=False)
R["countries_main_top"] = [{"name": x.name, "d": x.main_d, "lat": x.main["lat"], "lon": x.main["lon"], "town": x.main["town_name"], "town_country": x.main["town_country"],
                            "any_d": x.d} for x in cm.head(25).itertuples()]
R["countries_bottom"] = [{"name": x.name, "d": x.d, "town": x.town_name} for x in cc.tail(12).itertuples()]
tt = CR[CR.kind == "territory"].sort_values("d", ascending=False)
R["territories_top"] = [{"name": x.name, "d": x.d, "town": x.town_name, "town_country": x.town_country} for x in tt.head(10).itertuples()]
R["countries"] = {x["name"]: x for x in crow}
R["n_abroad"] = int(cc.abroad.sum())
R["countries_far100_top"] = [{"name": x.name, "far100": x.far100, "km2": x.km2} for x in cc[cc.km2 > 2e5].sort_values("far100", ascending=False).head(12).itertuples()]
R["countries_under10"] = int((cc.d < 10).sum()); R["countries_under25"] = int((cc.d < 25).sum())
R["countries_median_d"] = round(float(cc.d.median()), 1)
K = R["countries"]

# ---------- the United Kingdom ----------
A1 = [f for f in jload(f"{GEO}/ne_10m_admin_1_states_provinces.geojson")["features"] if f["properties"]["adm0_a3"] == "GBR"]
NAT = {n: shapely.union_all([shape(f["geometry"]) for f in A1 if f["properties"]["geonunit"] == n]) for n in UK_NATIONS}
UNIT = [(f["properties"]["name"], f["properties"]["geonunit"], shape(f["geometry"])) for f in A1]
for _, _, g in UNIT: shapely.prepare(g)
GB = shapely.union_all([NAT[n] for n in ("England", "Scotland", "Wales")])
GBM = max(GB.geoms, key=lambda q: q.area)               # the island of Great Britain
NIM = max(NAT["Northern Ireland"].geoms, key=lambda q: q.area) if NAT["Northern Ireland"].geom_type == "MultiPolygon" else NAT["Northern Ireland"]
def unit_at(la, lo):
    for nm, nat, g in UNIT:
        if shapely.contains_xy(g, lo, la): return UNIT_FIX.get(nm, nm), nat
    return None, None
UNIT_FIX = {"Perthshire and Kinross": "Perth and Kinross", "North Ayshire": "North Ayrshire"}   # Natural Earth spellings
UKST = .005
def uk_grid(geom):
    shapely.prepare(geom); x0, y0, x1, y1 = geom.bounds
    lo_, la_ = np.meshgrid(np.arange(x0, x1, UKST), np.arange(y0, y1, UKST)); lo_, la_ = lo_.ravel(), la_.ravel()
    ins = shapely.contains_xy(geom, lo_, la_); return la_[ins], lo_[ins]
def uk_pt(la, lo, d):
    p = {"lat": round(float(la), 3), "lon": round(float(lo), 3), "d": round(float(d), 1)}; p.update(near(float(la), float(lo)))
    p["unit"], p["nation"] = unit_at(la, lo); return p
uk = {}
GBla, GBlo = uk_grid(GBM); GBd = dists("town", GBla, GBlo)
R["uk_grid_points"] = int(len(GBla))
for n in UK_NATIONS:
    if n == "Northern Ireland":
        la_, lo_ = uk_grid(NIM); d = dists("town", la_, lo_)
    else:
        g = NAT[n]; shapely.prepare(g); ins = shapely.contains_xy(g, GBlo, GBla); la_, lo_, d = GBla[ins], GBlo[ins], GBd[ins]
    i = int(np.argmax(d)); uk[n] = uk_pt(la_[i], lo_[i], d[i])
    la2, lo2 = uk_grid(NAT[n]); d2 = dists("town", la2, lo2); i2 = int(np.argmax(d2)); uk[n]["with_islands"] = uk_pt(la2[i2], lo2[i2], d2[i2])
    uk[n]["far10"] = pc((d > 10).sum(), len(d)); uk[n]["far20"] = pc((d > 20).sum(), len(d))
hi = [g for nm, nat, g in UNIT if nm == "Highland"][0]; ins = shapely.contains_xy(hi, GBlo, GBla)
i = int(np.argmax(GBd[ins])); R["highland"] = uk_pt(GBla[ins][i], GBlo[ins][i], GBd[ins][i])
# the most remote spots on the island of Great Britain, at least 30 km apart
order = np.argsort(-GBd); spots = []
for i in order:
    if any(gc_km(GBla[i], GBlo[i], s["lat"], s["lon"]) < 30 for s in spots): continue
    spots.append(uk_pt(GBla[i], GBlo[i], GBd[i]))
    if len(spots) >= 10: break
R["uk"] = uk; R["gb_spots"] = spots
R["gb"] = {"far10": pc((GBd > 10).sum(), len(GBd)), "far20": pc((GBd > 20).sum(), len(GBd)), "far5": pc((GBd > 5).sum(), len(GBd)),
           "median": round(float(np.median(GBd)), 1), "max": round(float(GBd.max()), 1)}
U = R["uk"]
assert U["Scotland"]["nation"] == "Scotland" and U["Scotland"]["d"] == R["highland"]["d"] == spots[0]["d"]

# ---------- clean data out ----------
CR["main_lat"] = [m["lat"] for m in CR.main]; CR["main_lon"] = [m["lon"] for m in CR.main]; CR["main_town"] = [m["town_name"] for m in CR.main]
out = CR[["name", "iso", "kind", "continent", "sov", "km2", "lat", "lon", "d", "main_lat", "main_lon", "main_d", "main_town", "town_name", "town_country", "town_lat", "town_lon", "coast", "c100k", "c100k_name", "c1m", "c1m_name", "far25", "far100", "mean_town"]]
out.rename(columns={"name": "country_or_territory", "iso": "iso_a3", "km2": "land_km2_grid", "lat": "remote_lat", "lon": "remote_lon", "d": "km_to_nearest_town",
                    "town_name": "nearest_town", "town_country": "nearest_town_country", "coast": "km_to_coast", "c100k": "km_to_city_100k", "c100k_name": "nearest_city_100k",
                    "c1m": "km_to_city_1m", "c1m_name": "nearest_city_1m", "far25": "pct_land_over_25km_from_town", "far100": "pct_land_over_100km_from_town",
                    "mean_town": "mean_km_to_town", "main_lat": "main_landmass_remote_lat", "main_lon": "main_landmass_remote_lon",
                    "main_d": "main_landmass_km_to_nearest_town", "main_town": "main_landmass_nearest_town"}).sort_values("km_to_nearest_town", ascending=False).to_csv(f"{DATA}/country_remote_points.csv", index=False)
rows = []
for r in cont_rows:
    for k in MKEYS + ["any"]:
        p = r[k]; rows.append({"continent": r["continent"], "land": r["mainland"] if k != "any" else "continent with its islands", "measure": k if k != "any" else "town",
                               "lat": p["lat"], "lon": p["lon"], "km": p["d"], "nearest_town": p["town_name"], "nearest_town_country": p["town_country"], "country": p["country"]})
pd.DataFrame(rows).to_csv(f"{DATA}/continent_poles.csv", index=False)
pd.DataFrame([{"island": p["island"], "km2": p["km2"], "lat": p["lat"], "lon": p["lon"], "km_to_town": p["d"], "nearest_town": p["town_name"], "pct_over_100km": p["far100"]} for p in R["islands"]]).to_csv(f"{DATA}/islands.csv", index=False)
pd.DataFrame([{"name": p["name"], "lat": p["lat"], "lon": p["lon"], "km_to_town": p["d"], "nearest_town": p["town_name"], "nearest_town_country": p["town_country"], "km_to_coast": p["coast"],
               "km_to_city_1m": p["c1m"], "pct_over_100km": p["far100"]} for p in cand]).to_csv(f"{DATA}/famous_candidates.csv", index=False)
uko = [dict(spot=i + 1, **{k: s[k] for k in ("lat", "lon", "d", "nation", "unit", "town_name", "coast")}) for i, s in enumerate(spots)]
pd.DataFrame(uko).rename(columns={"d": "km_to_town", "unit": "council_area", "town_name": "nearest_town", "coast": "km_to_coast"}).to_csv(f"{DATA}/gb_remote_spots.csv", index=False)
pd.DataFrame({"km": dd, **{f"pct_land_within_{k}": R["cum"][k] for k in MKEYS}}).to_csv(f"{DATA}/land_share_by_distance.csv", index=False)
gz = pd.DataFrame({"lat": np.round(lat, 2), "lon": np.round(lon, 2), "cell_km2": np.round(A, 2), **{f"km_to_{k}": np.round(D[k]).astype(int) for k in MKEYS},
                   "continent": np.array(CONTINENTS + ["none"])[cont], "country": CT.name.values[cid]})
gz.to_csv(f"{DATA}/land_distances_0p1deg.csv.gz", index=False, compression="gzip")

# ---------- page data ----------
keep = ["lat", "lon", "d", "town_name", "town_country", "town_lat", "town_lon", "coast", "c100k", "c100k_name", "c1m", "c1m_name", "country"]
sp = lambda p: {k: p[k] for k in keep if k in p}
site = {"measures": MEASURES, "continents": [{"c": r["continent"], "m": r["mainland"], "km2": r["km2"], **{k: sp(r[k]) for k in MKEYS}, "any": sp(r["any"])} for r in cont_rows],
        "countries": [[x.name, x.iso, x.kind, x.continent, x.lat, x.lon, x.d, x.town_name, x.town_country, x.town_lat, x.town_lon, x.coast, x.c100k, x.c100k_name,
                       x.c1m, x.c1m_name, x.far100, x.km2, x.mean_town, x.far25, x.main["lat"], x.main["lon"], x.main_d, x.main["town_name"], x.main["town_country"]] for x in CR.sort_values("name").itertuples()],
        "islands": [{"n": p["island"], **sp(p), "km2": p["km2"]} for p in R["islands"]], "scraps": [sp(p) | {"place": p.get("place")} for p in R["scraps"]],
        "cands": [{"n": p["name"], **sp(p)} for p in cand], "uk": [sp(s) | {"nation": s["nation"], "unit": s["unit"]} for s in spots],
        "uknat": {n: sp(U[n]) | {"unit": U[n]["unit"]} for n in UK_NATIONS},
        "global": {k: {"world": sp(GL[k]["world"]), "ant": sp(GL[k]["ant"])} for k in MKEYS}, "eurasia": EURASIA_POLE}
jsave(site, f"{DATA}/site.json")
R["meta"] = {"page": PAGE, "repo": REPO, "doi": DOI, "blog": BLOG, "slug": SLUG}
jsave(R, f"{DATA}/results.json", indent=1)
print("results ok", {k: os.path.getsize(f"{DATA}/{k}") // 1024 for k in ("site.json", "results.json", "land_distances_0p1deg.csv.gz")})
print("share", {k: (SH[k]["100"], SH[k]["500"], SH[k]["median"]) for k in MKEYS}, R["north"])
for r in cont_rows: print(r["continent"], {k: (r[k]["d"], r[k]["lat"], r[k]["lon"], r[k]["town_name"], r[k]["country"]) for k in MKEYS}, "any", r["any"]["d"], r["any"]["country"])
for p in R["islands"]: print("island", p["island"], p["d"], p["lat"], p["lon"], p["town_name"], p["far100"])
for p in R["scraps"]: print("scrap", p["d"], p["lat"], p["lon"], p["country"], p["town_name"], p["comp_km2"])
for p in cand: print("cand", p["name"], p["d"], p["lat"], p["lon"], p["town_name"], p["town_country"], p["far100"])
print("eurasia", R["eurasia"])
print("antarctica", {k: v for k, v in R["antarctica"].items() if k not in ("max", "coast_pole")}, an["lat"], an["lon"], an["town_name"], an["town_country"], GL["coast"]["ant"]["d"], GL["coast"]["ant"]["lat"], GL["coast"]["ant"]["lon"])
for k in MKEYS: print("global", k, GL[k]["world"]["d"], GL[k]["world"]["lat"], GL[k]["world"]["lon"], GL[k]["world"]["country"], GL[k]["world"]["town_name"])
print("main top", [(x["name"], x["d"], x["lat"], x["lon"], x["town"], x["town_country"]) for x in R["countries_main_top"]])
print("top countries", [(x["name"], x["d"], x["town"], x["town_country"]) for x in R["countries_top"]])
print("bottom", R["countries_bottom"]); print("territories", R["territories_top"]); print("abroad", R["n_abroad"], "under10", R["countries_under10"], "median", R["countries_median_d"])
print("far100 top", R["countries_far100_top"])
for n in UK_NATIONS: print("UK", n, U[n]["d"], U[n]["lat"], U[n]["lon"], U[n]["unit"], U[n]["town_name"], "| islands", U[n]["with_islands"]["d"], U[n]["with_islands"]["lat"], U[n]["with_islands"]["lon"], U[n]["with_islands"]["unit"], U[n]["with_islands"]["town_name"], U[n]["far10"])
for s in spots: print("GB", s["d"], s["lat"], s["lon"], s["unit"], s["town_name"])
print("gb", R["gb"])
