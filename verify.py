"""Independent check: every value shown on the site vs. NASA's original CSV files."""
import json, csv, io, re
raw = json.load(open('data/psi_combustion.json'))
site = json.loads(open('site/data.js').read()[len('window.PSI = '):-1])
def rows(pid):
    t = raw[pid]['tables'][0]['csv'].replace('\r','')
    return [{k.strip():(v or '').strip() for k,v in r.items()} for r in csv.DictReader(io.StringIO(t))]
def num(s):
    m = re.search(r'-?\d+(\.\d+)?', s or ''); return float(m.group()) if m else None
by = {}
for t in site['tests']: by.setdefault(t['exp'], []).append(t)
checks = fails = 0; report = []
def chk(pid, label, a, b):
    global checks, fails
    checks += 1
    ok = a == b or (isinstance(a,(int,float)) and isinstance(b,(int,float)) and abs(a-b) < 1e-6)
    if not ok:
        fails += 1; report.append(f"  MISMATCH {pid} {label}: site={a} raw={b}")
# FLEX
R = rows('PSI-69'); S = by['PSI-69']
chk('PSI-69','row count',len(S),len(R))
for s,r in zip(S,R):
    o2 = num(r['O initial ambient composition; mole fraction'])
    chk('PSI-69',f"test {r['FLEX Test #']} O2", s['o2'], round(o2*100,1) if o2 is not None else None)
    chk('PSI-69',f"test {r['FLEX Test #']} burn", s['burn'], num(r['Burn time; s']))
    chk('PSI-69',f"test {r['FLEX Test #']} fuel", s['material'], r['Fuel'])
# BASS-II
R = rows('PSI-25'); S = by['PSI-25']
chk('PSI-25','row count',len(S),len(R))
for s,r in zip(S,R):
    chk('PSI-25',f"{r['Test #']} O2", s['o2'], num(r['Calibrated  initial O2 % by vol']))
    chk('PSI-25',f"{r['Test #']} material", s['detail'], re.sub(r'\s+',' ',r['Fuel Sample Material']).strip())
# SAME-R
R = rows('PSI-101'); S = by['PSI-101']
chk('PSI-101','row count',len(S),len(R))
for s,r in zip(S,R):
    chk('PSI-101',f"{r['SAME Test #']} flow", s['flow'], num(r['Inlet velocity (cm/s)']))
    chk('PSI-101',f"{r['SAME Test #']} material", s['material'], r['Sample Type'])
# SAFFIRE-II
R = [r for r in rows('PSI-99') if re.match(r'^2-\d', r['Sample Number'])]; S = by['PSI-99']
chk('PSI-99','row count',len(S),len(R))
for s,r in zip(S,R):
    chk('PSI-99',f"{r['Sample Number']} O2", s['o2'], num(r['Percent O2 (Note 1)']))
    chk('PSI-99',f"{r['Sample Number']} flow", s['flow'], num(r['Air Flow (cm/s)']))
# summary ranges shown on the site
for e in site['experiments']:
    vals = [t['o2'] for t in by[e['id']] if t.get('o2') is not None]
    if vals: chk(e['id'],'O2 min shown', e['o2min'], min(vals)); chk(e['id'],'O2 max shown', e['o2max'], max(vals))
print(f"{checks} checks, {fails} mismatches"); print("\n".join(report[:20]))
