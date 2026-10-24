#!/usr/bin/env python3
"""Model lamps, 2026-10-23: board lamps leave the columns; stale instance fields follow the libraries.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-model-lamps.py
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-model-lamps.py \\
        --check production/fields-after.net production/model-lamps-after.net \\
        [--erc-before production/fields-after.erc.json --erc-after production/model-lamps-after.erc.json]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-model-lamps.py --retire

The owner's ruling (2026-10-23): the PanelColumn is the logical column, tied to a control point; the panel
I/O hardware is not, and a model board lamp can be driven from any column's PCB. So every PanelLamp-* is a
model board lamp except the maintainer-call lamp (Value MC, on the column's pin 8). The owner added
ModelLamp-* (no Column pin, Style board) and PanelMCall-Lamp beside PanelLamp-* (Railroad a953197).

Edit, per sheet:
- PanelLamp-<color> with Value MC -> PanelMCall-Lamp; every other PanelLamp-<color> -> ModelLamp-<color>,
  Style indication -> board, its instance pin "1" entry removed. Description follows the new symbol.
  Wires are untouched: ~{LAMP} keeps its pin 2 offset; the Column wire of a model lamp ends on nothing.
- Instance properties the library symbol no longer defines are dropped (Address on Processor, Interlocking
  and Machine on PanelColumn, Host on the transports; Railroad c1d446b). Railroad on Encoding-AAR is kept:
  its Topic template still reads ${Railroad} (KEEP, pending the owner's decision).
- Cached definitions: the new lamps added, PanelLamp-* dropped where no instance remains, and the four
  symbols whose library changed in c1d446b refreshed (Processor, PanelColumn, Transport-MQTT, Encoding-AAR).

Gate (--check): same parts; lib ids change only on the lamps and to the expected targets; fields change only
as listed; connectivity after == before minus the model lamps' pin 1; ERC with no new (sheet, type), no count
grown, and no lib_symbol_mismatch left. KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
from kicad_services.netlist_reader import NetlistReader  # noqa: E402  (path set by explicit-seams)

OFFICE, HWIO, FIELD, TRACK = es.OFFICE, es.HWIO, "Railroad-Field", es.TRACK
LIBS = (OFFICE, HWIO, FIELD, TRACK)
COLORS = ("RED", "YELLOW", "BLUE")
MCALL = f"{OFFICE}:PanelMCall-Lamp"
REFRESH = {f"{HWIO}:Processor", f"{OFFICE}:PanelColumn", f"{OFFICE}:Transport-MQTT", f"{OFFICE}:Encoding-AAR"}
STANDARD = {"Reference", "Value", "Footprint", "Datasheet", "Description"}
# the stale fields c1d446b removed from the libraries, as the gate expects them per placed symbol
STALE = {f"{HWIO}:Processor": {"Address"}, f"{OFFICE}:PanelColumn": {"Interlocking", "Machine"},
         f"{OFFICE}:Transport-MQTT": {"Host"}, f"{OFFICE}:Transport-CMRInet": {"Host"},
         f"{OFFICE}:Transport-TimeCode": {"Host"}}
# kept although the library dropped it: the AAR encoding's Topic is the template ctc/${Railroad}/codeline/, and
# without the instance field KiCad reports unresolved_variable and the netlist loses the topic root. Pending the
# owner's decision on where Railroad lives (2026-10-23).
KEEP = {f"{OFFICE}:Encoding-AAR": {"Railroad"}}


def lamp_target(lib_id: str, value: str) -> str | None:
    m = re.fullmatch(rf"{OFFICE}:PanelLamp-({'|'.join(COLORS)})", lib_id)
    if not m:
        return None
    return MCALL if value == "MC" else f"{OFFICE}:ModelLamp-{m.group(1)}"


def lib_props(lib_text: str, name: str) -> dict[str, str]:
    s, e = cc.top_symbols(lib_text, 1)[name]
    return {k: v for k, (v, _, _) in cc.props_in(lib_text[s:e], 2).items()}


def drop_pin_entry(block: str, number: str) -> str:
    pat = re.compile(r'\n\t\t\(pin "' + re.escape(number) + r'"\n\t\t\t\(uuid "[^"]+"\)\n\t\t\)')
    assert len(pat.findall(block)) == 1, number
    return pat.sub("", block, count=1)


def edit() -> int:
    if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
        sys.exit("KiCad holds a lock; close it first")
    libs = {lib: (es.LIBDIR / f"{lib}.kicad_sym").read_text() for lib in LIBS}
    defined = {f"{lib}:{name}": set(lib_props(text, name)) for lib, text in libs.items() for name in cc.top_symbols(text, 1)}
    totals = Counter()
    for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
        t = p.read_text(); edits = []; add = {}; still = Counter(); report = Counter()
        for s, e, lib_id in es.instances(t):
            b = t[s:e]; props = cc.props_in(b, 2)
            value = props["Value"][0]
            target = lamp_target(lib_id, value)
            new_id = target or lib_id
            if target:
                lib, name = target.split(":")
                tprops = lib_props(libs[lib], name)
                b = b.replace(f'(lib_id "{lib_id}")', f'(lib_id "{target}")', 1)
                b = cc.set_prop(b, "Style", tprops["Style"], 2)
                b = cc.set_prop(b, "Description", tprops["Description"], 2)
                if name.startswith("ModelLamp-"):
                    b = drop_pin_entry(b, "1")
                add[target] = cc.cached(lib, libs[lib], name)
                report["mcall" if target == MCALL else "model"] += 1
            for k in sorted(set(props) - STANDARD - defined.get(new_id, set(props)) - KEEP.get(new_id, set())):
                b = cc.drop_prop(b, k, 2); report[f"drop {k}"] += 1
            if lib_id in REFRESH:
                lib, name = lib_id.split(":"); add[lib_id] = cc.cached(lib, libs[lib], name)
            still[new_id] += 1
            if b != t[s:e]:
                edits.append((s, e, b))
        if not edits:
            continue
        t = cc.splice(t, edits)
        drop = tuple(n for n in cc.top_symbols(t[slice(*next(iter(es.blocks(t, "lib_symbols", 1))))], 2)
                     if re.fullmatch(rf"{OFFICE}:PanelLamp-\w+", n) and still[n] == 0)
        t = es.update_cache(t, add, drop)
        p.write_text(t); totals.update(report)
        print(f"{p.name}: " + ", ".join(f"{k} {v}" for k, v in sorted(report.items())) + f"; cache +{len(add)} -{len(drop)}")
    print("total: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    return 0


# ---------------------------------------------------------------- gate
def check(before: Path, after: Path, erc_before: Path | None, erc_after: Path | None) -> int:
    b, a = NetlistReader().read(before), NetlistReader().read(after)
    fails: list[str] = []
    if set(b.components) != set(a.components):
        fails.append(f"parts differ: -{sorted(set(b.components) - set(a.components))} +{sorted(set(a.components) - set(b.components))}")
    model_lamps, counts = set(), Counter()
    for ref in sorted(set(b.components) & set(a.components)):
        cb, ca = b.components[ref], a.components[ref]
        want = lamp_target(cb.lib_id, cb.value) or cb.lib_id
        if ca.lib_id != want:
            fails.append(f"{ref}: lib id {ca.lib_id}, expected {want}")
        if ca.value != cb.value:
            fails.append(f"{ref}: Value changed {cb.value!r} -> {ca.value!r}")
        fb = {k: v for k, v in cb.fields.items() if k not in ("Description", "Sheetname", "Sheetfile", "Footprint", "Datasheet")}
        fa = {k: v for k, v in ca.fields.items() if k not in ("Description", "Sheetname", "Sheetfile", "Footprint", "Datasheet")}
        allowed_drop = STALE.get(cb.lib_id, set())
        for k in set(fb) | set(fa):
            if fb.get(k) == fa.get(k):
                continue
            if k in allowed_drop and k not in fa:
                counts[f"drop {k}"] += 1
            elif k == "Style" and want.startswith(f"{OFFICE}:ModelLamp-") and (fb.get(k), fa.get(k)) == ("indication", "board"):
                counts["style board"] += 1
            else:
                fails.append(f"{ref}: field {k} {fb.get(k)!r} -> {fa.get(k)!r}")
        if want.startswith(f"{OFFICE}:ModelLamp-"):
            model_lamps.add(ref); counts["model"] += 1
        elif want == MCALL:
            counts["mcall"] += 1
    if counts["model"] != counts["style board"]:
        fails.append(f"{counts['model']} model lamps but {counts['style board']} Style changes")

    def nets(model, strip):
        out = Counter()
        for net in model.nets:
            nodes = frozenset((n.reference, n.pin) for n in net.nodes if (n.reference, n.pin) not in strip)
            if len(nodes) > 1:
                out[nodes] += 1
        return out
    strip = {(ref, "1") for ref in model_lamps}
    nb, na = nets(b, strip), nets(a, set())
    for net in (nb - na).keys():
        fails.append("net lost: " + ", ".join(f"{r}.{p}" for r, p in sorted(net)))
    for net in (na - nb).keys():
        fails.append("net gained: " + ", ".join(f"{r}.{p}" for r, p in sorted(net)))
    lamp_nets = {net for net in nets(a, set()) if any((ref, "2") in net for ref in model_lamps)}
    if len(lamp_nets) != len(model_lamps):
        fails.append(f"{len(model_lamps)} model lamps but {len(lamp_nets)} ~{{LAMP}} nets after")

    if erc_before and erc_after:
        def viol(p):
            c = Counter()
            for sh in json.loads(p.read_text()).get("sheets", []):
                for v in sh.get("violations", []):
                    c[(sh.get("path"), v.get("type"))] += 1
            return c
        vb, va = viol(erc_before), viol(erc_after)
        for k, n in va.items():
            if n > vb.get(k, 0):
                fails.append(f"ERC {k}: {vb.get(k, 0)} -> {n}")
        if any(t == "lib_symbol_mismatch" for _, t in va):
            fails.append("ERC: lib_symbol_mismatch remains")
        counts["erc after"] = sum(va.values())
    print("counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for f in fails:
        print("FAIL", f)
    print("gate", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


def retire() -> int:
    """Remove PanelLamp-* from Railroad-Office once no sheet references them (step 3 of the plan)."""
    if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
        sys.exit("KiCad holds a lock; close it first")
    for p in es.SPCOAST.glob("*.kicad_sch"):
        if re.search(rf'"{OFFICE}:PanelLamp-', p.read_text()):
            sys.exit(f"{p.name} still references PanelLamp-*; run the edit first")
    path = es.LIBDIR / f"{OFFICE}.kicad_sym"; t = path.read_text()
    gone = [n for n in cc.top_symbols(t, 1) if re.fullmatch(r"PanelLamp-\w+", n)]
    t = cc.splice(t, [(s - 2, e, "") for n, (s, e) in cc.top_symbols(t, 1).items() if n in gone])  # with the preceding "\n\t"
    path.write_text(t)
    print(f"{OFFICE}: retired {', '.join(sorted(gone))}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", nargs=2, type=Path, metavar=("BEFORE.net", "AFTER.net"))
    ap.add_argument("--erc-before", type=Path); ap.add_argument("--erc-after", type=Path)
    ap.add_argument("--retire", action="store_true", help="remove PanelLamp-* from the Office library (after the edit)")
    a = ap.parse_args(argv)
    if a.check:
        return check(a.check[0], a.check[1], a.erc_before, a.erc_after)
    if a.retire:
        return retire()
    return edit()


if __name__ == "__main__":
    sys.exit(main())
