"""README.md, LICENSE and reddit/post.md, with numbers from data/results.json."""
from common import *

R = jload(f"{DATA}/results.json")
s, sh, CN, U, A, EU = R["source"], R["share"], R["continents"], R["uk"], R["antarctica"], R["eurasia"]
N = lambda v: f"{round(v):,}"
c = lambda k: CN[k]["town"]
readme = f"""# The middle of nowhere: the most remote places on Earth, measured from every town

A computed map of remoteness. For every point on land, the great-circle distance to the nearest place of 1,000 or more people ({N(s['towns'])} places in the GeoNames cities1000 gazetteer), the nearest city of 100,000+ and of 1,000,000+ (Natural Earth) and the nearest coast; the most remote point of every continent, large island, country and territory; and the same for the United Kingdom.

Interactive page: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}

## Headline results

- Outside Antarctica, {sh['town']['100']:.1f}% of the land ({sh['town']['100_m']:.1f} million km²) is more than 100 km from a town of 1,000+, and {sh['town']['500']:.1f}% more than 500 km. Half of the land is within {N(sh['town']['median'])} km of a town, {N(sh['c100k']['median'])} km of a city of 100,000+, {N(sh['c1m']['median'])} km of a city of a million and {N(sh['coast']['median'])} km of the sea.
- Land north of 60°N is {R['north']['north60_land_pct']:.0f}% of the land outside Antarctica but {R['north']['far100_share_north60']:.0f}% of the land over 100 km from a town and {R['north']['far500_share_north60']:.0f}% of the land over 500 km away.
- Most remote point of each mainland from a town: Asia, Cape Chelyuskin, {N(c('Asia')['d'])} km; Australia, Great Victoria Desert, {N(c('Australia and Oceania')['d'])} km; Africa, Libyan Desert of Sudan, {N(c('Africa')['d'])} km; North America, northern Saskatchewan, {N(c('North America')['d'])} km; South America, northern Pará, {N(c('South America')['d'])} km; Europe, north-eastern European Russia, {N(c('Europe')['d'])} km.
- Islands: Marion Island (Prince Edward Islands), {N(R['scraps'][0]['d'])} km from a town, is the most remote land outside Antarctica; Cape Columbia on Ellesmere Island {N(R['isl']['Ellesmere Island']['d'])} km. Antarctica has no towns in the gazetteer: every point is at least {N(A['min_town'])} km from one, the most remote {N(A['max']['d'])} km.
- Far from the sea is not far from people: the Eurasian pole of inaccessibility (here {EU['ours']['lat']:.2f}°N {EU['ours']['lon']:.2f}°E, {N(EU['ours']['d'])} km from the coast, {N(EU['sep_km'])} km from the usual 46°17′N 86°40′E) is {N(EU['ours_town'])} km from a town.
- Countries: on its main land mass, Greenland reaches farthest from a town ({N(R['countries_main_top'][0]['d'])} km), then Russia, Australia, Sudan and Canada. For {R['n_abroad']} countries the nearest town to the most remote point is in another country.
- United Kingdom: near Cape Wrath, {N(U['Scotland']['d'])} km from {U['Scotland']['town_name']}; England, Kielder Forest, {N(U['England']['d'])} km (nearest town {U['England']['town_name']}, in Scotland); Wales, tip of the Llŷn, {N(U['Wales']['d'])} km; Northern Ireland, the Sperrins, {N(U['Northern Ireland']['d'])} km.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/04_build_site.py`; results and page data embedded; loads `data/world.json`, `data/cities.json`, the map tiles in `img/tiles/`, and on demand `data/towns.json` and `data/coast.json`). |
| `header.png` | Social card, 1200 x 630. |
| `data/land_distances_0p1deg.csv.gz` | Every land cell of the 0.1° grid ({N(s['land_cells'])} rows): centre, area, km to the nearest town, city of 100,000+, city of 1,000,000+ and coast, continent and country. |
| `data/country_remote_points.csv` | Every country and territory: most remote point from a town (anywhere and on the main land mass), nearest town, km to coast and cities, share of land over 25 and 100 km from a town, mean distance. |
| `data/continent_poles.csv` | Most remote point of each mainland for each measure, and of each continent with its islands. |
| `data/islands.csv`, `data/famous_candidates.csv`, `data/gb_remote_spots.csv` | Big islands; regions often named as the emptiest; the ten most remote spots on Great Britain. |
| `data/land_share_by_distance.csv` | Share of land outside Antarctica within each distance of a town, city and coast. |
| `data/results.json` | Every number used in the page, paper, blog, collage and post. |
| `data/site.json`, `data/world.json`, `data/cities.json`, `data/towns.json`, `data/coast.json` | Page data (towns and coast packed; see the note inside each file). |
| `img/tiles/` | The four distance maps as Web Mercator raster tiles (zoom 0 to 3, 512 px). |
| `code/` | Scripts, run in order (below), and the page, paper and blog templates. |
| `release/` | Paper PDF and LaTeX source with figures (`paper/`), blog post, figures and meta (`blog/`), Zenodo files (`zenodo/`). |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |
| `qa/` | Screenshots of the page at desktop and phone widths. |

## Method in brief

- Grid: 0.1° latitude and longitude over Natural Earth 1:50m land, cell centres tested against the polygons (coastal cells exactly), {N(s['land_cells'])} land cells, each weighted by its true area on the sphere.
- Distances: great-circle, sphere of radius {s['radius_km']} km, via a k-d tree on unit vectors. Coast: the land outline densified to 0.02°. Lakes are land; the Caspian is sea; Antarctica's outline excludes ice shelves.
- Maxima: refined on a 0.01° grid inside the region (about 1 km). A country's most remote point is the point inside its 1:10m outline farthest from any town, at home or abroad. UK figures use a 0.005° grid and Natural Earth's first-level divisions.
- Antarctica is reported separately and left out of the world shares: its stations are not in the gazetteer.
- Caveats: cities1000 misses villages and hamlets under 1,000 people and keeps a few smaller administrative seats (for example Port-aux-Français on Kerguelen); Natural Earth populations are estimates; straight-line distance is not travel time (compare the Malaria Atlas Project's 2015 accessibility map, Weiss and others, Nature, 2018).

## How to rerun

Needs Python 3 with numpy, pandas, scipy, shapely 2, pyproj, Pillow, matplotlib and fontTools, xelatex and pdftotext; node with Playwright for `code/qa.js`. Raw inputs: `raw/geonames_cities1000.json` (GeoNames cities1000 as packaged by lutangar/cities.json, commit in `raw/cities_json_commit.txt`) and Natural Earth in `/home/claude/newdata/raw/geo/` (set `RP_GEO`). Intermediate files go to `/dev/shm/remoteplaces/work` (set `RPTMP`).

```
python3 code/01_grid.py         # read inputs, land grid, distances for every land cell
python3 code/02_geo.py          # outlines, map tiles, point files for the page
python3 code/03_results.py      # results.json, data tables, page data
python3 code/04_build_site.py   # index.html
python3 code/05_figures.py      # header, blog and paper figures
python3 code/06_paper.py        # paper PDF
python3 reddit/collage.py       # collage
python3 code/07_readme.py       # README, LICENSE, Reddit post
python3 code/08_release.py      # blog post, Zenodo files
```

## Sources and licences

- GeoNames, cities1000 (https://www.geonames.org/), CC BY 4.0, via lutangar/cities.json (https://github.com/lutangar/cities.json), commit {s['commit']}.
- Natural Earth populated places, land, countries and first-level divisions (https://www.naturalearthdata.com/). Public domain.
- Base map tiles on the page: © Esri; place labels © OpenFreeMap, OpenMapTiles, OpenStreetMap contributors.

## Citation

Hotham, T. (2026) The middle of nowhere: the most remote places on Earth, measured from every town. Zenodo. https://doi.org/{DOI}

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

{AI}
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)

lic = open("/home/claude/studies/meteorite-falls/LICENSE", encoding="utf-8").read().split("\n\n\nThis licence covers")[0]
lic += """


