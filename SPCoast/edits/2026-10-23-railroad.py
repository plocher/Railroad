#!/usr/bin/env python3
"""Railroad, 2026-10-23: layout-wide facts on the Railroad symbol; the AAR Topic is a macro; Name on processors and transports.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-railroad.py
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-railroad.py \\
        --check production/model-lamps-after.net production/railroad-after.net \\
        [--erc-before production/model-lamps-after.erc.json --erc-after production/railroad-after.erc.json]

The owner's rulings (2026-10-23):
- A `Railroad` symbol on the root sheet (Role STRUCTURE, Kind RAILROAD; Name, Railroad, Region, Era, Rulebook) carries
  the layout-wide facts (Railroad d52017c).
- A field value may reference another symbol's field with the macro `<ROLE:KIND:Field>`, keyed by the fields the
  libraries key symbols by, resolved to the one instance of that Role and Kind in scope (0009 §3.9) and expanded by
  the compiler, never by KiCad. The KIND segment is empty for a Role without Kind: `<OFFICE_UNIT::Columns>`.
  The AAR encoding's Topic is `ctc/<STRUCTURE:RAILROAD:Name>/codeline/`, the root the netlist carried while the
  encoding's own Railroad field fed KiCad's `${Railroad}`.
- `Name` is the identity key everywhere the compiler names an entity; Value is never read. Processor and the four
  Transport-* symbols gain `Name` = `${Value}` (hidden), as Interlocking and Railroad already have.

Edit:
- Railroad-Office Encoding-AAR: Topic default -> the macro. Railroad-Office Transport-MQTT, -CMRInet, -TimeCode,
  -LocoNet and Railroad-HardwareIO Processor: `Name` `${Value}` added after Role.
- Every sheet: placed processors and transports gain the `Name` instance field; cached copies refreshed (no pin moved).
- South-cTc: the placed Encoding-AAR gets the macro Topic and loses its Railroad field; the OfficeUnit loses Railroad
  and Era (off the library already). Cached Encoding-AAR and OfficeUnit refreshed.
- Root: the cached Railroad refreshed (its creation values were cached; the library has empty defaults; no pins).
Gate (--check): same connectivity; parts identical but for the Railroad symbol (placed after the before netlist);
fields change only as listed: Topic (the macro, expanded against the Railroad symbol, equals the before Topic),
Railroad x2 and Era x1 dropped, Name added on every processor and transport with Name == Value; ERC no new
(sheet, type), no count grown. KiCad must be closed.
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
from kicad_services.netlist_reader import NetlistReader  # noqa: E402

OFFICE, HWIO = es.OFFICE, es.HWIO
AAR, OU, RAILROAD = f"{OFFICE}:Encoding-AAR", f"{OFFICE}:OfficeUnit", f"{OFFICE}:Railroad"
NAMED = {f"{HWIO}:Processor"} | {f"{OFFICE}:Transport-{k}" for k in ("MQTT", "CMRInet", "TimeCode", "LocoNet")}
OLD_TOPIC, NEW_TOPIC = "ctc/${Railroad}/codeline/", "ctc/<STRUCTURE:RAILROAD:Name>/codeline/"
MACRO = re.compile(r"<([A-Z_]+):([A-Z_]*):([\w .]+)>")
DROP = {AAR: {"Railroad"}, OU: {"Railroad", "Era"}}


def expand(value: str, components) -> str:
    """The compiler's macro rule in miniature: <ROLE:KIND:Field> -> that field of the one symbol with that Role and Kind."""
    def one(m):
        role, kind, field = m.groups()
        hits = [c for c in components if c.fields.get("Role") == role and c.fields.get("Kind", "") == kind]
        if len(hits) != 1:
            raise LookupError(f"{len(hits)} symbols with Role {role} Kind {kind!r}")
        if field not in hits[0].fields:
            raise LookupError(f"{role}:{kind} has no field {field}")
        return hits[0].fields[field]
    return MACRO.sub(one, value)


