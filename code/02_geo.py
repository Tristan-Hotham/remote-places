"""Geography for the page and figures: a light world outline file (Natural Earth 1:50m), the four distance maps as
Web Mercator raster tiles (img/tiles/<measure>/{z}/{x}/{y}.png, 512 px tiles at zooms 0 to 3, cut from a 4,096 px
world image coloured by the classes in common.BINS, sea transparent), and
the point files the page loads on demand: every GeoNames town (data/towns.json), the Natural Earth cities of 100,000+
(data/cities.json) and a coastline thinned to about one point every 10 km (data/coast.json), used to measure any
clicked point in the browser."""
import numpy as np, pandas as pd
from PIL import Image
from shapely.geometry import shape, mapping
from common import *

iso_of = lambda p: p["ISO_A3_EH"] if p.get("ISO_A3_EH") not in ("-99", None) else p["ADM0_A3"]


def rnd(c, k=2):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return [round(c[0], k), round(c[1], k)]
    return [rnd(x, k) for x in c]


feats = []
for f in jload(f"{GEO}/ne_50m_admin_0_countries.geojson")["features"]:
    gs = shape(f["geometry"]).simplify(0.04, preserve_topology=True)
    if gs.is_empty: continue
    gm = mapping(gs)
    feats.append({"type": "Feature", "properties": {"iso": iso_of(f["properties"])}, "geometry": {"type": gm["type"], "coordinates": rnd(gm["coordinates"])}})
jsave({"type": "FeatureCollection", "features": feats}, f"{DATA}/world.json")

# ---------- Mercator overlays ----------
G = dict(np.load(f"{WORK}/grid.npz"))
S = 4096
x = (np.arange(S) + .5) / S
lon = -180 + 360 * x
yy = np.pi * (1 - 2 * (np.arange(S) + .5) / S)
lat = np.degrees(np.arctan(np.sinh(yy)))
jj = np.clip(((90 - lat) / RES).astype(int), 0, NY - 1); ii = np.clip(((lon + 180) / RES).astype(int), 0, NX - 1)
pal = []
for c in BIN_COL: pal += [int(c[i:i + 2], 16) for i in (1, 3, 5)]
pal += [0, 0, 0] * (256 - len(BIN_COL))
for k in MKEYS:
    a = grid2d(G, k)[jj[:, None], ii[None, :]]
    idx = np.where(np.isnan(a), 255, binof(np.nan_to_num(a))).astype(np.uint8)
    tot = 0
    for z in range(4):
        n = 2 ** z; step = S // n
        for tx in range(n):
            for ty in range(n):
                sub = idx[ty * step:(ty + 1) * step:step // 512, tx * step:(tx + 1) * step:step // 512]
                d = f"{IMG}/tiles/{k}/{z}/{tx}"; os.makedirs(d, exist_ok=True)
                im = Image.fromarray(np.ascontiguousarray(sub), "P"); im.putpalette(pal)
                im.save(f"{d}/{ty}.png", optimize=True, transparency=255); tot += os.path.getsize(f"{d}/{ty}.png")
    print(k, "tiles", tot // 1024, "KB")

# ---------- point files ----------
T = pd.read_pickle(f"{WORK}/towns.pkl").sort_values(["lat", "lon"])
# packed: latitude in hundredths of a degree as differences from the previous town (sorted by latitude), longitude in
# hundredths, and the country as an index into "cc"
la = np.round(T.lat.values * 100).astype(int); lo = np.round(T.lon.values * 100).astype(int)
CC = sorted(T.country.unique()); ci = {c: i for i, c in enumerate(CC)}
jsave({"note": "lat: cumulative sum of dlat / 100; lon / 100; cc index into cc", "cc": CC, "dlat": np.diff(la, prepend=0).tolist(), "lon": lo.tolist(),
       "name": T.name.tolist(), "c": [ci[c] for c in T.country]}, f"{DATA}/towns.json")
C = pd.read_pickle(f"{WORK}/cities.pkl"); C = C[C["pop"] >= 1e5].sort_values("pop", ascending=False)
jsave([{"name": r.name, "lat": round(r.lat, 3), "lon": round(r.lon, 3), "pop": int(r.pop), "country": r.country} for r in C.itertuples()], f"{DATA}/cities.json")
CO = np.load(f"{WORK}/coast.npy")[::5]
cl = np.round(CO[:, 1].astype(float) * 100).astype(int); cn = np.round(CO[:, 0].astype(float) * 100).astype(int)
jsave({"note": "hundredths of a degree; lat and lon as differences from the previous point", "dlat": np.diff(cl, prepend=0).tolist(), "dlon": np.diff(cn, prepend=0).tolist()}, f"{DATA}/coast.json")
print("world", os.path.getsize(f"{DATA}/world.json") // 1024, "KB; towns", os.path.getsize(f"{DATA}/towns.json") // 1024, "KB; coast", os.path.getsize(f"{DATA}/coast.json") // 1024, "KB; cities", len(C))
