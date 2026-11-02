"""House style for static figures: fonts (static instances cut from the variable Fraunces in /home/claude/ref/fonts,
written to WORK), the palette, Natural Earth outlines in the Equal Earth projection, the distance rasters re-projected to
Equal Earth, and a label placer that keeps every label on open sea or on the paper (never over land or data) and checks
that leader lines do not cross other labels."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
import matplotlib.patheffects as pe
import numpy as np
from pyproj import Transformer
from common import *

FD = os.path.join(WORK, "fonts"); os.makedirs(FD, exist_ok=True)
if not os.path.exists(f"{FD}/Fraunces-Black.ttf"):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for w, nm in ((900, "Black"), (700, "Bold")):
        instancer.instantiateVariableFont(TTFont(f"{FONTS}/FrauncesVar.ttf"), {"wght": w, "opsz": 144, "SOFT": 0, "WONK": 0}).save(f"{FD}/Fraunces-{nm}.ttf")
DISP = fm.FontProperties(fname=f"{FD}/Fraunces-Black.ttf")
DISPB = fm.FontProperties(fname=f"{FD}/Fraunces-Bold.ttf")
SERP = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Regular.ttf")
SERB = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Semibold.ttf")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 12, "axes.edgecolor": "#636A72", "axes.labelcolor": "#1D2128",
                     "xtick.color": "#636A72", "ytick.color": "#636A72"})
BG, FG, MUT, LAND, RULE, SEA = "#F6F4EF", "#1D2128", "#636A72", "#E2DED3", "#DDD8CC", "#E6EDF0"
HOT, COOL, INK = "#B4462E", "#2F6F8F", "#22102F"
MCOL = {m[0]: m[3] for m in MEASURES}
HALO = [pe.withStroke(linewidth=3.5, foreground=SEA)]
HALOP = [pe.withStroke(linewidth=3.5, foreground=BG)]

EE = Transformer.from_crs(4326, 8857, always_xy=True)
EEI = Transformer.from_crs(8857, 4326, always_xy=True)
W = jload(f"{DATA}/world.json")
WORLD_EXT = (-17.35e6, 17.35e6, -8.75e6, 8.7e6)


def rings(geom):
    cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in cs:
        yield np.array(poly[0])


SHAPES = []
for f in W["features"]:
    for ring in rings(f["geometry"]):
        x, y = EE.transform(np.clip(ring[:, 0], -179.99, 179.99), np.clip(ring[:, 1], -89.5, 89.5))
        SHAPES.append((f["properties"]["iso"], np.column_stack([x, y]), ring))


def world(ax, lw=.3, ext=WORLD_EXT, ec="#FFFFFF", land=LAND, z=1, fill=True):
    for iso, p, _ in SHAPES:
        ax.add_patch(MPoly(p, closed=True, fc=land if fill else "none", ec=ec, lw=lw, zorder=z))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.axis("off")


def outline(ax, fc=None, lw=.8, ec=MUT, z=0):
    """Equal Earth globe outline."""
    lat = np.linspace(-90, 90, 181)
    xl, yl = EE.transform(np.full_like(lat, -180), lat); xr, yr = EE.transform(np.full_like(lat, 180), lat[::-1])
    ax.add_patch(MPoly(np.column_stack([np.r_[xl, xr], np.r_[yl, yr]]), closed=True, fc=fc or "none", ec=ec, lw=lw, zorder=z))


def proj(lon, lat):
    return EE.transform(np.asarray(lon), np.asarray(lat))


def spines(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def hexrgb(c):
    return [int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def ee_raster(key, w=2400, ext=WORLD_EXT, sea=SEA, paper=BG):
    """RGB image of one distance measure in Equal Earth, w pixels wide, with sea and paper colours."""
    cache = f"{WORK}/ee_{key}_{w}.npy"
    h = int(round(w * (ext[3] - ext[2]) / (ext[1] - ext[0])))
    if os.path.exists(cache):
        b = np.load(cache)
    else:
        G = dict(np.load(f"{WORK}/grid.npz")); a = grid2d(G, key)
        x = ext[0] + (np.arange(w) + .5) * (ext[1] - ext[0]) / w; y = ext[3] - (np.arange(h) + .5) * (ext[3] - ext[2]) / h
        X, Y = np.meshgrid(x, y); lo, la = EEI.transform(X.ravel(), Y.ravel())
        lo, la = np.asarray(lo).reshape(h, w), np.asarray(la).reshape(h, w)
        ok = np.isfinite(lo) & np.isfinite(la) & (np.abs(lo) <= 180.0001) & (np.abs(la) <= 90)
        b = np.full((h, w), -2, np.int16)                     # -2 outside the globe, -1 sea
        jj = np.clip(((90 - la[ok]) / RES).astype(int), 0, NY - 1); ii = np.clip(((lo[ok] + 180) / RES).astype(int), 0, NX - 1)
        v = a[jj, ii]; b[ok] = np.where(np.isnan(v), -1, binof(np.nan_to_num(v)))
        # points round-tripping badly are off the globe
        x2, y2 = EE.transform(lo[ok], la[ok]); bad = np.hypot(x2 - X[ok], y2 - Y[ok]) > 1e4
        t = b[ok]; t[bad] = -2; b[ok] = t
        np.save(cache, b)
    pal = np.array([hexrgb(c) for c in BIN_COL] + [hexrgb(paper), hexrgb(sea)])
    return pal[np.where(b >= 0, b, np.where(b == -1, len(BIN_COL) + 1, len(BIN_COL)))]


def bin_legend(fig, x, y, w, h, title, fs=9, n=None):
    """Horizontal colour key for the distance classes, drawn in figure coordinates."""
    n = n or len(BIN_COL); a = fig.add_axes([x, y, w, h]); a.set_xlim(0, n); a.set_ylim(0, 1); a.axis("off")
    for i in range(n):
        a.add_patch(matplotlib.patches.Rectangle((i, 0), 1, 1, fc=BIN_COL[i], ec="none"))
    for i, b in enumerate(BINS[:n]):
        a.text(i, -.25, f"{b:,}", ha="center", va="top", fontsize=fs, color=FG)
    a.text(n, -.25, "km", ha="left", va="top", fontsize=fs, color=MUT)
    a.text(0, 1.25, title, ha="left", va="bottom", fontsize=fs + .5, color=FG)
    return a


class Labeler:
    """Places text labels on an axes so that each label box avoids `avoid` (a shapely geometry in data units: land
    and data), other labels and leader lines; a leader is drawn when the label is far from its target."""

    def __init__(self, fig, ax, avoid, halo=HALO, margin=None):
        from shapely.prepared import prep
        self.fig, self.ax, self.avoid, self.av, self.halo = fig, ax, avoid, prep(avoid), halo
        self.placed, self.lines = [], []
        fig.canvas.draw(); self.ren = fig.canvas.get_renderer(); self.margin = margin

    def tbox(self, t):
        from shapely.geometry import box
        bb = t.get_window_extent(self.ren)
        (x0, y0), (x1, y1) = self.ax.transData.inverted().transform([[bb.x0 - 4, bb.y0 - 3], [bb.x1 + 4, bb.y1 + 3]])
        return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def bad(self, b):
        from shapely.geometry import box
        x0, x1 = self.ax.get_xlim(); y0, y1 = self.ax.get_ylim(); m = self.margin or 0
        if not box(x0 + m, y0 + m, x1 - m, y1 - m).contains(b): return True
        return self.av.intersects(b) or any(b.intersects(o) for _, _, o in self.placed) or any(b.intersects(l) for _, l in self.lines)

    def place(self, name, s, cands, target=None, lead_gap=None, ha="center", col=FG, size=10, w="medium", lw=.7, family=MONO, fp=None):
        """cands: list of (x, y) in data units, tried in order. target: (x, y, r) to point at."""
        from shapely.geometry import Point, LineString
        from shapely.ops import nearest_points
        kw = dict(fontproperties=fp) if fp is not None else dict(family=family, fontweight=w)
        t = self.ax.text(0, 0, s, ha=ha, va="center", fontsize=size, color=col, linespacing=1.15, zorder=12, path_effects=self.halo, **kw)
        for x, y in cands:
            t.set_position((x, y)); b = self.tbox(t)
            if self.bad(b): continue
            ln = None
            if target is not None:
                c = Point(target[0], target[1]); gap = b.distance(c) - target[2]
                if lead_gap is not None and gap > lead_gap:
                    pb, _ = nearest_points(b, c); d = np.hypot(pb.x - c.x, pb.y - c.y)
                    e = (c.x + (pb.x - c.x) * target[2] / d, c.y + (pb.y - c.y) * target[2] / d)
                    ln = LineString([(pb.x, pb.y), e])
                    if any(ln.intersects(o) for _, _, o in self.placed) or any(ln.crosses(l) for _, l in self.lines): continue
            self.placed.append((name, t, b))
            if ln is not None:
                self.lines.append((name, ln)); self.ax.plot(*ln.xy, color=col, lw=lw, zorder=11)
            return t
        t.remove(); raise RuntimeError("no clean spot for " + name)

    def ring(self, x0, y0, step, n):
        """Candidate positions on growing squares around (x0, y0), nearest first."""
        out = [(x0, y0)]
        for r in range(1, n + 1):
            out += [(x0 + dx * step, y0 + dy * step) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
        return out

    def check(self):
        for nm, t, b in self.placed:
            assert not self.av.intersects(b), nm
            assert not any(b.intersects(o) for n2, _, o in self.placed if n2 != nm), nm
        for nm, l in self.lines:
            assert not any(l.intersects(o) for n2, _, o in self.placed if n2 != nm), nm
        return len(self.placed)


def land_ee(buffer_m=0, simplify=2e3):
    """Natural Earth 1:50m land in Equal Earth metres (for label avoidance), optionally buffered."""
    import shapely
    from shapely.geometry import shape, Polygon
    cache = f"{WORK}/land_ee.wkb"
    if os.path.exists(cache):
        g = shapely.from_wkb(open(cache, "rb").read())
    else:
        ps = []
        for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]:
            gg = shape(f["geometry"]); gs = gg.geoms if gg.geom_type == "MultiPolygon" else [gg]
            for q in gs:
                xy = np.array(q.exterior.coords); x, y = EE.transform(np.clip(xy[:, 0], -179.99, 179.99), np.clip(xy[:, 1], -89.9, 89.9))
                ps.append(Polygon(np.column_stack([x, y])).buffer(0))
        g = shapely.union_all(ps).simplify(simplify); open(cache, "wb").write(shapely.to_wkb(g))
    return g.buffer(buffer_m) if buffer_m else g
