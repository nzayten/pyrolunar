"""Builds the clean dataset for the PyroLunar site from raw NASA PSI data (7 investigations)."""
import csv, io, json, re, sys

src = json.load(open(sys.argv[1]))

def table(pid):
    t = src[pid]["tables"][0]
    recs = [{(k or "").strip(): v for k, v in x.items()} for x in csv.DictReader(io.StringIO(t["csv"].replace("\r", "")))]
    return recs, t["file"], t["csv"]

def num(s):
    if s is None: return None
    m = re.search(r"-?\d+(\.\d+)?", str(s).replace(",", "."))
    return float(m.group()) if m else None

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

EXP = {
  "PSI-102": dict(module="tespit"), "PSI-101": dict(module="tespit"),
  "PSI-69": dict(module="sondurme"), "PSI-68": dict(module="sondurme"),
  "PSI-25": dict(module="onleme"), "PSI-99": dict(module="onleme"), "PSI-100": dict(module="onleme"),
}

experiments, rows, raw = [], [], {}

for pid, meta in EXP.items():
    r = src[pid]
    recs, fname, csvtext = table(pid)
    raw[pid] = {"file": fname, "csv": csvtext.replace("\r", "")}
    tests = []

    if pid == "PSI-102":  # SAME
        for x in recs:
            mat = clean(x["Sample Material"]).split(":")[0]
            tests.append(dict(test=x["Sample #"], material=mat, phase="solid (heated)",
                o2=None, flow=num(x["Air Flow (cm/s)"]), pressure=None, diluent=None,
                outcome=None, note=("Same conditions as Teflon tests" if "same" in x["Sample Material"] else
                    f"Weight loss {x['Weight loss rate (mg/min)']} mg/min, aging {x['Aging Duration (minutes)']} min")))
    elif pid == "PSI-101":  # SAME-R
        for x in recs:
            tests.append(dict(test=x["SAME Test #"], material=clean(x["Sample Type"]), phase="solid (heated)",
                o2=None, flow=num(x["Inlet velocity (cm/s)"]), pressure=None, diluent=None, outcome=None,
                duration=num(x["Duration (sec)"]), aging=num(x["Net aging time (sec)"]), heat=num(x["Rt/R0"]),
                note=clean(x["Description"])))
    elif pid == "PSI-69":  # FLEX
        for x in recs:
            co2 = num(x["CO initial ambient composition; mole fraction"]) or 0
            he = num(x["He initial ambient composition; mole fraction"]) or 0
            dil = "CO₂" if co2 > 0 else ("Helium" if he > 0 else "N₂ only")
            p = num(x["Ambient pressure; mmHg"])
            o2 = num(x["O initial ambient composition; mole fraction"])
            tests.append(dict(test=x["FLEX Test #"], material=clean(x["Fuel"]), phase="liquid droplet",
                o2=round(o2*100, 1) if o2 is not None else None, flow=0, pressure=round(p/760, 2) if p else None,
                diluent=dil, co2=round(co2*100, 1), he=round(he*100, 1),
                d0=num(x["Droplet initial diameter; mm"]), dext=num(x["Visible flame extinction diameter; mm"]),
                burn=num(x["Burn time; s"]), outcome={"Extinction": "Extinction", "Completion": "Burned out",
                "Disruption": "Droplet disruption"}.get(clean(x["Test end"]), clean(x["Test end"]) or None), note=""))
    elif pid == "PSI-68":  # FLEX-2 (range summary)
        for x in recs:
            tests.append(dict(test=clean(x["Sample (Fuel Type)"]), material=clean(x["Sample (Fuel Type)"]), phase="liquid droplet",
                o2=None, o2_range=[17, 30], flow=None, flow_range=[0.1, 5], pressure=None, pressure_range=[0.5, 3.0],
                diluent="N₂ or Helium", outcome=None,
                note="Table gives tested ranges per fuel, not individual tests: O₂ 17/21/25/30 %, 0.5–3 atm, flow 0.1–5 cm/s"))
    elif pid == "PSI-25":  # BASS-II
        for x in recs:
            o2 = num(x["Calibrated  initial O2 % by vol"])
            mat = clean(x["Fuel Sample Material"])
            m = mat.lower()
            fam = "SIBAL fabric" if "sibal" in m else ("Nomex" if "nomex" in m else ("Candle" if "candle" in m else
                  ("PMMA rod" if "rod" in m else ("PMMA sphere" if "spher" in m else "PMMA sheet/film"))))
            tests.append(dict(test=clean(x["Test #"]), material=fam, detail=mat, phase="solid",
                o2=o2, flow=None, pressure=None, diluent=None, outcome=None,
                fan=clean(x["Fan display"]), note=f"Fan setting {clean(x['Fan display'])} (not given in cm/s)"))
    elif pid in ("PSI-99", "PSI-100"):  # SAFFIRE
        last = ""
        for x in recs:
            sn = clean(x.get("Sample Number") or "")
            if not sn or sn.startswith("F") or sn.lower().startswith("note"):
                continue
            mat = clean(x["Material"]) or last; last = mat
            mat = {"Cotton-Fiberglass (SIBAL)":"SIBAL fabric","SIBAL Fabric":"SIBAL fabric","Silicone":"Silicone","PMMA":"PMMA sheet/film","PMMA & Nomex":"PMMA + Nomex"}.get(mat, mat)
            flow = num(x.get("Air Flow (cm/s)") or x.get("Air Flow"))
            o2 = num(x.get("Percent O2 (Note 1)")) if pid == "PSI-99" else None
            d = clean(x.get("Flow Direction") or x.get("Direction"))
            dir_tr = {"Concurrent": "Concurrent (with flow)", "Opposed": "Opposed (against flow)"}.get(d, d)
            burn = clean(x.get("Burn Time (s)", ""))
            spread = clean(x.get("?-g Spread Length", ""))
            tests.append(dict(test=sn, material=mat, phase="solid", o2=o2, flow=flow, pressure=None,
                diluent=None, direction=dir_tr, burn=num(burn) if burn and burn[0].isdigit() else None,
                outcome=("No flame spread" if burn == "Insignificant" else ("Burned" if burn else None)),
                spread=spread or None,
                g1burn=clean(x.get("1-g Burn Length", "")) or None,
                g1spread=clean(x.get("1-g Spread Rate", "")) or None,
                note=(f"µg spread rate: {spread}" if spread and spread != "n/a" else "")))
    for t in tests:
        t["exp"] = pid
    rows.extend(tests)

    o2s = [t["o2"] for t in tests if t.get("o2") is not None] + sum([t.get("o2_range", []) for t in tests], [])
    pubs = [p for p in r["publications"] if p.get("title")][:4]
    experiments.append(dict(id=pid, acronym=r["acronym"], title=r["title"], module=meta["module"],
        start=r["start"], end=r["end"], doi=r["doi"], hardware=r["hardware"], platform=r["platform"],
        objective=clean(r["objective"]), approach=clean(r["approach"]), impacts=clean(r["impacts"]),
        n=len(tests), o2min=min(o2s) if o2s else None, o2max=max(o2s) if o2s else None,
        materials=sorted({t["material"] for t in tests if t["material"]}),
        pubs=[dict(title=clean(p["title"]), doi=p.get("doi") or "") for p in pubs],
        rawfile=fname))

out = dict(experiments=experiments, tests=rows, raw=raw)
open(sys.argv[2], "w").write("window.PSI = " + json.dumps(out, ensure_ascii=False) + ";")
for e in experiments:
    print(e["id"], e["acronym"], e["n"], "test | O2", e["o2min"], "-", e["o2max"], "|", ", ".join(e["materials"])[:90])
