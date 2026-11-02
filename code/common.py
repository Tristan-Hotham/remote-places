"""Shared paths, constants and helpers for the remote-places project ("The middle of nowhere").

Raw inputs (read in place, never modified):
  raw/geonames_cities1000.json   GeoNames cities1000 gazetteer: every populated place with 1,000 or more people
                                 (name, lat, lng, country, admin1; no population field). Packaged by lutangar/cities.json,
                                 commit in raw/cities_json_commit.txt. GeoNames, CC BY 4.0 (https://www.geonames.org/).
  /home/claude/newdata/raw/geo/ne_10m_populated_places_simple.geojson   Natural Earth populated places with
                                 population estimates (pop_max); used for cities of 100,000+ and 1,000,000+. Public domain.
  /home/claude/newdata/raw/geo/ne_50m_land.geojson                      Natural Earth 1:50m land (the land mask and the
                                 coastline). Lakes count as land; the Caspian Sea counts as sea. Public domain.
  /home/claude/newdata/raw/geo/ne_10m_admin_0_countries.geojson         Natural Earth 1:10m countries and territories.
  /home/claude/newdata/raw/geo/ne_50m_admin_0_countries.geojson         Natural Earth 1:50m countries (page and figure outlines).
  /home/claude/newdata/raw/geo/ne_10m_admin_1_states_provinces.geojson  Natural Earth 1:10m first-level units, used only
                                 to split the United Kingdom into England, Scotland, Wales and Northern Ireland and to name
                                 the council area of each UK point.

Method in one paragraph: a 0.1 degree latitude-longitude grid (3,600 x 1,800 cells) is laid over the Natural Earth land
mask. Every land cell is weighted by its true area on the sphere, so the shrinking cells near the poles count for what
they are. For each land cell centre the great-circle distance to the nearest (1) GeoNames place of 1,000+ people,
(2) Natural Earth city of 100,000+, (3) Natural Earth city of 1,000,000+ and (4) point on the Natural Earth coastline is
found with a k-d tree on unit vectors (the chord to the nearest point gives the great-circle angle exactly). Maxima are
then refined on a 0.01 degree grid around the best cells.
"""
import json, gzip, os, re, unicodedata
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
GEO = os.environ.get("RP_GEO", "/home/claude/newdata/raw/geo")
FONTS = os.environ.get("RP_FONTS", "/home/claude/ref/fonts")
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img")
WORK = os.path.join(os.environ.get("RPTMP", "/dev/shm/remoteplaces"), "work")   # intermediates live in memory, not in the repo
for d in (DATA, IMG, WORK):
    os.makedirs(d, exist_ok=True)

SLUG = "remote-places"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
DOI = "10.5281/zenodo.23873015"                # filled in by the publisher
BLOG = "https://blog.tristanhotham.com/2026/10/31/remote-places/"          # filled in by the publisher
GEONAMES_URL = "https://www.geonames.org/"
CITIES_JSON_URL = "https://github.com/lutangar/cities.json"
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")

RE_KM = 6371.0088              # mean Earth radius (IUGG), km
RES = 0.1                      # grid step, degrees
NX, NY = int(360 / RES), int(180 / RES)
FINE = 0.01                    # refinement step, degrees
THRESH = [100, 500]            # "far from any town" thresholds, km

# the four distance measures: key, short name, long name, colour used for the measure in charts
MEASURES = [("town", "a town", "nearest place of 1,000+ people (GeoNames)", "#B4462E"),
            ("c100k", "a city of 100,000+", "nearest city of 100,000+ (Natural Earth)", "#2F6F8F"),
            ("c1m", "a city of a million", "nearest city of 1,000,000+ (Natural Earth)", "#5B4B8A"),
            ("coast", "the sea", "nearest coast (Natural Earth 1:50m)", "#2E8B74")]
MKEYS = [m[0] for m in MEASURES]

# continents: Natural Earth's CONTINENT field, with Russia east of 60 degrees east counted as Asia (the Urals)
CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Australia and Oceania", "Antarctica"]
CONT_FIX = {"Oceania": "Australia and Oceania", "Seven seas (open ocean)": None}

# Natural Earth admin 0 features left out of the country lists (bases, buffer zones, reefs, banks, glaciers in dispute,
# tiny unpopulated rocks). Their land still counts in every global and continental figure.
SKIP = {"Dhekelia", "Akrotiri", "Cyprus U.N. Buffer Zone", "Siachen Glacier", "Southern Patagonian Ice Field", "Bir Tawil",
        "Spratly Is.", "Bajo Nuevo Bank", "Serranilla Bank", "Scarborough Reef", "Coral Sea Is.", "Ashmore and Cartier Is.",
        "Clipperton I.", "Brazilian I.", "USNB Guantanamo Bay", "Baikonur", "Indian Ocean Ter.", "U.S. Minor Outlying Is."}
