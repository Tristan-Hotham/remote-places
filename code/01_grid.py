"""Read the gazetteers and outlines, lay the 0.1 degree grid over the land, and measure from every land cell the
great-circle distance to the nearest town (1,000+), city of 100,000+, city of 1,000,000+ and coast.

Outputs (in WORK, not in the repo): towns.pkl, cities.pkl, coast.npy, countries.pkl, grid.npz, checks.json.

Rasterising: polygons are burnt into a 3,600 x 1,800 grid with PIL, pixel centres at the cell centres; a sample of
cells is then tested against the exact polygons with shapely and the agreement is recorded (checks.json). Country
cells come from the 1:10m country outlines, drawn largest first so that enclaves (Lesotho, San Marino) sit on top of
the country around them; land cells that fall just outside every 1:10m outline (a fringe along coasts, where the 1:50m
land and 1:10m countries disagree) take the nearest country."""
import numpy as np, pandas as pd
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree
from scipy import ndimage
import shapely
from shapely.geometry import shape
from common import *

CHK = {}
# ---------- towns (GeoNames cities1000) ----------
T0 = jload(f"{RAW}/geonames_cities1000.json")
T = pd.DataFrame(T0)
T["lat"] = T.lat.astype(float); T["lon"] = T.lng.astype(float)
CHK["towns_rows"] = len(T)
T = T[(T.lat.abs() <= 90) & (T.lon.abs() <= 180)].drop_duplicates(["name", "lat", "lon"]).reset_index(drop=True)
CHK["towns"] = len(T); CHK["towns_dupes_dropped"] = CHK["towns_rows"] - len(T)
CHK["towns_south_of_60s"] = int((T.lat < -60).sum())
CHK["commit"] = open(f"{RAW}/cities_json_commit.txt").read().strip()
T[["name", "lat", "lon", "country", "admin1"]].to_pickle(f"{WORK}/towns.pkl")

# ---------- cities with populations (Natural Earth) ----------
P = jload(f"{GEO}/ne_10m_populated_places_simple.geojson")["features"]
C = pd.DataFrame([{"name": re.sub(r"\s+", " ", f["properties"]["name"]), "lat": f["properties"]["latitude"], "lon": f["properties"]["longitude"],
                   "pop": int(f["properties"].get("pop_max") or 0), "country": f["properties"]["adm0name"], "iso": f["properties"]["adm0_a3"]} for f in P])
CHK["ne_places"] = len(C); CHK["c100k"] = int((C["pop"] >= 1e5).sum()); CHK["c1m"] = int((C["pop"] >= 1e6).sum())
C.to_pickle(f"{WORK}/cities.pkl")

# ---------- rasterise ----------
def rings(geom):
    g = shape(geom) if isinstance(geom, dict) else geom
    polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
    for p in polys:
        yield np.asarray(p.exterior.coords), [np.asarray(h.coords) for h in p.interiors]


def px(xy):
    return [(float((x + 180) / RES - .5), float((90 - y) / RES - .5)) for x, y in xy]


LANDG = [shape(f["geometry"]) for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]]
im = Image.new("L", (NX, NY), 0); dr = ImageDraw.Draw(im)
for g in LANDG:
    for ext, holes in rings(g):
        dr.polygon(px(ext), fill=1)
        for h in holes: dr.polygon(px(h), fill=0)
LAND = np.array(im, dtype=bool)
LANDU = shapely.union_all(LANDG); shapely.prepare(LANDU)
# cells on or next to the rasterised edge: decide them exactly with shapely (cell centre inside the land polygons)
edge = ndimage.binary_dilation(LAND, iterations=1) & ~ndimage.binary_erosion(LAND, iterations=1, border_value=1)
ej, ei = np.nonzero(edge)
LAND[ej, ei] = shapely.contains_xy(LANDU, GRID_LON[ei], GRID_LAT[ej])
CHK["edge_cells_exact"] = int(len(ej))
rng = np.random.default_rng(1)
jj, ii = rng.integers(0, NY, 40000), rng.integers(0, NX, 40000)
exact = shapely.contains_xy(LANDU, GRID_LON[ii], GRID_LAT[jj])
CHK["land_raster_agree_pct"] = round(100 * float((exact == LAND[jj, ii]).mean()), 2)
assert CHK["land_raster_agree_pct"] > 99.5, CHK

W = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
rows = []
for k, f in enumerate(W):
    p = f["properties"]; g = shape(f["geometry"])
    nm = NAME_FIX.get(p["NAME"], NAME_FIX.get(p.get("NAME_EN") or p["NAME"], p.get("NAME_EN") or p["NAME"]))
    nm = NAME_FIX.get(nm, nm)
    kind = "antarctica" if p["NAME"] == "Antarctica" else "skip" if p["NAME"] in SKIP else \
        "country" if (p["TYPE"] in COUNTRY_TYPES or p["NAME"] in COUNTRY_EXTRA) else "territory"
    iso = p["ISO_A3_EH"] if p.get("ISO_A3_EH") not in ("-99", None) else p["ADM0_A3"]
    iso2 = p["ISO_A2_EH"] if p.get("ISO_A2_EH") not in ("-99", None) else p["ISO_A2"]
    cont = CONT_FIX.get(p["CONTINENT"], p["CONTINENT"])
    rows.append({"k": k, "name": nm, "ne_name": p["NAME"], "iso": iso, "iso2": iso2, "adm0": p["ADM0_A3"], "sov": p["SOVEREIGNT"], "type": p["TYPE"],
                 "kind": kind, "continent": cont, "geom": g, "area_deg": g.area})