def edit() -> int:
    if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
        sys.exit("KiCad holds a lock; close it first")
    libs = {lib: (es.LIBDIR / f"{lib}.kicad_sym").read_text() for lib in (OFFICE, HWIO)}
    # libraries
    t = libs[OFFICE]; s, e = cc.top_symbols(t, 1)["Encoding-AAR"]; b = t[s:e]
    assert cc.props_in(b, 2)["Topic"][0] == OLD_TOPIC, cc.props_in(b, 2)["Topic"][0]
    libs[OFFICE] = cc.splice(t, [(s, e, cc.set_prop(b, "Topic", NEW_TOPIC, 2))])
    assert not ({"Railroad", "Era"} & set(cc.props_in(libs[OFFICE][slice(*cc.top_symbols(libs[OFFICE], 1)["OfficeUnit"])], 2))), "OfficeUnit still carries Railroad or Era"
    for lib_id in sorted(NAMED):
        lib, name = lib_id.split(":"); t = libs[lib]; s, e = cc.top_symbols(t, 1)[name]; b = t[s:e]
        assert "Name" not in cc.props_in(b, 2), f"{name} already has Name"
        libs[lib] = cc.splice(t, [(s, e, es.add_prop_after(b, "Role", cc._prop("Name", "${Value}", "0 0 0", size=1.27, autoplace=True), 2))])
    for lib, text in libs.items():
        (es.LIBDIR / f"{lib}.kicad_sym").write_text(text)
    print(f"libraries: Encoding-AAR Topic default -> {NEW_TOPIC}; Name added to {len(NAMED)} symbols")
    # sheets
    totals = Counter()
    for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
        t = p.read_text(); edits = []; add = {}; report = Counter()
        for s, e, lib_id in es.instances(t):
            b = t[s:e]; props = cc.props_in(b, 2)
            if lib_id in NAMED and "Name" not in props:
                x, y, _ = es.inst_at(b)
                b = es.add_prop_after(b, "Role", es.sheet_prop("Name", "${Value}", f"{cc.num(x)} {cc.num(y)} 0"), 2); report["name"] += 1
            if lib_id == AAR:
                assert props["Topic"][0] == OLD_TOPIC
                b = cc.set_prop(b, "Topic", NEW_TOPIC, 2); report["topic"] += 1
            for k in sorted(DROP.get(lib_id, set()) & set(props)):
                b = cc.drop_prop(b, k, 2); report[f"drop {k}"] += 1
            if lib_id == RAILROAD:
                report["railroad cache"] += 1
            if b != t[s:e] or lib_id == RAILROAD:
                lib, name = lib_id.split(":"); add[lib_id] = cc.cached(lib, libs[lib], name)
            if b != t[s:e]:
                edits.append((s, e, b))
        if edits or add:
            t = es.update_cache(cc.splice(t, edits), add); p.write_text(t); totals.update(report)
            print(f"{p.name}: " + ", ".join(f"{k} {v}" for k, v in sorted(report.items())) + f"; cache refreshed {len(add)}")
    assert totals["topic"] == 1 and totals["drop Railroad"] == 2 and totals["drop Era"] == 1 and totals["railroad cache"] == 1, dict(totals)
    print("total: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    return 0


def check(before: Path, after: Path, erc_before: Path | None, erc_after: Path | None) -> int:
    b, a = NetlistReader().read(before), NetlistReader().read(after)
    fails: list[str] = []
    added = set(a.components) - set(b.components)
    if set(b.components) - set(a.components) or any(a.components[r].lib_id != RAILROAD for r in added):
        fails.append(f"parts differ beyond the Railroad symbol: -{sorted(set(b.components) - set(a.components))} +{sorted(added)}")
    counts = Counter({"railroad added": len(added)})
    skip = ("Description", "Sheetname", "Sheetfile", "Footprint", "Datasheet")
    for ref in sorted(set(b.components) & set(a.components)):
        cb, ca = b.components[ref], a.components[ref]
        if cb.lib_id != ca.lib_id or cb.value != ca.value:
            fails.append(f"{ref}: lib id or Value changed")
        fb = {k: v for k, v in cb.fields.items() if k not in skip}; fa = {k: v for k, v in ca.fields.items() if k not in skip}
        for k in set(fb) | set(fa):
            if fb.get(k) == fa.get(k):
                continue
            if k in DROP.get(cb.lib_id, set()) and k not in fa:
                counts[f"drop {k}"] += 1
            elif k == "Name" and cb.lib_id in NAMED and k not in fb and fa[k] == ca.value:
                counts["name == value"] += 1
            elif k == "Topic" and cb.lib_id == AAR and fa.get(k) == NEW_TOPIC:
                counts["topic"] += 1
                try:
                    got = expand(fa[k], a.components.values())
                    if got != fb.get(k):
                        fails.append(f"{ref}: macro expands to {got!r}, before was {fb.get(k)!r}")
                    else:
                        counts["macro == before"] += 1
                except LookupError as exc:
                    fails.append(f"{ref}: macro: {exc}")
            else:
                fails.append(f"{ref}: field {k} {fb.get(k)!r} -> {fa.get(k)!r}")
    named = [c for c in a.components.values() if c.lib_id in NAMED]
    if counts["name == value"] != len(named):
        fails.append(f"{len(named)} processors and transports but {counts['name == value']} gained Name")

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
