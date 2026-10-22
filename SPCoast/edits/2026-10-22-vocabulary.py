#!/usr/bin/env python3
"""Vocabulary, 2026-10-22: the naming-audit rulings applied to the libraries and every sheet.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-vocabulary.py [--dry-run]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-vocabulary.py --check before.net after.net

Owner's rulings on docs/review/naming-audit-2026-10-22.md (FieldUnit-Subdivision):
- `Host` stays only on the transport symbols (CMRI's own word for the end a node is reached through).
  Everywhere else it is `Processor`: the Interlocking, OfficeUnit and Processor pins, the unit sheets' port and labels.
- One spelling of the bus: `IOBus` on the Processor pin; the office side is `PanelIOBus` (FieldUnit ADR 0005: PANEL I/O)
  on the unit ports, the Panel sheet pins and labels, and the root labels.
- `MAIN HOUSE` becomes `House` (instrument house); its `H` pin becomes `MC` and is not visible, as the owner asked.
- OfficeUnit's `Type` becomes `Style` with the glossary's value `US&S`.
- `TimeCode` and `LocoNet` throughout; the LocoNet transport's pin is `Transport` like the others.
- The CMRInet node's `Board` becomes `NodeType`; the JMRI drivers' IC is `MQTT-JMRI`, the attachment's kind.
- The one `input` Codeline sheet pin becomes `bidirectional` like the six others.
Gate: --check compares the netlists under the pin-name mapping; nothing else may change. KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(es)
cc, blocks = es.cc, es.blocks
SPCOAST, LIBDIR, HWIO, OFFICE, TRACK = es.SPCOAST, es.LIBDIR, es.HWIO, es.OFFICE, es.TRACK
UNITS = ("Watsonville", "Corporal", "Christopher", "Luchessa", "Sargent", "GilroyCalTrain", "GilroyInterchange")
PANELS = tuple(f"{u}-Panel" for u in UNITS)
JMRI_DRIVERS = ("Driver-JMRI-Sensor", "Driver-JMRI-Sensor-Feedback", "Driver-JMRI-SignalMast", "Driver-JMRI-Turnout", "Driver-JMRI-Turnout-Feedback")


def rename_prop(block: str, old: str, new: str, depth: int, value: str | None = None) -> str:
    p = cc.props_in(block, depth)
    assert old in p and new not in p, (old, new, list(p))
    v, s, e = p[old]
    head = f'(property "{old}" "'
    assert block[s:s + len(head)] == head
    out = block[:s] + f'(property "{new}" "' + block[s + len(head):]
    return cc.set_prop(out, new, value, depth) if value is not None else out


def hide_pin(block: str, name: str) -> str:
    pat = re.compile(r'(\(pin \w+ line\n(\t+)\(at [^)]*\)\n\t+\(length [^)]*\)\n)(\t+\(name "' + re.escape(name) + '")')
    m = pat.search(block)
    assert m, name
    if "(hide yes)" in block[m.start():m.start() + 200].split('(name "')[0]:
        return block
    tabs = m.group(2)
    return block[:m.end(1)] + f"{tabs}(hide yes)\n" + block[m.end(1):]


# ---------------------------------------------------------------- libraries
def edit_track(text, report):
    syms = cc.top_symbols(text, 1)
    s, e = syms["Interlocking"]
    text = cc.splice(text, [(s, e, es.rename_pin(text[s:e], "Host", "Processor"))])
    s, e = cc.top_symbols(text, 1)["MAIN HOUSE"]
    b = text[s:e]
    b = es.rename_pin(b, "H", "MC")
    b = hide_pin(b, "MC")
    b = b.replace('(symbol "MAIN HOUSE"', '(symbol "House"', 1).replace('(symbol "MAIN HOUSE_', '(symbol "House_')
    text = cc.splice(text, [(s - 2, e, "")])
    text = es.insert_lib_symbol(text, "\t" + b, "House")
    report.append(f"{TRACK}: Interlocking pin Host -> Processor; MAIN HOUSE -> House, pin H -> MC (hidden)")
    return text


def edit_office(text, report):
    syms = cc.top_symbols(text, 1)
    edits = []
    s, e = syms["OfficeUnit"]
    b = es.rename_pin(text[s:e], "Host", "Processor")
    b = rename_prop(b, "Type", "Style", 2, "US&S")
    edits.append((s, e, b))
    s, e = syms["Codeline-Transport-TimeCode"]
    edits.append((s, e, cc.set_prop(text[s:e], "Value", "TimeCode", 2)))
    s, e = syms["Codeline-Transport-Loconet"]
    b = es.rename_pin(text[s:e], "Encoding", "Transport")
    b = cc.set_prop(b, "Value", "LocoNet", 2)
    b = b.replace('(symbol "Codeline-Transport-Loconet"', '(symbol "Codeline-Transport-LocoNet"', 1).replace('(symbol "Codeline-Transport-Loconet_', '(symbol "Codeline-Transport-LocoNet_')
    edits.append((s - 2, e, ""))
    text = cc.splice(text, edits)
    text = es.insert_lib_symbol(text, "\t" + b, "Codeline-Transport-LocoNet")
    report.append(f"{OFFICE}: OfficeUnit pin Host -> Processor, Type -> Style = US&S; TimeCode Value; Loconet -> LocoNet with pin Transport")
    return text


def edit_hwio(text, report):
    syms = cc.top_symbols(text, 1)
    edits = []
    s, e = syms["Processor"]
    b = es.rename_pin(text[s:e], "Host", "Processor")
    b = es.rename_pin(b, "IO_Bus", "IOBus")
    b = b.replace('(text "Host"', '(text "Processor"').replace('(text "IO_Bus"', '(text "IOBus"')
    edits.append((s, e, b))
    s, e = syms["Remote-IO-CMRInet"]
    b = rename_prop(text[s:e], "Board", "NodeType", 2)
    assert b.count("${Board}") == 1, b.count("${Board}")
    edits.append((s, e, b.replace("${Board}", "${NodeType}")))     # the body text that shows the node type
    for name in JMRI_DRIVERS:
        s, e = syms[name]
        b = text[s:e]
        assert cc.props_in(b, 2)["IC"][0] == "MQTT", name
        edits.append((s, e, cc.set_prop(b, "IC", "MQTT-JMRI", 2)))
    text = cc.splice(text, edits)
    report.append(f"{HWIO}: Processor pins Processor and IOBus; Remote-IO-CMRInet Board -> NodeType; JMRI drivers IC = MQTT-JMRI")
    return text


# ---------------------------------------------------------------- sheets
def relabel(text: str, kind: str, old: str, new: str) -> tuple[str, int]:
    pat = f'({kind} "{old}"'
    n = text.count(pat)
    return text.replace(pat, f'({kind} "{new}"'), n


def resheetpin(text: str, old: str, new: str) -> tuple[str, int]:
    pat = f'\n\t\t(pin "{old}" '
    n = text.count(pat)
    return text.replace(pat, f'\n\t\t(pin "{new}" '), n


def edit_unit(name, text, libs, report):
    text, a = relabel(text, "hierarchical_label", "Host", "Processor")
    text, b = relabel(text, "hierarchical_label", "OfficeIOBus", "PanelIOBus")
    text, c = resheetpin(text, "IOBus", "PanelIOBus")          # the Panel box pin; the unit's own IOBus label is untouched
    houses = text.count(f'(lib_id "{TRACK}:MAIN HOUSE")')
    text = text.replace(f'(lib_id "{TRACK}:MAIN HOUSE")', f'(lib_id "{TRACK}:House")')
    add = {f"{TRACK}:House": cc.cached(TRACK, libs[TRACK], "House"),
           f"{TRACK}:Interlocking": cc.cached(TRACK, libs[TRACK], "Interlocking")}
    drop = (f"{TRACK}:MAIN HOUSE",)
    if f'(lib_id "{HWIO}:Processor")' in text:
        add[f"{HWIO}:Processor"] = cc.cached(HWIO, libs[HWIO], "Processor")
    if name == "GilroyInterchange":
        n = 0
        edits = []
        for s, e, lib_id in es.instances(text):
            if lib_id.split(":")[1] in JMRI_DRIVERS:
                edits.append((s, e, cc.set_prop(text[s:e], "IC", "MQTT-JMRI", 2))); n += 1
        text = cc.splice(text, edits)
        add |= {f"{HWIO}:{d}": cc.cached(HWIO, libs[HWIO], d) for d in JMRI_DRIVERS if f'(lib_id "{HWIO}:{d}")' in text}
        report.append(f"{name}: {n} JMRI drivers IC = MQTT-JMRI")
    if name == "GilroyCalTrain":
        s, e = es.find_one(text, f"{HWIO}:Remote-IO-CMRInet")
        text = cc.splice(text, [(s, e, rename_prop(text[s:e], "Board", "NodeType", 2))])
        add[f"{HWIO}:Remote-IO-CMRInet"] = cc.cached(HWIO, libs[HWIO], "Remote-IO-CMRInet")
        report.append(f"{name}: node Board -> NodeType")
    text = es.update_cache(text, add, drop=drop)
    report.append(f"{name}: labels Host->Processor x{a}, OfficeIOBus->PanelIOBus x{b}, Panel box pin IOBus->PanelIOBus x{c}, {houses} houses -> House")
    return text


def edit_panel(name, text, libs, report):
    text, n = relabel(text, "hierarchical_label", "IOBus", "PanelIOBus")
    report.append(f"{name}: {n} labels IOBus -> PanelIOBus")
    return text


def edit_root(text, libs, report):
    text, a = resheetpin(text, "Host", "Processor")
    text, b = resheetpin(text, "OfficeIOBus", "PanelIOBus")
    text, c = relabel(text, "global_label", "OfficeIOBus", "PanelIOBus")
    text, d = relabel(text, "global_label", "TIMECODE", "TimeCode")
    n = text.count('(pin "Codeline" input')
    text = text.replace('(pin "Codeline" input', '(pin "Codeline" bidirectional')
    s, e = es.find_one(text, f"{OFFICE}:OfficeUnit")
    text = cc.splice(text, [(s, e, rename_prop(text[s:e], "Type", "Style", 2, "US&S"))])
    s, e = es.find_one(text, f"{OFFICE}:Codeline-Transport-TimeCode")
    text = cc.splice(text, [(s, e, cc.set_prop(text[s:e], "Value", "TimeCode", 2))])
    add = {f"{OFFICE}:OfficeUnit": cc.cached(OFFICE, libs[OFFICE], "OfficeUnit"),
           f"{OFFICE}:Codeline-Transport-TimeCode": cc.cached(OFFICE, libs[OFFICE], "Codeline-Transport-TimeCode"),
           f"{HWIO}:Processor": cc.cached(HWIO, libs[HWIO], "Processor")}
    text = es.update_cache(text, add, drop=(f"{OFFICE}:Codeline-Transport-Loconet",))
    report.append(f"South-cTc: sheet pins Host->Processor x{a}, OfficeIOBus->PanelIOBus x{b}; labels PanelIOBus x{c}, TimeCode x{d}; "
                  f"{n} Codeline pin -> bidirectional; OfficeUnit Style = US&S; transport Value TimeCode")
    return text


# ---------------------------------------------------------------- check
PIN_MAP = {("Interlocking", "Host"): "Processor", ("OfficeUnit", "Host"): "Processor", ("Processor", "Host"): "Processor",
           ("Processor", "IO_Bus"): "IOBus", ("MAIN HOUSE", "H"): "MC", ("Codeline-Transport-Loconet", "Encoding"): "Transport"}


def check(before_path, after_path):
    sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
    from kicad_services.netlist_reader import NetlistReader
    b = NetlistReader().read(Path(before_path)); a = NetlistReader().read(Path(after_path))
    def fn(n): return n.pinfunction.rsplit("_", 1)[0] if n.pinfunction else n.pin
    def mapped(m, mapping):
        out = set()
        for net in m.nets:
            nodes = set()
            for n in net.nodes:
                p = fn(n); part = m.components[n.reference].part
                if mapping and (part, p) in PIN_MAP:
                    p = PIN_MAP[(part, p)]
                nodes.add((n.reference, p))
            if len(nodes) > 1:
                out.add(frozenset(nodes))
        return out
    bad = []
    if mapped(b, True) != mapped(a, False):
        lost = mapped(b, True) - mapped(a, False); gained = mapped(a, False) - mapped(b, True)
        bad.append(f"connectivity differs under the pin map: {len(lost)} lost, {len(gained)} gained; e.g. {sorted(next(iter(lost)) if lost else next(iter(gained)))[:4]}")
    if set(a.components) != set(b.components):
        bad.append("parts differ")
    for r, cb in b.components.items():
        ca = a.components[r]
        pb, pa = cb.part, ca.part
        if (pb, pa) not in ((pb, pb), ("MAIN HOUSE", "House")):
            bad.append(f"{r}: part {pb} -> {pa}")
        fb, fa = dict(cb.fields), dict(ca.fields)
        vb, va = cb.value, ca.value
        if pb == "OfficeUnit":
            if fb.pop("Type", None) != "US&S506" or fa.pop("Style", None) != "US&S": bad.append(f"{r}: Type/Style")
        if pb == "Remote-IO-CMRInet":
            if fb.pop("Board", None) != fa.pop("NodeType", None): bad.append(f"{r}: Board/NodeType")
        if pb in JMRI_DRIVERS:
            if fb.pop("IC", None) != "MQTT" or fa.pop("IC", None) != "MQTT-JMRI": bad.append(f"{r}: IC")
        if pb == "Codeline-Transport-TimeCode":
            if (vb, va) != ("Time Coded", "TimeCode"): bad.append(f"{r}: Value {vb}->{va}")
            vb = va
        for k in ("Sheetname", "Sheetfile", "Description"):
            fb.pop(k, None); fa.pop(k, None)
        if fb != fa or vb != va:
            bad.append(f"{r}: fields changed {sorted(set(fb.items()) ^ set(fa.items()))[:4]}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args(argv)
    if a.check:
        bad = check(*a.check)
        print("\n".join("FAIL " + x for x in bad) or "check passed: same connectivity under the renamed pins, same parts, only the ruled fields changed")
        return 1 if bad else 0
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    report = []
    paths = {lib: LIBDIR / f"{lib}.kicad_sym" for lib in (TRACK, OFFICE, HWIO)}
    libs = {TRACK: edit_track(paths[TRACK].read_text(), report), OFFICE: edit_office(paths[OFFICE].read_text(), report),
            HWIO: edit_hwio(paths[HWIO].read_text(), report)}
    out = {}
    for u in UNITS:
        p = SPCOAST / f"{u}.kicad_sch"; out[p] = edit_unit(u, p.read_text(), libs, report)
    for pn in PANELS:
        p = SPCOAST / f"{pn}.kicad_sch"; out[p] = edit_panel(pn, p.read_text(), libs, report)
    p = SPCOAST / "South-cTc.kicad_sch"; out[p] = edit_root(p.read_text(), libs, report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written"); return 0
    for lib, t in libs.items():
        paths[lib].write_text(t)
    for p, t in out.items():
        p.write_text(t)
    print("wrote 3 libraries and", len(out), "sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
