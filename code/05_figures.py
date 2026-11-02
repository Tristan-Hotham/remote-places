"""Header card, blog figures (release/blog/b_*.png, 1,800 px wide) and paper figures (release/paper/f_*.png).
Numbers from data/results.json. Map labels sit on open sea or on the paper, checked by figstyle.Labeler."""
import pandas as pd
import shapely, shapely.affinity
from shapely.geometry import shape, Point, box
from scipy.spatial import cKDTree
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from figstyle import *

R = jload(f"{DATA}/results.json")
BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
CN, SH = R["continents"], R["share"]
LANDB = land_ee(6e4)          # land plus 60 km, the no-go zone for labels on world maps
W_IN = 12                     # figure width in inches: 150 dpi gives 1,800 px for the blog


def both(fig, name, blog=True):
    fig.savefig(os.path.join(PA, "f_" + name + ".png"), dpi=200, facecolor=fig.get_facecolor())
    if blog:
        fig.savefig(os.path.join(BL, "b_" + name + ".png"), dpi=1800 / W_IN, facecolor=fig.get_facecolor())
    plt.close(fig)


SHORT = {"Africa": "AFRICA", "Asia": "ASIA", "Europe": "EUROPE", "North America": "NORTH AMERICA", "South America": "SOUTH AMERICA",
         "Australia and Oceania": "AUSTRALIA", "Antarctica": "ANTARCTICA"}
# preferred label spots (lon, lat) on the sea near each pole
PREF = {"town": {"Africa": (-30, 22), "Asia": (105, 89), "Europe": (20, 76), "North America": (-150, 52), "South America": (-30, -2),
                 "Australia and Oceania": (100, -33), "Antarctica": (150, -62)},
        "c1m": {"Africa": (-30, 22), "Asia": (-150, 86), "Europe": (45, 88), "North America": (-160, 48), "South America": (-40, -50),
                "Australia and Oceania": (100, -15), "Antarctica": (20, -62)}}


def world_map(key, title, name, extra=()):
    EXT = (WORLD_EXT[0], WORLD_EXT[1], WORLD_EXT[2], 1.0e7)                 # paper above the pole for Arctic labels
    fig = plt.figure(figsize=(W_IN, 7.3), facecolor=BG); ax = fig.add_axes([0, .1, 1, .82])
    img = ee_raster(key, 2400)
    ax.imshow(img, extent=WORLD_EXT, origin="upper", interpolation="nearest", zorder=1)
    outline(ax, ec="#C3C9CC", lw=.7, z=2); world(ax, lw=.25, ec=(1, 1, 1, .55), z=3, fill=False, ext=EXT)
    pts = []
    for cn in CONTINENTS:
        p = CN[cn][key]; x, y = proj(p["lon"], p["lat"]); pts.append((cn, float(x), float(y), p))
        ax.scatter([x], [y], s=46, c="#fff", ec=INK, lw=1.6, zorder=8)
    for nm, p in extra:
        x, y = proj(p["lon"], p["lat"]); pts.append((nm, float(x), float(y), p)); ax.scatter([x], [y], s=46, marker="D", c="#fff", ec=INK, lw=1.5, zorder=8)
    avoid = shapely.union_all([LANDB] + [Point(x, y).buffer(1.6e5) for _, x, y, _ in pts])
    L = Labeler(fig, ax, avoid, margin=2e5)
    for nm, x, y, p in pts:
        if nm in SHORT:
            lo0, la0 = PREF[key][nm]; s = f"{SHORT[nm]}\n{p['d']:,.0f} km"
        else:
            lo0, la0 = nm[1]; s = nm[0] + f"\n{p['d']:,.0f} km"
        x0, y0 = proj(lo0, la0); cands = L.ring(float(x0), float(y0), 2.5e5, 26)
        L.place(s if isinstance(nm, str) else nm[0], s, cands, target=(x, y, 1.2e5), lead_gap=4e5, size=9.5, col=INK)
    L.check()
    fig.text(.03, .975, title, fontsize=11, color=FG, va="top", linespacing=1.5)
    bin_legend(fig, .2, .045, .6, .022, f"Great-circle distance to the {dict((m[0], m[2]) for m in MEASURES)[key]}", fs=8.5)
    return fig, ax


# ---------- 1. distance to a town ----------
SC = R["scraps"][0]
fig, ax = world_map("town", "Distance from every point on land to the nearest place of 1,000+ people.\nCircles: the most remote point of each continent's mainland. Diamond: the most remote land outside Antarctica.",
                    "map_town", extra=[(("MARION ISLAND", (60, -40)), SC)])
both(fig, "map_town")
# ---------- 2. distance to a city of a million ----------
fig, ax = world_map("c1m", "Distance from every point on land to the nearest city of 1,000,000+.\nCircles: the farthest point of each continent's mainland from such a city.", "map_c1m")
both(fig, "map_c1m")

