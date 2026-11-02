"""Blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.23873015, https://doi.org/10.5281/zenodo.23873015 and https://blog.tristanhotham.com/2026/10/31/remote-places/ stay as placeholders for the publisher."""
import json as _json, shutil, zipfile, importlib.util
from common import *

R = jload(f"{DATA}/results.json")
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Middle_of_Nowhere"

# the page build checks the shared facts; these are statements in the blog text and alt text
spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "code", "04_build_site.py")); spec.loader.exec_module(importlib.util.module_from_spec(spec))
CN = R["continents"]
assert max(CN, key=lambda c: CN[c]["town"]["d"] if c != "Antarctica" else 0) == "Asia"                 # "Asia leads" from a town
assert max((c for c in CN if c != "Antarctica"), key=lambda c: CN[c]["c100k"]["d"]) == "North America"   # from a city of 100,000
assert max((c for c in CN if c != "Antarctica"), key=lambda c: CN[c]["c1m"]["d"]) == "Asia"              # from a city of a million
assert max((c for c in CN if c != "Antarctica"), key=lambda c: CN[c]["coast"]["d"]) == "Asia"            # from the sea
assert 68 < CN["Asia"]["c1m"]["lat"] < 70 and (CN["Asia"]["c1m"]["lon"] < -170 or CN["Asia"]["c1m"]["lon"] > 170)   # Chukotka
assert 66 < CN["North America"]["c1m"]["lat"] < 70 and -168 < CN["North America"]["c1m"]["lon"] < -160 and CN["North America"]["c1m"]["country"] == "United States"   # NW Alaska
assert CN["South America"]["c1m"]["lat"] < -53                                                          # southern tip
assert {"Libya", "Egypt", "Mauritania", "Algeria", "Saudi Arabia"} <= {r["name"] for r in R["countries_main_top"][:20] if r["town_country"] != r["name"]}   # purple bars named in alt text
assert sum(s["unit"] == "Highland" for s in R["gb_spots"]) > 5                                         # "most of them in Highland"

post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = re.sub(r"\{\{(?!IMG|DOI_URL|BLOG_URL|DOI\}\})([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(R, m.group(1)), m.group(3)), post)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u), post, re.M) for u in used) and "wp:image" not in post
for img in used:
    assert os.path.exists(f"{REL}/blog/{img}"), img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{[^|}]+\}\}", post)) <= {"https://doi.org/10.5281/zenodo.23873015"}
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
for bad in ("\u2014", "\u2013", "--", "DSIT", "DCMS", "civil serv"):
    assert bad not in vis, bad
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
sh = R["share"]["town"]
meta = {"title": "The middle of nowhere: the places on Earth farthest from any town",
        "slug": "remote-places",
        "excerpt": f"I measured how far every point on land is from the nearest town of 1,000 people. A quarter of the land outside Antarctica is more than 100 km from one; the most landlocked place on Earth is just {R['eurasia']['ours_town']:.0f} km from one; and Britain's middle of nowhere is near Cape Wrath.",
        "seo_description": f"How far is every point on land from a town? {sh['100']:.0f}% of land is over 100 km from one. The most remote places on each continent, in every country and in Britain.",
        "tags": ["maps", "geography", "data visualisation", "remoteness", "pole of inaccessibility", "GeoNames", "Natural Earth", "wilderness"],
        "header_alt": "Title card reading 'The middle of nowhere' in black and red on pale paper, beside a world map coloured by distance to the nearest town: pale cream across Europe, India and China, orange and red over the Sahara, Siberia, Canada and Australia, and dark purple over Greenland and Antarctica. Text: the places on Earth farthest from any town; a quarter of the land outside Antarctica is more than 100 km from a place of 1,000 people."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# Zenodo
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/remote-places_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for d in ("code", "data"):
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            if fn.endswith(".pyc") or fn == "__pycache__":
                continue
            z.write(os.path.join(ROOT, d, fn), f"remote-places/{d}/{fn}")
    for fn in ("README.md", "LICENSE"):
        z.write(os.path.join(ROOT, fn), f"remote-places/{fn}")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), "remote-places/reddit/collage.py")
    z.write(os.path.join(RAW, "cities_json_commit.txt"), "remote-places/raw/cities_json_commit.txt")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("\\textdegree{}", "°").replace("\\textdegree ", "°").replace("\\textdegree", "°").replace("\\textsuperscript{2}", "²").replace("\\'a", "á")
assert "\\" not in ab, re.findall(r"\\\w+", ab)[:5]
zmeta = {"title": "The Middle of Nowhere: The Most Remote Places on Earth, Measured from Every Town",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {BLOG}.</p><p>Town data: GeoNames (www.geonames.org), CC BY 4.0. Cities, land and countries: Natural Earth (public domain).</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["remoteness", "pole of inaccessibility", "settlement", "accessibility", "GeoNames", "Natural Earth", "great-circle distance", "wilderness", "open data", "maps"],
         "license": "cc-by-4.0", "language": "eng",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": GEONAMES_URL, "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": CITIES_JSON_URL, "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj
jsave(zmeta, f"{Z}/metadata.json", indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
