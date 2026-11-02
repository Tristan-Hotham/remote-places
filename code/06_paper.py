"""Build the paper: fill code/paper_template.tex from data/results.json, add tables, compile with xelatex.
Output: release/paper/<NAME>.pdf and .tex (figures f_*.png sit beside them). The DOI stays as the 10.5281/zenodo.23873015 placeholder."""
import subprocess
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Middle_of_Nowhere"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")
L = lambda la, lo: f"{abs(la):.2f}{'N' if la >= 0 else 'S'} {abs(lo):.2f}{'E' if lo >= 0 else 'W'}"

# statements made in words in the paper only
assert round(R["share"]["town"]["500"]) == 1                                                         # "only about one per cent"
assert R["isl"]["Ellesmere Island"]["d"] > max(R["cand"][c]["d"] for c in ("Sahara", "Changtang", "Rub al Khali", "Australian interior", "Siberia", "Amazon"))   # "exceed them all"
assert R["eurasia"]["ref_town"] < 100 and R["eurasia"]["ours_town"] < 100
assert R["continents"]["Asia"]["coast"]["d"] == R["global"]["coast"]["world"]["d"]


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pc": return f"{round(float(v))}\\%"
    if f == "pc1": return f"{float(v):.1f}\\%"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f in ("lat", "lon"):
        v = float(v); return f"{abs(v):.2f}\\textdegree{{}}" + ("N" if v >= 0 else "S") if f == "lat" else f"{abs(v):.2f}\\textdegree{{}}" + ("E" if v >= 0 else "W")
    return tex(str(v))


CN = R["continents_list"]
rows = "".join(f"{tex(c['mainland'].replace('mainland ', ''))} & {c['town']['d']:,.0f} & {L(c['town']['lat'], c['town']['lon'])} & {tex(c['town']['town_name'])} & {c['c100k']['d']:,.0f} & {c['c1m']['d']:,.0f} & {c['coast']['d']:,.0f} & {L(c['coast']['lat'], c['coast']['lon'])}\\\\\n" for c in CN)
TC = ("\\begin{table}[tbp]\\centering\\footnotesize\\setlength{\\tabcolsep}{4pt}\\caption{The most remote point of each mainland: km to the nearest town, its position and the town; km from the most remote points for cities of 100,000+ and 1,000,000+ and for the coast, with the position of the coast maximum.}\\label{tab:cont}"
      "\\begin{tabular}{lrllrrrl}\\toprule Mainland & Town & Where & Nearest town & 100k & 1m & Coast & Where\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(p['island'])} & {p['km2']:,} & {p['d']:,.0f} & {L(p['lat'], p['lon'])} & {tex(p['town_name'])} & {p['far100']:.1f}\\%\\\\\n" for p in R["islands"])
TI = ("\\begin{table}[tbp]\\centering\\small\\caption{The fifteen largest islands: grid area, the most remote point from a town and the share of the island more than 100 km from one.}\\label{tab:isl}"
      "\\begin{tabular}{lrrllr}\\toprule Island & km\\textsuperscript{2} & km to town & Where & Nearest town & Over 100 km\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(p['name'])} & {p['d']:,.0f} & {L(p['lat'], p['lon'])} & {tex(p['town_name'])} ({tex(p['town_country'])}) & {p['far100']:.1f}\\%\\\\\n" for p in R["candidates"])
TA = ("\\begin{table}[tbp]\\centering\\small\\caption{Famous empty places: the most remote point from a town within each region and the share of the region more than 100 km from one. Regions are boxes or countries (see code/common.py).}\\label{tab:cand}"
      "\\begin{tabular}{lrllr}\\toprule Region & km to town & Where & Nearest town & Over 100 km\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
K = R["countries"]
rows = "".join(f"{tex(r['name'])} & {r['d']:,.0f} & {L(r['lat'], r['lon'])} & {tex(r['town'])}{'' if r['town_country'] == r['name'] else ' (' + tex(r['town_country']) + ')'} & {r['any_d']:,.0f} & {K[r['name']]['far100']:.1f}\\%\\\\\n" for r in R["countries_main_top"][:25])
TY = ("\\begin{table}[tbp]\\centering\\footnotesize\\caption{The 25 countries over 100,000 km\\textsuperscript{2} whose main land mass reaches farthest from a town: km, position and nearest town (country if different); km counting all islands; share of the country more than 100 km from a town. All countries and territories are in data/country\\_remote\\_points.csv.}\\label{tab:cty}"
      "\\begin{tabular}{lrllrr}\\toprule Country & km & Where & Nearest town & With islands & Over 100 km\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = re.sub(r"\{\{(?!TABLE_|meta\.doi)([^}|]+)(\|(\w+))?\}\}", lambda m: tfmt(get(R, m.group(1)), m.group(3) or "raw"), t)
fit = lambda T: T.replace("\\begin{tabular}", "\\resizebox{\\textwidth}{!}{\\begin{tabular}").replace("\\end{tabular}", "\\end{tabular}}")
TC, TA, TY = fit(TC), fit(TA), fit(TY)
for k, v in (("CONT", TC), ("ISL", TI), ("CAND", TA), ("CTY", TY)):
    t = t.replace("{{TABLE_%s}}" % k, v)
t = t.replace("\\href{https://doi.org/{{meta.doi}}}{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
t = t.replace("\\url{https://doi.org/{{meta.doi}}}", "https://doi.org/\\{\\{DOI\\}\\}")
assert "{{" not in t and "--" not in t and "\u2014" not in t and "\u2013" not in t, re.findall(r"\{\{[^}]*\}\}", t)[:4]
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:12])
for ext in (".aux", ".log", ".out"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("\u2014") + txt.count("\u2013") + txt.count("--"))