# ---------- 3. cumulative share of land ----------
fig = plt.figure(figsize=(W_IN, 5.8), facecolor=BG); ax = fig.add_axes([.08, .13, .66, .72]); ax.set_facecolor(BG)
d = np.array(R["cum"]["d"])
for k, short, long, c in MEASURES:
    v = np.array(R["cum"][k]); ax.plot(np.maximum(d, 1), v, color=c, lw=2.6)
    ax.plot([SH[k]["median"]], [50], "o", color=c, ms=6, zorder=5)
ax.set_xscale("log"); ax.set_xlim(2, 4000); ax.set_ylim(0, 100); spines(ax); ax.grid(color=RULE, lw=.8); ax.set_axisbelow(True)
ax.set_xticks([2, 5, 10, 25, 50, 100, 250, 500, 1000, 4000]); ax.set_xticklabels(["2", "5", "10", "25", "50", "100", "250", "500", "1,000", "4,000 km"])
ax.set_yticks(range(0, 101, 20)); ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)])
ax.set_ylabel("share of land within that distance"); ax.axhline(50, color=MUT, lw=.8, ls=(0, (3, 3)))
for k, short, long, c in MEASURES:
    v = np.array(R["cum"][k]); i = int(np.searchsorted(v, 50))
lab = [("town", f"a town of 1,000+\nmedian {SH['town']['median']:.0f} km"),
       ("c100k", f"a city of 100,000+\nmedian {SH['c100k']['median']:.0f} km"),
       ("coast", f"the sea\nmedian {SH['coast']['median']:.0f} km"),
       ("c1m", f"a city of a million\nmedian {SH['c1m']['median']:.0f} km")]
for j, (k, t) in enumerate(lab):
    fig.text(.77, .82 - j * .18, t, color=MCOL[k], fontsize=11, va="top", fontweight="medium", linespacing=1.35)
fig.text(.08, .975, "How much of the world's land (outside Antarctica) lies within a given distance of...\nDots: the median, the distance within which half of all land lies.", fontsize=10.5, color=FG, va="top", linespacing=1.4)
both(fig, "share")

# ---------- 4. countries: the farthest point from a town on each country's main land mass ----------
top = R["countries_main_top"][:20]
fig = plt.figure(figsize=(W_IN, 7.2), facecolor=BG); ax = fig.add_axes([.2, .06, .56, .86]); ax.set_facecolor(BG)
nm = [r["name"] for r in top][::-1]; v = [r["d"] for r in top][::-1]
ax.barh(nm, v, color=[MCOL["town"] if r["town_country"] == r["name"] else "#7A5C8E" for r in top][::-1], height=.68)
for i, r in enumerate(top[::-1]):
    ax.text(r["d"] + 8, i, f"{r['d']:,.0f} km  {r['town']}" + (f", {r['town_country']}" if r["town_country"] != r["name"] else ""), va="center", fontsize=9.3, color=FG)
ax.set_xlim(0, 1250); ax.set_xticks([]); spines(ax); ax.spines["bottom"].set_visible(False); ax.tick_params(axis="y", length=0, labelsize=10)
fig.text(.02, .975, "The farthest point from a town on each country's main land mass, and the nearest town to it (countries over 100,000 km²)", fontsize=10.5, color=FG, va="top")
fig.legend(handles=[Patch(color=MCOL["town"], label="nearest town in the same country"), Patch(color="#7A5C8E", label="nearest town across a border")],
           loc="lower right", bbox_to_anchor=(.98, .08), frameon=False, fontsize=9.5)
both(fig, "countries")

# ---------- 5. continents: the four measures ----------
fig, axs = plt.subplots(1, 4, figsize=(W_IN, 4.9), facecolor=BG); fig.subplots_adjust(left=.16, right=.985, wspace=.12, top=.82, bottom=.06)
order = [c for c in CONTINENTS if c != "Antarctica"]
for a, (k, short, long, c) in zip(axs, MEASURES):
    a.set_facecolor(BG); vals = [CN[x][k]["d"] for x in order][::-1]
    a.barh(range(len(order)), vals, color=c, height=.66)
    for i, vv in enumerate(vals): a.text(vv + max(vals) * .03, i, f"{vv:,.0f}", va="center", fontsize=9)
    a.set_xlim(0, max(vals) * 1.42); a.set_xticks([]); spines(a); a.spines["bottom"].set_visible(False); a.tick_params(axis="y", length=0, labelsize=10)
    a.set_yticks(range(len(order))); a.set_yticklabels([CN[x]["mainland"].replace("mainland ", "").replace("Australia", "Australia") for x in order][::-1] if a is axs[0] else [])
    a.set_title(f"from {short}", loc="left", fontsize=10.5, color=c, fontweight="medium")
