#!/usr/bin/env python3
"""Railroad, 2026-10-24: Name = ${Value} on every Trackplan appliance symbol, so no key is read from Value.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-24-trackplan-names.py
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-24-trackplan-names.py \\
        --check production/SPCoast.net production/trackplan-names-after.net \\
        [--erc-before production/names-after.erc.json --erc-after production/trackplan-names-after.erc.json]

The owner (2026-10-24), on review finding 4 (appliance names read from Value): no exception. "The data model keys
should be chosen to be functional descriptions of their use/content, and the kicad symbol attribute names should
reflect that choice; Value is generic." So every Railroad-Trackplan APPLIANCE symbol (switches, derails, masts,
heads, track circuits, maintainer calls, auxiliaries) gains `Name` = `${Value}` (hidden), the appliance's own name:
`783`, `784EAB`, `1NA`, a head's letter `A`. The compiler reads Name and never Value.

Edit: the library symbols and every placed instance gain Name; cached copies refreshed (no pin moved).
Gate (--check): same parts, lib ids, Values and connectivity; the only field change is Name added on every
Trackplan appliance with Name == Value; ERC no new (sheet, type), no count grown. KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
from kicad_services.netlist_reader import NetlistReader  # noqa: E402

TRACK = es.TRACK
SKIP = ("Description", "Sheetname", "Sheetfile", "Footprint", "Datasheet")


def appliance_symbols(lib_text: str) -> list[str]:
    out = []
    for name, (s, e) in cc.top_symbols(lib_text, 1).items():
        if cc.props_in(lib_text[s:e], 2).get("Role", ("",))[0] == "APPLIANCE":
            out.append(name)
    return sorted(out)


def edit() -> int:
    if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
        sys.exit("KiCad holds a lock; close it first")
    path = es.LIBDIR / f"{TRACK}.kicad_sym"; t = path.read_text()
    names = appliance_symbols(t)
    for name in names:
        s, e = cc.top_symbols(t, 1)[name]; b = t[s:e]
        assert "Name" not in cc.props_in(b, 2), f"{name} already has Name"
        t = cc.splice(t, [(s, e, es.add_prop_after(b, "Role", cc._prop("Name", "${Value}", "0 0 0", size=1.27, autoplace=True), 2))])
    path.write_text(t)
    named = {f"{TRACK}:{n}" for n in names}
    print(f"library: Name added to {len(names)} appliance symbols: {', '.join(names)}")
    totals = Counter()
    for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
        sch = p.read_text(); edits = []; add = {}; n = 0
        for s, e, lib_id in es.instances(sch):
            if lib_id not in named:
                continue
            b = sch[s:e]
            if "Name" in cc.props_in(b, 2):
                continue
            x, y, _ = es.inst_at(b)
            edits.append((s, e, es.add_prop_after(b, "Role", es.sheet_prop("Name", "${Value}", f"{cc.num(x)} {cc.num(y)} 0"), 2)))
            add[lib_id] = cc.cached(TRACK, t, lib_id.split(":")[1]); n += 1
        if edits:
            p.write_text(es.update_cache(cc.splice(sch, edits), add)); totals["name"] += n
            print(f"{p.name}: name {n}; cache refreshed {len(add)}")
    print(f"total: name {totals['name']}")
    return 0


def check(before: Path, after: Path, erc_before: Path | None, erc_after: Path | None) -> int:
    b, a = NetlistReader().read(before), NetlistReader().read(after)
    fails: list[str] = []
    if set(b.components) != set(a.components):
        fails.append("parts differ")
    counts = Counter()
    for ref in sorted(set(b.components) & set(a.components)):
        cb, ca = b.components[ref], a.components[ref]
        if cb.lib_id != ca.lib_id or cb.value != ca.value:
            fails.append(f"{ref}: lib id or Value changed")
        fb = {k: v for k, v in cb.fields.items() if k not in SKIP}; fa = {k: v for k, v in ca.fields.items() if k not in SKIP}
        for k in set(fb) | set(fa):
            if fb.get(k) == fa.get(k):
                continue
            if k == "Name" and ca.lib_id.startswith(f"{TRACK}:") and ca.fields.get("Role") == "APPLIANCE" and k not in fb \
                    and fa[k] == ("" if ca.value == "~" else ca.value):
                counts["name == value"] += 1
            else:
                fails.append(f"{ref}: field {k} {fb.get(k)!r} -> {fa.get(k)!r}")
    appliances = [c for c in a.components.values() if c.lib_id.startswith(f"{TRACK}:") and c.fields.get("Role") == "APPLIANCE"]
    if counts["name == value"] != len(appliances):
        fails.append(f"{len(appliances)} trackplan appliances but {counts['name == value']} gained Name")

    def nets(m):
        return Counter(frozenset((n.reference, n.pin) for n in net.nodes) for net in m.nets if len(net.nodes) > 1)
    if nets(b) != nets(a):
        fails.append("connectivity differs")
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
        counts["erc after"] = sum(va.values())
    print("counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for f in fails:
        print("FAIL", f)
    print("gate", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", nargs=2, type=Path, metavar=("BEFORE.net", "AFTER.net"))
    ap.add_argument("--erc-before", type=Path); ap.add_argument("--erc-after", type=Path)
    a = ap.parse_args(argv)
    if a.check:
        return check(a.check[0], a.check[1], a.erc_before, a.erc_after)
    return edit()


if __name__ == "__main__":
    sys.exit(main())
