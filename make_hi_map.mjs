// Builds countries-hi.json: Natural Earth 50m outlines, simplified so the globe stays smooth when zoomed in.
// Every island is kept; only coastline points too close together to see at game zoom levels are dropped.
//   npm install world-atlas@2 topojson-client@3 topojson-simplify@3
//   node make_hi_map.mjs
import {presimplify, simplify} from "topojson-simplify";
import {quantize} from "topojson-client";
import {readFileSync, writeFileSync} from "fs";
import {createRequire} from "module";

const MIN_AREA = 0.006; // square degrees: raise for a lighter file, lower for more detail
const topo = JSON.parse(readFileSync(createRequire(import.meta.url).resolve("world-atlas/countries-50m.json")));

// world-atlas stores coordinates as delta-encoded integers; simplification needs real longitudes and latitudes
const [kx, ky] = topo.transform.scale, [dx, dy] = topo.transform.translate;
topo.arcs = topo.arcs.map(arc => { let x = 0, y = 0; return arc.map(([px, py]) => [(x += px) * kx + dx, (y += py) * ky + dy]); });
delete topo.transform;

const out = quantize(simplify(presimplify(topo), MIN_AREA), 1e5);
writeFileSync("countries-hi.json", JSON.stringify(out));
console.log(`countries-hi.json: ${out.arcs.reduce((n, a) => n + a.length, 0)} points`);
