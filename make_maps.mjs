// Builds the globe's two outline files from Natural Earth 50m country shapes:
//   countries-mid.json  zoomed out: lightly simplified, only islands big enough to see
//   countries-hi.json   zoomed in (3x and up): more detail, every island kept
//
//   npm install world-atlas@2 topojson-client@3 topojson-simplify@3
//   node make_maps.mjs
import {presimplify, simplify, filter, filterWeight} from "topojson-simplify";
import {quantize} from "topojson-client";
import {readFileSync, writeFileSync} from "fs";
import {createRequire} from "module";

// minArea: drop coastline points that bend the outline by less than this (square degrees)
// minIsland: drop islands smaller than this (square degrees); 0 keeps them all
const LEVELS = {
  "countries-mid.json": {minArea: 0.08, minIsland: 0.07},
  "countries-hi.json":  {minArea: 0.006, minIsland: 0},
};

const source = readFileSync(createRequire(import.meta.url).resolve("world-atlas/countries-50m.json"), "utf8");

for (const [file, {minArea, minIsland}] of Object.entries(LEVELS)) {
  const topo = JSON.parse(source);
  // world-atlas stores coordinates as delta-encoded integers; simplifying needs real longitudes and latitudes
  const [kx, ky] = topo.transform.scale, [dx, dy] = topo.transform.translate;
  topo.arcs = topo.arcs.map(arc => { let x = 0, y = 0; return arc.map(([px, py]) => [(x += px) * kx + dx, (y += py) * ky + dy]); });
  delete topo.transform;

  let out = simplify(presimplify(topo), minArea);
  if (minIsland) out = filter(out, filterWeight(out, minIsland));
  out = quantize(out, 1e5);
  writeFileSync(file, JSON.stringify(out));
  console.log(`${file}: ${out.arcs.reduce((n, a) => n + a.length, 0)} points`);
}
