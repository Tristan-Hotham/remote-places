// QA: open index.html at desktop and phone widths, log console errors, take screenshots to qa/.
// Run from the study root with a static server (python3 -m http.server 47321; set PORT to change).
const { chromium } = require("playwright");
// MapLibre from a local npm copy (the CDN is not reachable from the build container); tiles, labels and fonts are blocked here.
const ML = process.env.MAPLIBRE_DIST || "/tmp/ml/node_modules/maplibre-gl/dist";
const fs = require("fs"); fs.mkdirSync("qa", { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const errs = [];
  for (const [nm, vw, vh] of (process.env.ONLY ? [[process.env.ONLY, process.env.ONLY === "phone" ? 390 : 1280, 900]] : [["desktop", 1280, 900], ["phone", 390, 844]])) {
    const p = await b.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: nm === "phone" ? 2 : 1 });
    await p.route(/arcgisonline|googleapis|gstatic|openfreemap/, r => r.abort());
    if (!process.env.NOLIB) {
      await p.route(/maplibre-gl\.js$/, r => r.fulfill({ path: ML + "/maplibre-gl.js" }));
      await p.route(/maplibre-gl\.css$/, r => r.fulfill({ path: ML + "/maplibre-gl.css" }));
    } else await p.route(/maplibre-gl/, r => r.abort());
    p.on("console", m => { if (m.type() === "error" && !/ERR_FAILED|net::|Failed to fetch|AJAXError|Failed to load resource/.test(m.text())) errs.push(nm + ": " + m.text()); });
    p.on("pageerror", e => errs.push(nm + " pageerror: " + e.message));
    await p.goto("http://localhost:" + (process.env.PORT || 47321) + "/index.html", { waitUntil: "load" });
    if (process.env.NOLIB) {
      await p.waitForTimeout(1500); await p.screenshot({ path: `qa/${nm}_nolib.png` });
      console.log(nm, "no map library, loading text:", await p.textContent("#loading"), "charts:", await p.locator("#shareChart svg").count());
      await p.close(); continue;
    }
    for (let k = 0; k < 60 && !(await p.evaluate(() => !!window.map && document.getElementById("loading") === null)); k++) await p.waitForTimeout(500);
    console.log(nm, "map ready:", await p.evaluate(() => !!window.map && document.getElementById("loading") === null));
    await p.waitForTimeout(2500);
    await p.screenshot({ path: `qa/${nm}_top.png` });
    const shot = async (sel, f) => { await p.locator(sel).scrollIntoViewIfNeeded().catch(() => {}); await p.waitForTimeout(700);
      try { await p.locator(sel).screenshot({ path: `qa/${nm}_${f}.png`, timeout: 45000 }); }
      catch (e) { await p.evaluate(s => document.querySelector(s).scrollIntoView({ block: "start" }), sel); await p.waitForTimeout(400);
        const bb = await p.locator(sel).boundingBox(), vh = p.viewportSize().height; const y = Math.max(0, bb.y);
        await p.screenshot({ path: `qa/${nm}_${f}.png`, clip: { x: Math.max(0, bb.x), y, width: Math.min(bb.width, p.viewportSize().width), height: Math.min(bb.height, vh - y) }, timeout: 60000 }); } };
    await shot("#atlas", "map_town");
    for (const m of ["c100k", "c1m", "coast"]) { await p.click(`#measRow [data-m="${m}"]`); await p.waitForTimeout(1200); await shot("#atlas", "map_" + m); }
    await p.click('#measRow [data-m="town"]'); await p.waitForTimeout(800);
    // country selector: United Kingdom, then Libya
    for (const c of ["United Kingdom", "Libya"]) {
      const v = await p.evaluate(n => String(SITE.countries.findIndex(c => c[0] === n)), c);
      await p.selectOption("#csel", v); await p.waitForTimeout(2600); await shot("#atlas", "country_" + c.replace(/ /g, "_"));
      console.log(nm, c, "popup:", (await p.textContent(".maplibregl-popup-content").catch(() => "none")).slice(0, 110));
    }
    // click anywhere: measure a point in the Australian desert
    await p.click('#focusRow .btn:nth-child(6)'); await p.waitForTimeout(1500);
    await p.evaluate(() => measure(-25.5, 128.5, null, false));
    for (let k = 0; k < 40 && await p.evaluate(() => S.pick && S.pick.busy); k++) await p.waitForTimeout(500);
    await p.waitForTimeout(800); await shot("#atlas", "click_measure");
    console.log(nm, "measured:", await p.evaluate(() => S.pick && [Math.round(S.pick.dt), S.pick.town, Math.round(S.pick.d2), S.pick.c2 && S.pick.c2.name]));
    // continent pole from the side panel
    await p.click(".back"); await p.click('#side [data-c="Asia"]'); await p.waitForTimeout(2200); await shot("#atlas", "pole_asia");
    // layers panel
    await p.click(".lyrBtn"); await p.waitForTimeout(300);
    await p.evaluate(() => { for (const [k, v] of [["towns", true], ["cities", true]]) { const c = document.querySelector(`.lyrPanel [data-k="${k}"]`); c.checked = v; c.dispatchEvent(new Event("change")); } });
    await p.click('#focusRow .btn:last-child'); await p.waitForTimeout(2500); await shot("#map", "layers_panel");
    console.log(nm, "layers:", await p.evaluate(() => JSON.stringify({ towns: map.getLayoutProperty("towns", "visibility"), n: map.querySelectSourceFeatures ? 0 : 0, cities: map.getLayoutProperty("cities", "visibility") })));
    await p.click(".lyrPanel .reset"); await p.click(".lyrBtn");
    for (const c of ["shareChart", "bandChart", "contChart", "islTable", "candTable", "ctyChart", "ctyTable", "ukTable"]) await shot("#" + c, c);
    if (nm === "phone") { await p.click("#theme"); await p.waitForTimeout(1500); await shot("#atlas", "dark_map"); await shot("#shareChart", "dark_share"); }
    await p.locator("#mapbox").scrollIntoViewIfNeeded(); await p.click(".mfs-btn"); await p.waitForTimeout(1500);
    console.log(nm, "fullscreen:", await p.evaluate(() => !!(document.fullscreenElement || document.querySelector(".mfs-fake"))), "map h:", await p.evaluate(() => document.getElementById("map").clientHeight));
    await p.screenshot({ path: `qa/${nm}_fullscreen.png` });
    await p.click(".mfs-btn"); await p.waitForTimeout(500);
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (ov > 0) console.log(nm, "widest:", await p.evaluate(() => [...document.querySelectorAll("body *")].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + "." + e.className + "#" + e.id + " " + Math.round(e.getBoundingClientRect().right))));
    console.log(nm, "horizontal overflow px:", ov);
    await p.close();
  }
  console.log("errors:", errs.length ? errs : "none");
  await b.close();
})();