CT = pd.DataFrame(rows)
CT.loc[CT.name == "Greenland", "kind"] = "country"      # self-governing within the Kingdom of Denmark; listed with countries
dup = CT[CT.kind != "skip"].name.duplicated(keep=False)
assert not dup.any(), CT[CT.kind != "skip"][dup].name.tolist()
cim = Image.new("I", (NX, NY), 0); cd = ImageDraw.Draw(cim)
for r in CT.sort_values("area_deg", ascending=False).itertuples():
    for ext, holes in rings(r.geom):
        cd.polygon(px(ext), fill=r.k + 1)
        for h in holes: cd.polygon(px(h), fill=0)
CID = np.array(cim, dtype=np.int32) - 1                  # -1 = no country
gap = LAND & (CID < 0)
CHK["land_cells_outside_countries"] = int(gap.sum())
_, (nj, ni) = ndimage.distance_transform_edt(CID < 0, return_indices=True)
CIDF = np.where(gap, CID[nj, ni], CID)
CIDF = np.where(LAND, CIDF, -1)

# continent per land cell. Russia is split along a rough line for the Urals and the Pai-Khoi ridge: Europe west of
# 60 E up to 65 N, then a line to 66 E at 68.5 N, back to 60.5 E at the Yugorsky Strait (69.8 N), and out through the
# Kara Sea (66.5 E, then 70 E north of 74.5 N) so that Vaygach, Novaya Zemlya and Franz Josef Land are in Europe and
# Yamal and Severnaya Zemlya in Asia; everything east of that, including Chukotka beyond 180 degrees, is Asia.
def ural_lon(la):
    return np.interp(la, [0, 65, 68.5, 69.8, 70.3, 70.6, 74, 74.5, 90], [60, 60, 66, 60.5, 60.5, 66.5, 66.5, 70, 70])
cont_of = CT.continent.tolist()
lonI = np.broadcast_to(GRID_LON[None, :], (NY, NX))
CONT = np.full((NY, NX), -1, np.int8)
for k, cn in enumerate(cont_of):
    if not isinstance(cn, str): continue
    m = CIDF == k
    if CT.adm0[k] == "RUS":
        latI = np.broadcast_to(GRID_LAT[:, None], (NY, NX)); eu = (lonI > 0) & (lonI < ural_lon(latI))
        CONT[m & eu] = CONTINENTS.index("Europe"); CONT[m & ~eu] = CONTINENTS.index("Asia")
    else:
        CONT[m] = CONTINENTS.index(cn)
CHK["land_cells"] = int(LAND.sum()); CHK["land_cells_no_continent"] = int((LAND & (CONT < 0)).sum())

# land mass per cell: the Natural Earth 1:50m land polygon it lies in (Afro-Eurasia and the Americas are single
# polygons; Chukotka east of 180 degrees is joined to Eurasia below). Edge cells without a polygon take the nearest.
pim = Image.new("I", (NX, NY), 0); pdr = ImageDraw.Draw(pim); polys = []
for g in LANDG:
    polys += list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
polys.sort(key=lambda q: -q.area)
for k, q in enumerate(polys):
    for ext, holes in rings(q):
        pdr.polygon(px(ext), fill=k + 1)
        for h in holes: pdr.polygon(px(h), fill=0)
PID = np.array(pim, dtype=np.int32) - 1
_, (pj, pi) = ndimage.distance_transform_edt(PID < 0, return_indices=True)
PID = np.where(LAND & (PID < 0), PID[pj, pi], PID)
def pid_at(la, lo): return PID[int((90 - la) / RES), int((lo + 180) / RES)]
PID[PID == pid_at(66, -172)] = pid_at(50, 90)
CHK["land_polygons"] = len(polys)

# ---------- coastline points (land outlines densified to 0.02 degrees, about 2 km) ----------
bd = shapely.segmentize(shapely.boundary(LANDU), 0.02)
CO = shapely.get_coordinates(bd)
CHK["coast_points"] = len(CO)
np.save(f"{WORK}/coast.npy", CO.astype(np.float32))

# ---------- distances ----------
J, I = np.nonzero(LAND)
lat, lon = GRID_LAT[J], GRID_LON[I]
U = unit(lat, lon)
trees = {"town": cKDTree(unit(T.lat, T.lon)), "c100k": cKDTree(unit(C[C["pop"] >= 1e5].lat, C[C["pop"] >= 1e5].lon)),
         "c1m": cKDTree(unit(C[C["pop"] >= 1e6].lat, C[C["pop"] >= 1e6].lon)), "coast": cKDTree(unit(CO[:, 1], CO[:, 0]))}
D, NI = {}, {}
for k, tr in trees.items():
    d, ix = tr.query(U, workers=-1)
    D[k] = chord_km(d).astype(np.float32); NI[k] = ix.astype(np.int32)
    print(k, "max", round(float(D[k].max())), "km")
np.savez_compressed(f"{WORK}/grid.npz", J=J.astype(np.int16), I=I.astype(np.int16), cid=CIDF[J, I].astype(np.int16), cont=CONT[J, I], pid=PID[J, I].astype(np.int32),
                    area=cell_area_km2(lat).astype(np.float32), **{f"d_{k}": v for k, v in D.items()}, **{f"n_{k}": v for k, v in NI.items()})
CT.drop(columns=["geom"]).to_pickle(f"{WORK}/countries_meta.pkl")
CT[["k", "name", "geom"]].to_pickle(f"{WORK}/countries_geom.pkl")
jsave(CHK, f"{WORK}/checks.json", indent=1)
print(CHK)
