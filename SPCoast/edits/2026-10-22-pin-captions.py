#!/usr/bin/env python3
"""Pin captions, 2026-10-22: the hard-coded text labels that stand in for pin names follow the renamed pins.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-pin-captions.py

Survey of every library symbol's (text ...) against its pin names found three captions still carrying an old
pin name: OfficeUnit 'Host' (pin Processor), Interlocking 'Host' (pin Processor), Codeline-Transport-LocoNet
'Encoding' (pin Transport). Everything else that looked like an old name is not a pin caption ('H' = hand-throw
on manual switches and locks, 'MC' = the maintainer-call lamp on the desk expander). Fit is checked visually by
the owner. Gate: the netlist must be identical. KiCad must be closed.
"""
import importlib.util, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
CHANGES = {es.TRACK: [("Interlocking", '(text "Host"', '(text "Processor"')],
           es.OFFICE: [("OfficeUnit", '(text "Host"', '(text "Processor"'),
                       ("Codeline-Transport-LocoNet", '(text "Encoding"', '(text "Transport"')]}
libs = {}
for lib, items in CHANGES.items():
    p = es.LIBDIR / f"{lib}.kicad_sym"; t = p.read_text()
    for name, old, new in items:
        s, e = cc.top_symbols(t, 1)[name]; b = t[s:e]
        assert b.count(old) == 1, (name, old, b.count(old))
        t = cc.splice(t, [(s, e, b.replace(old, new))])
        print(f"{lib}:{name}: caption {old[7:]} -> {new[7:]}")
    p.write_text(t); libs[lib] = t
for sheet in ("Watsonville", "Corporal", "Christopher", "Luchessa", "Sargent", "GilroyCalTrain", "GilroyInterchange"):
    p = es.SPCOAST / f"{sheet}.kicad_sch"
    p.write_text(es.update_cache(p.read_text(), {f"{es.TRACK}:Interlocking": cc.cached(es.TRACK, libs[es.TRACK], "Interlocking")}))
p = es.SPCOAST / "South-cTc.kicad_sch"
p.write_text(es.update_cache(p.read_text(), {f"{es.OFFICE}:OfficeUnit": cc.cached(es.OFFICE, libs[es.OFFICE], "OfficeUnit")}))
print("definitions refreshed: Interlocking on 7 sheets, OfficeUnit on South-cTc")