COUNTRY_TYPES = {"Sovereign country", "Country", "Sovereignty"}
COUNTRY_EXTRA = {"Israel", "Kosovo", "Palestine", "W. Sahara"}
NAME_FIX = {"United States of America": "United States", "People's Republic of China": "China", "Republic of the Congo": "Congo",
            "Democratic Republic of the Congo": "DR Congo", "The Bahamas": "Bahamas", "The Gambia": "Gambia",
            "Federated States of Micronesia": "Micronesia", "Fr. S. Antarctic Lands": "French Southern Lands",
            "S. Geo. and the Is.": "South Georgia and South Sandwich Islands", "Heard I. and McDonald Is.": "Heard and McDonald Islands",
            "Br. Indian Ocean Ter.": "British Indian Ocean Territory", "W. Sahara": "Western Sahara", "Falkland Is.": "Falkland Islands",
            "Faeroe Is.": "Faroe Islands", "Republic of Serbia": "Serbia", "United Republic of Tanzania": "Tanzania",
            "East Timor": "Timor-Leste", "Macao S.A.R": "Macao", "Hong Kong S.A.R.": "Hong Kong", "Åland": "Aland Islands",
            "Federation of Bosnia and Herzegovina": "Bosnia and Herzegovina", "Northern Cyprus": "Northern Cyprus",
            "Turkish Republic of Northern Cyprus": "Northern Cyprus", "Republic of Cyprus": "Cyprus", "Kingdom of Eswatini": "Eswatini",
            "North Macedonia": "North Macedonia", "Ivory Coast": "Ivory Coast", "Côte d'Ivoire": "Ivory Coast", "Curaçao": "Curacao",
            "Saint Barthélemy": "Saint Barthelemy", "São Tomé and Príncipe": "Sao Tome and Principe"}

# famous candidates checked by name: region boxes (lon0, lat0, lon1, lat1) or a country code, and the measure to maximise
EURASIA_POLE = (46.2833, 86.6667)   # the far-from-coast pole of inaccessibility of Eurasia, about 46 17 N 86 40 E (Dzungaria)
CANDIDATES = [
    ("Sahara", "box", (-17.0, 15.0, 35.0, 31.0), "town"),
    ("Rub' al Khali (Empty Quarter)", "box", (44.0, 16.0, 56.5, 24.0), "town"),
    ("Tibet's Changtang", "box", (78.0, 31.5, 92.0, 37.0), "town"),
    ("Australian interior", "iso", "AUS", "town"),
    ("Greenland", "iso", "GRL", "town"),
    ("Northern Canada (north of 60 N)", "boxiso", ((-142.0, 60.0, -52.0, 84.0), "CAN"), "town"),
    ("Siberia (mainland Russia east of 60 E)", "boxiso", ((60.0, 45.0, 180.0, 82.0), "RUS"), "town"),
    ("Amazon (Brazil)", "iso", "BRA", "town"),
]
UK_NATIONS = ["Scotland", "England", "Wales", "Northern Ireland"]


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def dash(v):
    """Remove em and en dashes and double hyphens from text (house style)."""
    if isinstance(v, str):
        v = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", v)
        v = v.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", "-")
        while "--" in v:
            v = v.replace("--", "-")
        return v
    if isinstance(v, list):
        return [dash(x) for x in v]
    if isinstance(v, dict):
        return {k: dash(x) for k, x in v.items()}
    return v


def jsave(obj, path, indent=None):
    if os.path.abspath(path).startswith(DATA):
        obj = dash(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, separators=None if indent else (",", ":"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"[\W_]+", " ", s).strip()


def get(R, path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f == "k": return f"{float(v) / 1000:.1f}"
    if f == "m": return f"{float(v) / 1e6:.1f}"
    if f == "lat": v = float(v); return f"{abs(v):.2f}°{'N' if v >= 0 else 'S'}"
    if f == "lon": v = float(v); return f"{abs(v):.2f}°{'E' if v >= 0 else 'W'}"
    raise ValueError(f)


def ll(lat, lon, k=2):
    """Latitude and longitude in words, e.g. 57.81°N 5.27°W."""
    return f"{abs(lat):.{k}f}°{'N' if lat >= 0 else 'S'} {abs(lon):.{k}f}°{'E' if lon >= 0 else 'W'}"


def unit(lat, lon):
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def chord_km(c):
    """Great-circle distance (km) from the chord length between two unit vectors."""
    return 2 * RE_KM * np.arcsin(np.clip(np.asarray(c) / 2, 0, 1))


def gc_km(lat1, lon1, lat2, lon2):
    p1, p2, l1, l2 = map(np.radians, (lat1, lat2, lon1, lon2))
    return 2 * RE_KM * np.arcsin(np.sqrt(np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2))


def cell_area_km2(lat_c, res=RES):
    """Exact area of a res x res degree cell centred on latitude lat_c."""
    a, b = np.radians(lat_c - res / 2), np.radians(lat_c + res / 2)
    return RE_KM ** 2 * np.radians(res) * (np.sin(b) - np.sin(a))


GRID_LAT = 90 - RES / 2 - RES * np.arange(NY)        # row j centre latitude (north to south)
GRID_LON = -180 + RES / 2 + RES * np.arange(NX)      # column i centre longitude

# colour classes for the distance maps (km) and their colours, pale near towns to dark in the middle of nowhere
BINS = [0, 10, 25, 50, 100, 250, 500, 1000, 2000, 3000]
BIN_COL = ["#FFF6DD", "#FCE3A8", "#F7C978", "#EFA658", "#DD7A40", "#BF4F3A", "#963247", "#6A2353", "#43184E", "#22102F"]
BIN_LAB = ["under 10 km", "10 to 25", "25 to 50", "50 to 100", "100 to 250", "250 to 500", "500 to 1,000", "1,000 to 2,000", "2,000 to 3,000", "over 3,000 km"]
MERC_LAT = 85.0511287798


def grid2d(G, key):
    """Full 1,800 x 3,600 array of one distance measure, NaN over the sea."""
    a = np.full((NY, NX), np.nan, np.float32); a[G["J"], G["I"]] = G["d_" + key]; return a


def binof(d):
    return np.clip(np.searchsorted(BINS, d, side="right") - 1, 0, len(BINS) - 1)
