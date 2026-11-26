"""Build cities.json for Pin the City from GeoNames (data: CC BY 4.0, geonames.org).

    python build_cities.py

Downloads cities15000.zip (every city over 15,000 people, about 3 MB) once into .geonames/,
then writes cities.json next to this script: five tiers of [name, country, lat, lng].
"""
import csv, io, json, math, sys, urllib.request, zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
CACHE, OUT = HERE / ".geonames", HERE / "cities.json"
GEONAMES = "https://download.geonames.org/export/dump/"

# Tiers 1-2 are hand-picked: no signal in the data reliably says "everyone knows this one".
# Write names as GeoNames spells them (or one of their alternate names); coordinates come from the data.
CURATED = {
    "Landmark city": "London GB, New York City US, Paris FR, Tokyo JP, Sydney AU, Rome IT, Los Angeles US, Dubai AE, "
                     "Beijing CN, Berlin DE, Madrid ES, Hong Kong HK, Barcelona ES, Amsterdam NL, San Francisco US, "
                     "Singapore SG, Moscow RU, Rio de Janeiro BR, Cairo EG, Toronto CA",
    "Major city": "Mumbai IN, Istanbul TR, Bangkok TH, Mexico City MX, Seoul KR, Cape Town ZA, Chicago US, Athens GR, "
                  "Delhi IN, Shanghai CN, Buenos Aires AR, Lisbon PT, Vienna AT, Dublin IE, Prague CZ, Stockholm SE, "
                  "Miami US, Vancouver CA, Melbourne AU, Venice IT, Edinburgh GB, Kyoto JP, Havana CU, Lima PE, "
                  "Nairobi KE, Jakarta ID, Manila PH, Marrakesh MA, Copenhagen DK, Montreal CA",
}
# Tiers 3-5 come from the data: (tier name, how many cities, max share for any one country)
RANKED = [("Regional hub", 400, .06), ("Off the beaten path", 800, .05), ("Deep cut", 1500, .04)]
MAX_NAME = 18  # longer names don't fit the split-flap board


def fetch(name):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(GEONAMES + name, path)
    return path


def load():
    """One dict per city. Column list: https://download.geonames.org/export/dump/readme.txt"""
    countries = {}
    for line in fetch("countryInfo.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            f = line.split("\t")
            countries[f[0]] = f[4]
    with zipfile.ZipFile(fetch("cities15000.zip")) as z:
        text = z.read("cities15000.txt").decode("utf-8")
    for f in csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE):
        if f[7] == "PPLX":  # a district inside a bigger city
            continue
        yield {"name": f[1], "cc": f[8], "country": countries.get(f[8], f[8]),
               "lat": float(f[4]), "lng": float(f[5]), "pop": int(f[14] or 0),
               "alts": f[3].split(",") if f[3] else []}


def fame(c):
    # Famous cities get translated into many languages, so the count of alternate names is a strong
    # fame signal. Population breaks ties between places that are translated equally often.
    return math.log2(1 + len(c["alts"])) + 1.2 * math.log10(c["pop"] + 1)


def entry(c):
    return [c["name"], c["country"], round(c["lat"], 3), round(c["lng"], 3)]


def build(cities):
    cities = sorted(cities, key=fame, reverse=True)
    tiers, used = [], set()

    for tier, names in CURATED.items():
        picked = []
        for item in names.split(", "):
            name, cc = item.rsplit(" ", 1)
            # sorted by fame, so the first match is the well-known one (Paris FR, not a small namesake)
            match = next((c for c in cities if c["cc"] == cc and (c["name"] == name or name in c["alts"])), None)
            if match:
                picked.append(match)
                used.add((match["name"], cc))
            else:
                print(f"  not found in GeoNames, skipped: {item}", file=sys.stderr)
        tiers.append({"name": tier, "cities": [entry(c) for c in picked]})

    pool = [c for c in cities if len(c["name"]) <= MAX_NAME]
    for tier, size, share in RANKED:
        cap, per_country, picked, rest = max(2, round(size * share)), Counter(), [], []
        for c in pool:
            key = (c["name"], c["cc"])
            if key in used:  # already in a tier, or a same-named town in the same country
                continue
            if len(picked) < size and per_country[c["cc"]] < cap:
                picked.append(c)
                per_country[c["cc"]] += 1
                used.add(key)
            else:
                rest.append(c)  # over its country's cap here, so it moves down to the next tier
        pool = rest
        tiers.append({"name": tier, "cities": [entry(c) for c in picked]})
    return tiers


if __name__ == "__main__":
    tiers = build(load())
    OUT.write_text(json.dumps({"source": "GeoNames, CC BY 4.0", "tiers": tiers},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for t in tiers:
        print(f"{t['name']:<21}{len(t['cities']):>5}  e.g. {', '.join(c[0] for c in t['cities'][:5])}")
    print(f"Wrote {OUT}")