This licence covers the code in code/, reddit/collage.py and the page scripts.
The text of the page, paper and blog post, the figures, the map tiles and the
derived data files in data/ are released under CC BY 4.0. Town data come from
GeoNames (www.geonames.org), CC BY 4.0: please credit "GeoNames". City
populations, land, coast and country outlines come from Natural Earth, which is
in the public domain.
"""
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write(lic)

post = f"""## Title

[OC] The middle of nowhere: I measured how far every point on land is from the nearest town. A quarter of the land outside Antarctica is more than 100 km from a place of 1,000 people

## Body

I measured the straight-line distance from every point on land (a 0.1° grid, {N(s['land_cells'])} cells) to the nearest of {N(s['towns'])} places with 1,000+ people in the GeoNames gazetteer, and to the nearest city and coast. {sh['town']['100']:.0f}% of the land outside Antarctica is more than 100 km from a town, but only {sh['town']['500']:.1f}% is more than 500 km away. The most remote mainland spots: Cape Chelyuskin in Siberia ({N(c('Asia')['d'])} km), the Great Victoria Desert in Australia ({N(c('Australia and Oceania')['d'])} km) and the Libyan Desert of Sudan ({N(c('Africa')['d'])} km). Counting islands, Marion Island in the Southern Ocean is {N(R['scraps'][0]['d'])} km from a town. The famous pole of inaccessibility in China, the land farthest from the sea, is just {N(EU['ours_town'])} km from one. In Britain the most remote spot is near Cape Wrath, {N(U['Scotland']['d'])} km from {U['Scotland']['town_name']}; England's is Kielder Forest, whose nearest town is in Scotland. Caveats: villages under 1,000 people are not counted, and Antarctica's research stations are not towns. Interactive map where you can pick any country or click anywhere: {PAGE}

## Source comment

Source: GeoNames cities1000 (geonames.org, CC BY 4.0, via lutangar/cities.json) for towns; Natural Earth for cities of 100,000+ and 1,000,000+, land, coast and countries. Great-circle distances on a 0.1° area-weighted grid with a k-d tree; maxima refined to 0.01°.

Tools: Python (numpy, scipy, shapely, pyproj, matplotlib); MapLibre for the interactive map.

Interactive version: {PAGE}
Paper: https://doi.org/{DOI}
Blog post: {BLOG}
"""
assert round(sh["town"]["100"]) == 25
for t in (readme, post):
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv"):
        assert bad not in t.replace("```", "").replace("|---|---|", ""), bad
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(post)
print("readme, licence, post ok")
