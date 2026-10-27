#!/usr/bin/env python3
"""Gate for 2026-10-18-head-cast.py: connectivity, derived head names and fields, before vs after.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-18-head-cast-gate.py BEFORE.net AFTER.net
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.netlist_reader import NetlistReader

ASPECT = {"Railroad-Field:Cast-Aspect-CPL", "Railroad-Field:Cast-Aspect-CL", "Railroad-Field:Cast-Aspect-Semaphore"}
LETTERS = "ABCDE"
before, after = (NetlistReader().read(Path(p)) for p in sys.argv[1:3])
part = lambda c: f"{c.lib}:{c.part}"
units = {r for r, c in before.components.items() if part(c) in ASPECT}
heads = {r for r, c in after.components.items() if part(c).startswith("Railroad-Field:Cast-Head-")}
masts = {r for r, c in after.components.items() if part(c) == "Railroad-Field:Mast"}
pin_names = lambda m, ref: {p.pin: p.name for p in m.components[ref].pins} if hasattr(m.components[ref], "pins") else {}

def nets(model, drop):
    out = set()
    for net in model.nets:
        nodes = frozenset((n.reference, n.pin) for n in net.nodes if not drop(n))
        if len(nodes) > 1:
            out.add(nodes)
    return out

# the heads' ASPECT pin before / IND pin after: the one on a net with a unit (before) or a mast (after)
def special_pins(model, partners):
    out = set()
    for net in model.nets:
        refs = {n.reference for n in net.nodes}
        if refs & partners:
            out |= {(n.reference, n.pin) for n in net.nodes if n.reference in heads}
    return out
asp_pins, ind_pins = special_pins(before, units), special_pins(after, masts)
print("head casts:", len(heads), "aspect pins before:", len(asp_pins), "IND pins after:", len(ind_pins))
nb = nets(before, lambda n: n.reference in units or (n.reference, n.pin) in asp_pins)
na = nets(after, lambda n: (n.reference, n.pin) in ind_pins)
print("nets not touching a unit or a head input: identical:", nb == na, f"({len(nb)} vs {len(na)})")
for x in sorted(nb ^ na, key=lambda s: sorted(s)):
    print("   differs:", sorted(x))

# expected head names from before: unit letter (ASPECT pin number / 2) + mast on the unit's IND net
exp = {}
mast_of_unit = {}
for net in before.nets:
    nodes = [(n.reference, n.pin) for n in net.nodes]
    for r, p in nodes:
        if r in units and int(p) % 2 == 1:
            (m,) = [x for x, _ in nodes if x in masts]
            mast_of_unit[(r, (int(p) + 1) // 2)] = before.components[m].value
for net in before.nets:
    nodes = [(n.reference, n.pin) for n in net.nodes]
    for r, p in nodes:
        if r in units and int(p) % 2 == 0:
            name = mast_of_unit[(r, int(p) // 2)] + LETTERS[int(p) // 2 - 1]
            for d, _ in nodes:
                if d in heads:
                    exp[d] = name
got = {}
for net in after.nets:
    nodes = [(n.reference, n.pin) for n in net.nodes]
    ms = [x for x, _ in nodes if x in masts]
    for d, p in nodes:
        if (d, p) in ind_pins:
            assert len(ms) == 1, (d, ms)
            got[d] = after.components[ms[0]].value + after.components[d].fields.get("Head", "?")
print("heads derived from mast + Head == old unit letters:", got == exp, sorted(set(exp.values())))
for d in sorted(set(exp) | set(got)):
    if exp.get(d) != got.get(d):
        print("   ", d, exp.get(d), "->", got.get(d))

# parts and fields
pb = {r: part(c) for r, c in before.components.items() if r not in units}
pa = {r: part(c) for r, c in after.components.items()}
print("parts (units removed) same refs:", set(pb) == set(pa), "re-symbolled == head casts:", {r for r in pb if pb[r] != pa.get(r)} == heads)
other = []
for r in sorted(set(pb) & set(pa)):
    fb, fa = before.components[r].fields, after.components[r].fields
    if r in heads:
        keys = {k for k in set(fb) | set(fa) if fb.get(k) != fa.get(k)}
        allowed = {k for k in keys if k.startswith("Pin.") or k in {"Head", "Style", "Description", "Sheetname", "Sheetfile"}}
        if keys - allowed:
            other.append((r, sorted(keys - allowed)))
    elif fb != fa or before.components[r].value != after.components[r].value:
        other.append((r, sorted(k for k in set(fb) | set(fa) if fb.get(k) != fa.get(k))))
print("field changes outside the head casts' own fields:", other or "none")
print("head casts:", {r: (pa[r].split(":")[1], after.components[r].fields.get("Head"), after.components[r].fields.get("Style")) for r in sorted(heads)})