fig.text(.02, .965, "The most remote point of each continent's mainland, km, by what it is far from", fontsize=11, color=FG, va="top")
both(fig, "continents")

# ---------- 6. latitude (paper only) ----------
B = pd.DataFrame(R["bands"])
fig = plt.figure(figsize=(W_IN, 4.6), facecolor=BG); ax = fig.add_axes([.08, .14, .9, .74]); ax.set_facecolor(BG)
ax.bar(B.b + 2.5, B.far100, width=4.4, color=MCOL["town"], label="over 100 km from a town")
ax.bar(B.b + 2.5, B.far500, width=4.4, color=INK, label="over 500 km")
ax.set_xlim(-57, 86); ax.set_ylim(0, 100); spines(ax); ax.grid(axis="y", color=RULE); ax.set_axisbelow(True)
ax.set_xticks(range(-50, 90, 10)); ax.set_xticklabels([f"{abs(v)}°{'S' if v < 0 else 'N' if v > 0 else ''}" for v in range(-50, 90, 10)])
ax.set_ylabel("% of land in the band"); ax.legend(frameon=False, loc="upper left", fontsize=10)
fig.text(.08, .94, "Share of land in each 5° band of latitude that is far from any town (Antarctica excluded)", fontsize=11, color=FG)
both(fig, "lat", blog=False)

# ---------- 7. the United Kingdom ----------
UKB = [0, 2, 5, 10, 15, 20, 30, 40, 60, 80]
UKC = BIN_COL
T = pd.read_pickle(f"{WORK}/towns.pkl"); tree = cKDTree(unit(T.lat, T.lon))
CG = pd.read_pickle(f"{WORK}/countries_geom.pkl")
geo = {n: CG.geom[CG.name == n].iloc[0] for n in ("United Kingdom", "Ireland", "Isle of Man", "Jersey", "Guernsey")}
UK = geo["United Kingdom"]; shapely.prepare(UK)
other = shapely.union_all([geo[n] for n in ("Ireland", "Isle of Man", "Jersey", "Guernsey")])
st = .01; lo_ = np.arange(-11.0, 2.0, st); la_ = np.arange(49.8, 61.0, st)
LO, LA = np.meshgrid(lo_, la_); ins = shapely.contains_xy(UK, LO.ravel(), LA.ravel())
dd = np.full(LO.size, np.nan); dist, _ = tree.query(unit(LA.ravel()[ins], LO.ravel()[ins]), workers=-1); dd[ins] = chord_km(dist)
bi = np.clip(np.searchsorted(UKB, np.nan_to_num(dd), side="right") - 1, 0, len(UKB) - 1)
pal = np.array([hexrgb(c) for c in UKC]); img = np.ones((LO.size, 4)); img[:, :3] = pal[bi]; img[~ins, 3] = 0
img = img.reshape(LO.shape + (4,))
K = np.cos(np.radians(55.5))
fig = plt.figure(figsize=(W_IN, 10.5), facecolor=BG); ax = fig.add_axes([.0, .06, .64, .9]); ax.set_facecolor(SEA)
def pg(g, **kw):
    for q in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
        xy = np.array(q.exterior.coords); ax.add_patch(MPoly(np.column_stack([xy[:, 0] * K, xy[:, 1]]), closed=True, **kw))
pg(other, fc="#DDD8CC", ec="#fff", lw=.4, zorder=1)
ax.imshow(img, extent=(lo_[0] * K - st * K / 2, lo_[-1] * K + st * K / 2, la_[0] - st / 2, la_[-1] + st / 2), origin="lower", interpolation="nearest", zorder=2)
pg(UK, fc="none", ec=(1, 1, 1, .7), lw=.4, zorder=3)
ax.set_xlim(-11.0 * K, 2.0 * K); ax.set_ylim(49.85, 60.95); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values(): s.set_edgecolor("#C3C9CC")
U, spots = R["uk"], R["gb_spots"]
marks = [("Scotland", U["Scotland"]), ("England", U["England"]), ("Wales", U["Wales"]), ("Northern Ireland", U["Northern Ireland"])]
pts = []
for i, s in enumerate(spots[:6]):
    x, y = s["lon"] * K, s["lat"]; ax.scatter([x], [y], s=60, c="#fff", ec=INK, lw=1.5, zorder=8); pts.append((x, y))
    if i: ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=6.5, color=INK, zorder=9, fontweight="bold")
for n, p in marks[1:]:
    x, y = p["lon"] * K, p["lat"]; ax.scatter([x], [y], s=60, marker="D", c="#fff", ec=INK, lw=1.5, zorder=8); pts.append((x, y))
