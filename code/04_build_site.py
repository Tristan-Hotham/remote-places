"""Build index.html from code/page_template.html. Every number in the text is a {{path|format}} token filled from
data/results.json; page data (results and site.json) is embedded; data/world.json, data/cities.json, img/d_*.png and,
on demand, data/towns.json and data/coast.json are loaded by the page. Facts stated in words (place names, rankings,
"a quarter") are checked here. The full-screen map snippet (code/fullscreen_snippet.html) is pasted before </body>.
10.5281/zenodo.23873015 and https://blog.tristanhotham.com/2026/10/31/remote-places/ stay as placeholders for the publisher."""
import json
from common import *

R = jload(f"{DATA}/results.json")
SITE = jload(f"{DATA}/site.json")
CN, U, K, SC, ISL, EU = R["continents"], R["uk"], R["countries"], R["scraps"], R["isl"], R["eurasia"]
inbox = lambda p, la0, la1, lo0, lo1: la0 <= p["lat"] <= la1 and lo0 <= p["lon"] <= lo1

# facts stated in words (page, blog, paper, collage)
assert round(R["share"]["town"]["100"]) == 25                                                  # "a quarter of the land"
assert R["source"]["towns_south_60"] == 0                                                        # no town in Antarctica
assert EU["ours"]["country"] == "China" and EU["ours"]["c1m_pop"] > 2e6 and EU["ours"]["c1m_name"] == "Ürümqi"   # Dzungaria; "a city of several million"
assert EU["ours"]["town"] < 100 and 40 < EU["ours"]["lat"] < 48 and 82 < EU["ours"]["lon"] < 92
assert inbox(CN["Asia"]["town"], 77.5, 77.95, 103.5, 105.0)                                      # Cape Chelyuskin, Taymyr
assert CN["Australia and Oceania"]["town"]["country"] == "Australia" and inbox(CN["Australia and Oceania"]["town"], -31, -27, 127.5, 129.0)   # Great Victoria Desert, WA near SA
assert CN["Africa"]["town"]["country"] == "Sudan" and inbox(CN["Africa"]["town"], 19.5, 21, 24, 26.5)          # Libyan Desert, NW Sudan
assert CN["North America"]["town"]["country"] == "Canada" and inbox(CN["North America"]["town"], 59.5, 60, -104, -102)   # far north Saskatchewan
assert CN["South America"]["town"]["country"] == "Brazil" and inbox(CN["South America"]["town"], .5, 2.3, -58, -54.5)     # northern Para near Suriname
assert CN["Europe"]["town"]["country"] == "Russia" and inbox(CN["Europe"]["town"], 68, 71, 58, 61)               # NE corner of European Russia, Kara Sea
assert SC[1]["town_name"] == "Port-aux-Français" and SC[0]["town_name"] == "Port Alfred"                         # Kerguelen base; Eastern Cape
assert inbox(ISL["Ellesmere Island"], 82.9, 83.3, -70.5, -69.3) and ISL["Greenland"]["lat"] > 82.5             # Cape Columbia; north coast of Greenland
assert CN["Africa"]["coast"]["country"] == "Central African Republic" and CN["Africa"]["coast"]["town_name"] == "Obo"
assert CN["North America"]["coast"]["country"] == "United States" and inbox(CN["North America"]["coast"], 42.5, 45.9, -104.05, -96.5)   # South Dakota
assert CN["South America"]["coast"]["country"] == "Brazil" and inbox(CN["South America"]["coast"], -16, -12, -58.5, -55)               # Mato Grosso
assert CN["Australia and Oceania"]["coast"]["country"] == "Australia" and inbox(CN["Australia and Oceania"]["coast"], -24.5, -22, 131, 133.5)   # west of Alice Springs
assert [r["name"] for r in R["countries_top"][:5]] == ["South Africa", "Canada", "Greenland", "United States", "Russia"]
assert K["United States"]["town_country"] == "Russia" and K["Russia"]["town_name"] == "Longyearbyen" and inbox(K["United States"], 51, 53, 172, 180)   # western Aleutians
assert inbox(K["Russia"], 79.8, 82, 44, 66)                                                      # Franz Josef Land
assert [r["name"] for r in R["countries_main_top"][:5]] == ["Greenland", "Russia", "Australia", "Sudan", "Canada"]
assert (K["Libya"]["town_country"], K["Egypt"]["town_country"], K["Saudi Arabia"]["town_country"]) == ("Chad", "Libya", "Yemen")
assert inbox(U["Scotland"], 58.5, 58.7, -5.05, -4.85) and U["Scotland"]["unit"] == "Highland"   # near Cape Wrath
assert sum(s["unit"] == "Highland" for s in R["gb_spots"]) >= 8                                  # "almost all ... Highland"
assert inbox(U["England"], 55.1, 55.35, -2.75, -2.4) and U["England"]["unit"] == "Northumberland" and U["England"]["town_name"] == "Langholm"   # Kielder; Langholm is in Scotland
assert inbox(U["England"]["with_islands"], 51.15, 51.23, -4.71, -4.63)                           # Lundy
assert inbox(U["Wales"], 52.7, 52.85, -4.85, -4.65) and U["Wales"]["unit"] == "Gwynedd"           # tip of the Llyn Peninsula
assert inbox(U["Northern Ireland"], 54.6, 54.9, -7.3, -6.8)                                       # Sperrin Mountains
assert inbox(R["global"]["c100k"]["world"], -53.3, -52.9, 73.2, 73.9) and R["global"]["c100k"]["world"]["country"] == "Heard and McDonald Islands"
assert inbox(R["global"]["c1m"]["world"], -10.5, -7.5, -141, -138.5) and R["global"]["c1m"]["world"]["country"] == "French Polynesia"   # the Marquesas
assert R["antarctica"]["max"]["lat"] < -80                                                       # the polar plateau
assert R["north"]["far500_share_north60"] > 90


def build():
    tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
    html = re.sub(r"\{\{(?!DOI\}\}|BLOG_URL\}\})([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(R, m.group(1)), m.group(3)), tpl)
    left = re.findall(r"\{\{[^}]*\}\}", html)
    assert set(left) <= {"10.5281/zenodo.23873015", "https://blog.tristanhotham.com/2026/10/31/remote-places/"}, left[:5]
    J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    RS = {k: v for k, v in R.items() if k not in ("countries",)}
    html = html.replace("/*RESULTS*/", J(RS)).replace("/*SITE*/", J(SITE))
    html = html.replace("/*FULLSCREEN*/", open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read())
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv"):
        assert bad not in vis, bad
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        for bad in ("—", "–"):
            assert bad not in scr, bad
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()) // 1024, "KB")


if __name__ == "__main__":
    build()
