# The middle of nowhere: the most remote places on Earth, measured from every town

A computed map of remoteness. For every point on land, the great-circle distance to the nearest place of 1,000 or more people (171,737 places in the GeoNames cities1000 gazetteer), the nearest city of 100,000+ and of 1,000,000+ (Natural Earth) and the nearest coast; the most remote point of every continent, large island, country and territory; and the same for the United Kingdom.

Interactive page: https://maps.tristanhotham.com/remote-places/
Paper: https://doi.org/10.5281/zenodo.23873015
Blog post: https://blog.tristanhotham.com/2026/10/31/remote-places/

## Headline results

- Outside Antarctica, 24.6% of the land (33.1 million km²) is more than 100 km from a town of 1,000+, and 1.3% more than 500 km. Half of the land is within 40 km of a town, 175 km of a city of 100,000+, 458 km of a city of a million and 400 km of the sea.
- Land north of 60°N is 13% of the land outside Antarctica but 35% of the land over 100 km from a town and 93% of the land over 500 km away.
- Most remote point of each mainland from a town: Asia, Cape Chelyuskin, 641 km; Australia, Great Victoria Desert, 579 km; Africa, Libyan Desert of Sudan, 517 km; North America, northern Saskatchewan, 506 km; South America, northern Pará, 364 km; Europe, north-eastern European Russia, 288 km.
- Islands: Marion Island (Prince Edward Islands), 1,749 km from a town, is the most remote land outside Antarctica; Cape Columbia on Ellesmere Island 1,170 km. Antarctica has no towns in the gazetteer: every point is at least 879 km from one, the most remote 4,367 km.
- Far from the sea is not far from people: the Eurasian pole of inaccessibility (here 45.83°N 88.76°E, 2,478 km from the coast, 169 km from the usual 46°17′N 86°40′E) is 65 km from a town.
- Countries: on its main land mass, Greenland reaches farthest from a town (1,162 km), then Russia, Australia, Sudan and Canada. For 34 countries the nearest town to the most remote point is in another country.
- United Kingdom: near Cape Wrath, 82 km from Ullapool; England, Kielder Forest, 24 km (nearest town Langholm, in Scotland); Wales, tip of the Llŷn, 23 km; Northern Ireland, the Sperrins, 20 km.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/04_build_site.py`; results and page data embedded; loads `data/world.json`, `data/cities.json`, the map tiles in `img/tiles/`, and on demand `data/towns.json` and `data/coast.json`). |
| `header.png` | Social card, 1200 x 630. |
| `data/land_distances_0p1deg.csv.gz` (in the Zenodo archive only, 21 MB) | Every land cell of the 0.1° grid (2,147,063 rows): centre, area, km to the nearest town, city of 100,000+, city of 1,000,000+ and coast, continent and country. |
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

- Grid: 0.1° latitude and longitude over Natural Earth 1:50m land, cell centres tested against the polygons (coastal cells exactly), 2,147,063 land cells, each weighted by its true area on the sphere.
- Distances: great-circle, sphere of radius 6371.0088 km, via a k-d tree on unit vectors. Coast: the land outline densified to 0.02°. Lakes are land; the Caspian is sea; Antarctica's outline excludes ice shelves.
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

- GeoNames, cities1000 (https://www.geonames.org/), CC BY 4.0, via lutangar/cities.json (https://github.com/lutangar/cities.json), commit e5e759c56751bd7329e29c576f6a9e77607b424e.
- Natural Earth populated places, land, countries and first-level divisions (https://www.naturalearthdata.com/). Public domain.
- Base map tiles on the page: © Esri; place labels © OpenFreeMap, OpenMapTiles, OpenStreetMap contributors.

## Citation

Hotham, T. (2026) The middle of nowhere: the most remote places on Earth, measured from every town. Zenodo. https://doi.org/10.5281/zenodo.23873015

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