landuk = shapely.union_all([UK, other]); lk = shapely.affinity.scale(landuk, xfact=K, yfact=1, origin=(0, 0)).buffer(.04)
avoid = shapely.union_all([lk] + [Point(x, y).buffer(.12) for x, y in pts])
L = Labeler(fig, ax, avoid)
assert 58.5 < U["Scotland"]["lat"] < 58.7 and -5.05 < U["Scotland"]["lon"] < -4.85     # Cape Wrath, the north-west tip of mainland Scotland
assert 55.1 < U["England"]["lat"] < 55.35 and -2.75 < U["England"]["lon"] < -2.4       # Kielder Forest, Northumberland
assert 52.7 < U["Wales"]["lat"] < 52.85 and -4.85 < U["Wales"]["lon"] < -4.65          # the tip of the Llyn Peninsula
assert 54.6 < U["Northern Ireland"]["lat"] < 54.9 and -7.3 < U["Northern Ireland"]["lon"] < -6.8   # the Sperrin Mountains
labs = [("Scotland", f"SCOTLAND: near Cape Wrath\n{U['Scotland']['d']:.0f} km from {U['Scotland']['town_name']}", (-7.2, 59.25)),
        ("England", f"ENGLAND: Kielder Forest\n{U['England']['d']:.0f} km from {U['England']['town_name']}\n(in Scotland)", (0.3, 56.0)),
        ("Wales", f"WALES: tip of the Llŷn\n{U['Wales']['d']:.0f} km from {U['Wales']['town_name']}", (-6.5, 52.2)),
        ("Northern Ireland", f"NORTHERN IRELAND:\nthe Sperrins, {U['Northern Ireland']['d']:.0f} km\nfrom {U['Northern Ireland']['town_name']}", (-9.6, 56.4))]
for n, s, (lo0, la0) in labs:
    p = U[n]; L.place(n, s, L.ring(lo0 * K, la0, .1, 14), target=(p["lon"] * K, p["lat"], .07), lead_gap=.15, size=9.5, col=INK)
L.check()
fig.text(.65, .93, "The most remote spots\nin the United Kingdom", fontproperties=DISPB, fontsize=21, color=FG, va="top")
fig.text(.65, .845, "Distance to the nearest place of 1,000+\npeople. Circles: the ten most remote spots\non the island of Great Britain, at least\n30 km apart (top six drawn); diamonds:\nthe most remote point of England, Wales\nand Northern Ireland.", fontsize=9.5, color=FG, va="top", linespacing=1.45)
yy = .62
for i, s in enumerate(spots[:10]):
    fig.text(.65, yy - i * .033, f"{i + 1:>2}  {s['d']:>4.0f} km  {s['unit']}", fontsize=9.5, color=FG, va="top")
    fig.text(.65, yy - i * .033 - .015, f"            {s['lat']:.2f}°N {abs(s['lon']):.2f}°W", fontsize=8, color=MUT, va="top")
a = fig.add_axes([.66, .12, .3, .018]); a.set_xlim(0, len(UKC)); a.set_ylim(0, 1); a.axis("off")
for i in range(len(UKC)): a.add_patch(Rectangle((i, 0), 1, 1, fc=UKC[i], ec="none"))
for i, b in enumerate(UKB): a.text(i, -.3, str(b), ha="center", va="top", fontsize=8.5)
a.text(len(UKC), -.3, "km", fontsize=8.5, va="top", color=MUT); a.text(0, 1.4, "km to the nearest town", fontsize=9, va="bottom")
both(fig, "uk")

# ---------- header card 1200 x 630 ----------
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([.39, .08, .6, .84]); ax.imshow(ee_raster("town", 1400), extent=WORLD_EXT, origin="upper", interpolation="nearest")
outline(ax, ec="#C3C9CC", lw=.6, z=2); ax.set_xlim(WORLD_EXT[0], WORLD_EXT[1]); ax.set_ylim(WORLD_EXT[2], WORLD_EXT[3]); ax.axis("off")
fig.text(.04, .86, "The middle", fontproperties=DISP, fontsize=50, color=FG, va="top")
fig.text(.04, .70, "of nowhere", fontproperties=DISP, fontsize=50, color=HOT, va="top")
fig.text(.04, .50, f"The places on Earth farthest from\nany town. A quarter of the land\noutside Antarctica is more than\n100 km from a place of 1,000 people.", fontproperties=SERP, fontsize=14.5, color=FG, va="top", linespacing=1.35)
fig.text(.04, .04, "maps.tristanhotham.com/remote-places", fontsize=11, color=MUT)
assert round(SH["town"]["100"]) == 25
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG)
plt.close(fig)
print("figures done", sorted(os.listdir(BL)), sorted(x for x in os.listdir(PA) if x.endswith(".png")))
