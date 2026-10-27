#!/usr/bin/env python3
"""House MC pin, 2026-10-22: the pin is visible; its NAME is not (name text size 0), as the owner meant.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-house-pin.py

2026-10-22-vocabulary.py had hidden the pin itself. The House definition is refreshed on every sheet that
places one. Gate: the netlist must be identical before and after. KiCad must be closed.
"""
import importlib.util, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
TRACK, LIB = es.TRACK, es.LIBDIR / f"{es.TRACK}.kicad_sym"
if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
lib = LIB.read_text()
s, e = cc.top_symbols(lib, 1)["House"]
b = lib[s:e]
pat = re.compile(r'(\(pin passive line\n\t+\(at [^)]*\)\n\t+\(length [^)]*\)\n)(\t+)\(hide yes\)\n(\t+\(name "MC"\n\t+\(effects\n\t+\(font\n\t+\(size )[\d.]+ [\d.]+\)')
m = pat.search(b)
assert m, "MC pin with a hidden flag not found"
b = b[:m.start()] + m.group(1) + m.group(3) + "0 0)" + b[m.end():]
assert "(hide yes)\n\t\t\t\t(name" not in b
lib = cc.splice(lib, [(s, e, b)])
LIB.write_text(lib)
n = 0
for sheet in ("Watsonville", "Corporal", "Christopher", "Luchessa", "Sargent", "GilroyCalTrain", "GilroyInterchange"):
    p = es.SPCOAST / f"{sheet}.kicad_sch"
    t = p.read_text()
    assert f'(lib_id "{TRACK}:House")' in t
    p.write_text(es.update_cache(t, {f"{TRACK}:House": cc.cached(TRACK, lib, "House")}))
    n += 1
print(f"House: MC pin visible, its name text size 0; definition refreshed on {n} sheets")
