"""r/dataisbeautiful collage for remote-places: 2400 x 3200 px, light background. Numbers from data/results.json.
Every label sits on open sea or on the paper around the globe, with a halo; figstyle.Labeler checks that no label
touches land, data or another label and that no leader line crosses a label."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from figstyle import *
import pandas as pd
import shapely, shapely.affinity
from shapely.geometry import Point
from scipy.spatial import cKDTree
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

R = jload(f"{DATA}/results.json")
CN, SH, U, A = R["continents"], R["share"], R["uk"], R["antarctica"]
BGc = "#F7F5F0"; SEAc = "#E6EDF0"
HALOS = [pe.withStroke(linewidth=4, foreground=SEAc)]
HALOP = [pe.withStroke(linewidth=4, foreground=BGc)]

fig = plt.figure(figsize=(12, 16.0), dpi=200, facecolor=BGc)
fig.text(.045, .985, "The middle of nowhere", fontproperties=DISP, fontsize=46, color=FG, va="top")
fig.text(.045, .935, f"How far every point on land is from the nearest town of 1,000+ people. {SH['town']['100']:.0f}% of the land outside\n"
         f"Antarctica is more than 100 km from one; the most remote land of all is {R['scraps'][0]['d']:,.0f} km away.",
         fontproperties=SERP, fontsize=14, color=FG, va="top", linespacing=1.45)

# ---- map
EXT = (WORLD_EXT[0], WORLD_EXT[1], WORLD_EXT[2], 1.05e7)
ax = fig.add_axes([0, .515, 1, .39])
ax.imshow(ee_raster("town", 2400, sea=SEAc, paper=BGc), extent=WORLD_EXT, origin="upper", interpolation="nearest", zorder=1)
outline(ax, ec="#C3C9CC", lw=.8, z=2); world(ax, lw=.25, ec=(1, 1, 1, .5), z=3, fill=False, ext=EXT)
NAMES = {"Asia": "CAPE CHELYUSKIN", "Australia and Oceania": "GREAT VICTORIA DESERT", "Africa": "LIBYAN DESERT", "North America": "N. SASKATCHEWAN",
         "South America": "NORTHERN BRAZIL", "Europe": "ARCTIC RUSSIA", "Antarctica": "ANTARCTICA"}
SUB = {"Asia": "Asia", "Australia and Oceania": "Australia", "Africa": "Africa", "North America": "N. America",
       "South America": "S. America", "Europe": "Europe", "Antarctica": "no towns:"}
PREF = {"Asia": (115, 89), "Australia and Oceania": (100, -36), "Africa": (-32, 20), "North America": (-100, 89), "South America": (-28, -3),
        "Europe": (25, 89), "Antarctica": (150, -60)}
pts = []
for cn in CONTINENTS:
    p = CN[cn]["town"]; x, y = proj(p["lon"], p["lat"]); pts.append((cn, float(x), float(y), p))
    ax.scatter([x], [y], s=60, c="#fff", ec=INK, lw=1.8, zorder=8)
M = R["scraps"][0]; mx, my = proj(M["lon"], M["lat"]); ax.scatter([mx], [my], s=60, marker="D", c="#fff", ec=INK, lw=1.8, zorder=8)
avoid = shapely.union_all([land_ee(6e4)] + [Point(x, y).buffer(1.7e5) for _, x, y, _ in pts] + [Point(float(mx), float(my)).buffer(1.7e5)])
L = Labeler(fig, ax, avoid, halo=HALOS, margin=2e5)
for cn, x, y, p in pts:
    x0, y0 = proj(*PREF[cn])
    L.place(cn, f"{NAMES[cn]}\n{SUB[cn]}{',' if cn != 'Antarctica' else ''} {p['d']:,.0f} km", L.ring(float(x0), float(y0), 2.5e5, 26), target=(x, y, 1.3e5), lead_gap=4e5, size=9.5, col=INK)
x0, y0 = proj(40, -38)
L.place("Marion", f"MARION ISLAND\n{M['d']:,.0f} km, most remote\noutside Antarctica", L.ring(float(x0), float(y0), 2.5e5, 30), target=(float(mx), float(my), 1.3e5), lead_gap=4e5, size=9.5, col=INK)
print("map labels ok:", L.check(), "leaders:", [n for n, _ in L.lines])

# ---- legend under the map
kx, ky, kw = .045, .487, .55
a = fig.add_axes([kx, ky, kw, .012]); a.set_xlim(0, len(BIN_COL)); a.set_ylim(0, 1); a.axis("off")
for i, c in enumerate(BIN_COL): a.add_patch(Rectangle((i, 0), 1, 1, fc=c, ec="none"))
for i, b in enumerate(BINS): a.text(i, -.45, f"{b:,}", ha="center", va="top", fontsize=9, color=FG)
a.text(len(BIN_COL) + .1, -.45, "km", ha="left", va="top", fontsize=9, color=MUT)
fig.text(kx, ky + .02, "Great-circle distance to the nearest place of 1,000+ people (GeoNames)", fontsize=10, color=FG)
fig.legend(handles=[Line2D([], [], ls="", marker="o", ms=9, mfc="#fff", mec=INK, mew=1.8, label="most remote point of each mainland"),
                    Line2D([], [], ls="", marker="D", ms=8, mfc="#fff", mec=INK, mew=1.8, label="most remote land outside Antarctica")],
           loc="upper left", bbox_to_anchor=(.64, .515), frameon=False, fontsize=10, handletextpad=.4, labelspacing=.7)

# ---- numbers row
nums = [(f"{SH['town']['100']:.0f}%", HOT, "of the land outside Antarctica\nis over 100 km from a town"),
        (f"{R['eurasia']['ours_town']:.0f} km", COOL, "from a town: the land farthest\nfrom the sea, in China"),
        (f"{A['min_town']:,.0f} km", "#5B4B8A", "the least any point in\nAntarctica is from a town"),
        (f"{U['Scotland']['d']:.0f} km", INK, "Britain's most remote spot,\nnear Cape Wrath")]
for i, (big, col, small) in enumerate(nums):
    xx = .045 + i * .235
    fig.text(xx, .455, big, fontproperties=DISP, fontsize=34, color=col, va="top")
    fig.text(xx, .415, small, family=MONO, fontsize=10, color=FG, va="top", linespacing=1.4)

# ---- share curves
s = fig.add_axes([.085, .075, .44, .25]); s.set_facecolor(BGc)
d = np.array(R["cum"]["d"])
for k, short, long, c in MEASURES:
    s.plot(np.maximum(d, 1), R["cum"][k], color=c, lw=2.4); s.plot([SH[k]["median"]], [50], "o", color=c, ms=5)
s.set_xscale("log"); s.set_xlim(2, 4000); s.set_ylim(0, 100); spines(s); s.grid(color=RULE, lw=.7); s.set_axisbelow(True)
s.set_xticks([2, 10, 100, 1000]); s.set_xticklabels(["2", "10", "100", "1,000 km"]); s.set_yticks(range(0, 101, 25)); s.set_yticklabels([f"{v}%" for v in range(0, 101, 25)])
s.tick_params(labelsize=9.5)
s.set_title("Share of land within a distance of...", family=MONO, fontsize=12, color=FG, loc="left", pad=8)
for j, (k, t) in enumerate((("town", "a town of 1,000+"), ("c100k", "a city of 100,000+"), ("coast", "the sea"), ("c1m", "a city of a million"))):
    s.plot([2.5, 3.4], [95 - j * 7.5] * 2, color=MCOL[k], lw=2.4); s.text(3.7, 95 - j * 7.5, t, color=MCOL[k], fontsize=9.5, fontweight="medium", va="center", ha="left")
s.text(2.5, 64, "dots: half of all land\nis within this distance", fontsize=8.5, color=MUT, va="top")
# the key must sit clear of every curve: check the curves stay below it over its width
for k in MKEYS:
    v = np.interp(np.log10([2.5, 20]), np.log10(np.maximum(d, 1)), R["cum"][k]); assert v.max() < 50, k

# ---- the UK
T = pd.read_pickle(f"{WORK}/towns.pkl"); tree = cKDTree(unit(T.lat, T.lon))
CG = pd.read_pickle(f"{WORK}/countries_geom.pkl")
UK = CG.geom[CG.name == "United Kingdom"].iloc[0]; IE = shapely.union_all([CG.geom[CG.name == n].iloc[0] for n in ("Ireland", "Isle of Man")])
st = .02; lo_ = np.arange(-8.4, 2.0, st); la_ = np.arange(49.8, 61.0, st)
LO, LA = np.meshgrid(lo_, la_); shapely.prepare(UK); ins = shapely.contains_xy(UK, LO.ravel(), LA.ravel())
dd = np.full(LO.size, np.nan); dist, _ = tree.query(unit(LA.ravel()[ins], LO.ravel()[ins]), workers=-1); dd[ins] = chord_km(dist)
UKB = [0, 2, 5, 10, 15, 20, 30, 40, 60, 80]
bi = np.clip(np.searchsorted(UKB, np.nan_to_num(dd), side="right") - 1, 0, 9)
img = np.ones((LO.size, 4)); img[:, :3] = np.array([hexrgb(c) for c in BIN_COL])[bi]; img[~ins, 3] = 0
K = np.cos(np.radians(55.5))
u = fig.add_axes([.585, .1, .37, .265]); u.set_facecolor(SEAc)
for q in (IE.geoms if IE.geom_type == "MultiPolygon" else [IE]):
    xy = np.array(q.exterior.coords); u.add_patch(MPoly(np.column_stack([xy[:, 0] * K, xy[:, 1]]), closed=True, fc="#DDD8CC", ec="none", zorder=1))
u.imshow(img.reshape(LO.shape + (4,)), extent=(lo_[0] * K, (lo_[-1] + st) * K, la_[0], la_[-1] + st), origin="lower", interpolation="nearest", zorder=2)
u.set_xlim(-11.0 * K, 2.0 * K); u.set_ylim(49.9, 61.0); u.set_aspect("equal"); u.set_xticks([]); u.set_yticks([])
for sp in u.spines.values(): sp.set_edgecolor("#C3C9CC")
u.set_title("The UK's most remote spots", family=MONO, fontsize=12, color=FG, loc="left", pad=8)
UKP = [("Scotland", f"Near CAPE WRATH\n{U['Scotland']['d']:.0f} km from a town", (-8.6, 59.6)),
       ("England", f"KIELDER\nEngland\n{U['England']['d']:.0f} km", (0.2, 56.4)),
       ("Wales", f"LLŶN\nWales\n{U['Wales']['d']:.0f} km", (-6.9, 52.3)),
       ("Northern Ireland", f"SPERRINS\nN. Ireland\n{U['Northern Ireland']['d']:.0f} km", (-8.6, 56.3))]
up = [(U[n]["lon"] * K, U[n]["lat"]) for n, _, _ in UKP]
for x, y in up: u.scatter([x], [y], s=34, c="#fff", ec=INK, lw=1.5, zorder=8)
lk = shapely.affinity.scale(shapely.union_all([UK, IE]), xfact=K, yfact=1, origin=(0, 0)).buffer(.05)
LU = Labeler(fig, u, shapely.union_all([lk] + [Point(x, y).buffer(.12) for x, y in up]), halo=HALOS)
for (n, t, (lo0, la0)), (x, y) in zip(UKP, up):
    starts = [(lo0, la0)] + ([(-10.2, 55.6), (-10.3, 53.6), (-7.0, 56.6)] if n == "Northern Ireland" else [])
    cands = [c for a, b in starts for c in LU.ring(a * K, b, .07, 18)]
    LU.place(n, t, cands, target=(x, y, .08), lead_gap=.15, size=8.5, col=INK)
print("uk labels ok:", LU.check())
uk = fig.add_axes([.64, .074, .28, .007]); uk.set_xlim(0, 10); uk.set_ylim(0, 1); uk.axis("off")
for i, c in enumerate(BIN_COL): uk.add_patch(Rectangle((i, 0), 1, 1, fc=c, ec="none"))
for i, b in enumerate(UKB): uk.text(i, -.6, str(b), ha="center", va="top", fontsize=7.5, color=FG)
uk.text(10.15, -.6, "km", ha="left", va="top", fontsize=7.5, color=MUT)
fig.text(.585, .0755, "UK, km:", fontsize=8, color=FG)

fig.text(.045, .006, "Source: GeoNames cities1000 (geonames.org, CC BY 4.0) for towns; Natural Earth for cities, land, coast and countries (public domain).\n"
         "Straight-line distances over the globe on a 0.1° area-weighted grid; villages under 1,000 people are not counted. Antarctica's stations are not towns.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib  ·  maps.tristanhotham.com/remote-places", family=MONO, fontsize=8.2, color=MUT, linespacing=1.5, va="bottom")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "middle_of_nowhere.png")
fig.savefig(out, facecolor=BGc, dpi=200)
print("ok", out)
