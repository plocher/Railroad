#!/usr/bin/env python3
"""One-off, 2026-10-12: split the three libraries into four by use, and apply the owner's rulings
of the same day (checkpoint E65 to E67). Text-level edits; untouched bytes stay.

- Railroad-Trackplan <- RailroadPlant; minus `Signal Head - Searchlight` (CL covers it);
  plus `Signal Head - CPL` (copy of the CL head, Style CPL); semaphore Styles LQ and UQ.
- Railroad-Office <- RailroadDesk minus the Local-* plates.
- Railroad-Field <- RailroadDevice minus Driver-* and Setting, plus the Local-* plates;
  the LQ device's lamp pin word corrected.
- Railroad-HardwareIO <- Driver-* and Setting.
- Every Pin.<base> value keeps only its primary word: binary, level, position, color, pixel,
  message. Direction is the KiCad electrical type (E66).
Run from anywhere; reads and writes ~/Dropbox/KiCad/Railroad/symbols/.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks, end_of  # noqa: E402

DIR = Path.home() / "Dropbox/KiCad/Railroad/symbols"


def symbol_blocks(text):
    out, first = {}, None
    for s, e in blocks(text, "symbol", 1):
        first = s if first is None else first
        out[re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', text[s:e]).group(1)] = text[s:e]
    return text[: first - 2], out


def set_prop(b, name, value):
    m = re.search(r'\n\t\t\(property "%s" "' % re.escape(name), b)
    if m:
        s = m.end(); e = b.index('"', s)
        return b[:s] + value.replace('"', '\\"') + b[e:]
    t = re.search(r'\n\t\t\(property "Role" ', b); ts = t.start() + 3; te = end_of(b, ts)
    tmpl = b[ts:te].replace('(property "Role" "', '(property "%s" "' % name, 1)
    tmpl = re.sub(r'(\(property "[^"]+" ")[^"]*(")', lambda mm: mm.group(1) + value + mm.group(2), tmpl, count=1)
    return b[:te] + "\n\t\t" + tmpl + b[te:]


def rename_symbol(b, old, new):
    return b.replace('(symbol "%s"' % old, '(symbol "%s"' % new).replace('(symbol "%s_' % old, '(symbol "%s_' % new)


def primary_words(b):
    return re.sub(r'(\(property "Pin\.[^"]+" ")([a-z]+)[^"]*(")', r"\1\2\3", b)


src = {n: symbol_blocks((DIR / f"{n}.kicad_sym").read_text()) for n in ("RailroadPlant", "RailroadDevice", "RailroadDesk")}
header = src["RailroadDesk"][0]
out = {"Railroad-Trackplan": {}, "Railroad-Office": {}, "Railroad-Field": {}, "Railroad-HardwareIO": {}}

for name, b in src["RailroadPlant"][1].items():
    if name == "Signal Head - Searchlight":
        continue
    if name == "Signal Head - SemaphoreLQ2":
        b = set_prop(b, "Style", "LQ")
    if name == "Signal Head - SemaphoreUQ3":
        b = set_prop(b, "Style", "UQ")
    out["Railroad-Trackplan"][name] = b
cl = src["RailroadPlant"][1]["Signal Head - CL"]
cpl = set_prop(rename_symbol(cl, "Signal Head - CL", "Signal Head - CPL"), "Style", "CPL")
cpl = set_prop(cpl, "Description", "Color-position light head: colored lamps in fixed positions, one lit at a time (three-lamp or multiplexed). Style CPL (E65).")
out["Railroad-Trackplan"]["Signal Head - CPL"] = cpl
out["Railroad-Trackplan"]["Signal Head - CL"] = set_prop(cl, "Description", "Color light head: one light source showing one color at a time (searchlight roundel, or one RGB point in the model). Style CL (E65).")

for name, b in src["RailroadDesk"][1].items():
    out["Railroad-Field" if name.startswith("Local-") else "Railroad-Office"][name] = b

for name, b in src["RailroadDevice"][1].items():
    if name == "Device-Head-Semaphore-LQ":
        b = set_prop(b, "Pin.LAMP", "binary")
    out["Railroad-HardwareIO" if name.startswith("Driver-") or name == "Setting" else "Railroad-Field"][name] = b

for lib, syms in out.items():
    text = header + "".join("\n\t" + primary_words(syms[n]) for n in sorted(syms)) + "\n)\n"
    (DIR / f"{lib}.kicad_sym").write_text(text)
    print(f"{lib}.kicad_sym: {len(syms)} symbols")
for n in ("RailroadPlant", "RailroadDevice", "RailroadDesk"):
    (DIR / f"{n}.kicad_sym").unlink()
