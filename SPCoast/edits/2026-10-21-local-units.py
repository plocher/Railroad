#!/usr/bin/env python3
"""Local units, 2026-10-21: Sargent, Watsonville, Corporal and Christopher drawn like Luchessa, their panels on the desk bus.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-local-units.py [--dry-run]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-local-units.py --check before.net after.net

Owner's instruction (2026-10-21): assume each of the four is like Sargent, a local cpNode-Xiao with I2C I/O for
its appliances; prepopulate the symbols and the ports, tidy later by hand.

Per unit sheet: a Processor '<unit>' (cpNode-Xiao) above the Interlocking, its Host pin wired to the Interlocking's
Host pin (the Host port stays exposed, no-connected at the parent, as Luchessa has it); an IOBus port on the
processor's IO_Bus pin; Sargent's three expanders labelled onto that bus; the Panel sheet box gains an I2C pin
carrying the OfficeIOBus port. Per panel: an I2C label on every MAX7313's bus pin. South-cTc: every box gets the
four ports in the owner's order; OfficeIOBus wired to the desk bus, Host and IOBus no-connected, and the three
units' SPCoastApp host wires removed since they host themselves.

Helpers come from 2026-10-21-explicit-seams.py. KiCad must be closed.
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
SPCOAST, LIBDIR, HWIO, TRACK = es.SPCOAST, es.LIBDIR, es.HWIO, es.TRACK

UNITS = {   # sheet: (Interlocking at, new processor ref)   -- Sargent already has Proc6
    "Watsonville": ((44.45, 33.02), "Proc8"),
    "Corporal": ((99.06, 36.83), "Proc9"),
    "Christopher": ((72.39, 36.83), "Proc10"),
}
PANEL_BOX = (226.06, 164.86, 40.21, 6.59)               # the untouched Panel sheet box on these four sheets
SHEET_ROW, HOST_LINE, OFFICE_LINE = 111.76, 81.28, 87.63      # the owner's layout: boxes' top edge, the two bus lines above it
ROOT = {    # box: Host pin x (existing, or new for Sargent), IOBus x, OfficeIOBus x
    "Watsonville": dict(host=240.03, host_new=False, iobus=237.49, office=228.6),
    "Corporal": dict(host=182.88, host_new=False, iobus=180.34, office=172.72),
    "Christopher": dict(host=156.21, host_new=False, iobus=153.67, office=127.0),
    "Sargent": dict(host=214.63, host_new=True, iobus=212.09, office=199.39),
}
HOST_LINE_DROP = [(148.59, 156.21), (156.21, 182.88), (182.88, 240.03)]   # host-line segments that only served the three units
HOST_LINE_JUNCTIONS_DROP = [156.21, 182.88]
OFFICE_LINE_END = 83.82                                                     # where the owner's office line stops today
MAX7313_PIN = (10.16, 39.37)        # the MAX7313's I2C pin, sheet offset for rotation 0
EXP_PIN = (17.78, 7.62)             # MCP23017 / PCA9685 unit's I2C pin, sheet offset for rotation 0


def no_connect(x: float, y: float) -> str:
    return f'\t(no_connect\n\t\t(at {cc.num(x)} {cc.num(y)})\n\t\t(uuid "{cc.uid()}")\n\t)'


def panel_pin_block(x: float, y: float) -> str:
    return (f'\t\t(pin "I2C" bidirectional\n\t\t\t(at {cc.num(x)} {cc.num(y)} 0)\n\t\t\t(uuid "{cc.uid()}")\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)\n\t\t)')


def panel_port(text: str, report: list[str], name: str) -> str:
    """The Panel sheet box gains an I2C pin on its right edge; an OfficeIOBus label sits on it."""
    bx, by, bw, bh = PANEL_BOX
    px, py = round(bx + bw, 3), round(by + 2.54, 3)
    edits = []
    for s, e in blocks(text, "sheet", 1):
        b = text[s:e]
        if '(property "Sheetname" "Panel"' not in b:
            continue
        assert f"\n\t\t(at {cc.num(bx)} {cc.num(by)})" in b and "\n\t\t(pin " not in b, name
        i = b.index("\n\t\t(instances")
        edits.append((s, e, b[:i] + "\n" + panel_pin_block(px, py) + b[i:]))
    assert len(edits) == 1, name
    text = cc.splice(text, edits)
    text = es.insert_before_first(text, "symbol", [es.hier_label("OfficeIOBus", px, py, 0)])
    report.append(f"{name}: Panel box pin I2C at ({px}, {py}) carrying the OfficeIOBus port")
    return text


def edit_unit(name: str, text: str, hwio: str, report: list[str]) -> str:
    (ix, iy), ref = UNITS[name]
    (cx, cy), (hx, hy) = es.interlocking_pins(text)
    assert (cx, cy) == (ix, iy), (name, cx, cy)
    place = (round(ix + 5.08, 3), round(iy - 17.78, 3))
    hits = es.occupied(text, *place, margin=1.27)
    assert not hits, (name, hits[:5])
    proc = es.symbol_instance(f"{HWIO}:Processor", ref, name, *place, es.sheet_path(text),
                              [("Role", "STRUCTURE"), ("Kind", "PROCESSOR"), ("Board", "cpNode-Xiao")], es.PROC_DESC, pins=2)
    text = es.insert_symbol_in_order(text, proc, *place)
    px_host, py_host = round(place[0] + 12.7, 3), round(place[1] + 5.08, 3)
    assert px_host == round(hx, 3), (px_host, hx)
    bus = (round(place[0] - 10.16, 3), py_host)
    text = es.insert_before_first(text, "global_label", [es.wire(px_host, py_host, hx, hy)])
    text = es.insert_before_first(text, "symbol", [es.hier_label("IOBus", *bus, 180)])
    report.append(f"{name}: Processor {ref} '{name}' (cpNode-Xiao) at {place}; Host wired to the Interlocking; IOBus port on its bus pin")
    text = panel_port(text, report, name)
    return es.update_cache(text, {f"{HWIO}:Processor": cc.cached(HWIO, hwio, "Processor")})


def edit_sargent(text: str, hwio: str, report: list[str]) -> str:
    s, e = es.find_one(text, f"{HWIO}:Processor", "Proc6")
    x, y, _ = es.inst_at(text[s:e])
    labels = [es.hier_label("IOBus", round(x - 10.16, 3), round(y + 5.08, 3), 180)]
    n = 0
    for s, e, lib_id in es.instances(text):
        if lib_id.split(":")[1].startswith("Driver-I2C-") and "\n\t\t(unit 1)" in text[s:e]:   # the bus pin lives on unit 1
            ex, ey, rot = es.inst_at(text[s:e])
            assert rot == 0, (lib_id, rot)
            labels.append(es.hier_label("IOBus", round(ex + EXP_PIN[0], 3), round(ey + EXP_PIN[1], 3), 0))
            n += 1
    assert n == 3, n
    (cx, cy), (hx, hy) = es.interlocking_pins(text)
    labels.append(es.hier_label("Host", hx, hy, 0))            # the Host port, on the wire end at the Interlocking's pin
    text = es.insert_before_first(text, "symbol", labels)
    report.append(f"Sargent: IOBus port on Proc6's bus pin; {n} expanders labelled onto it; Host port on the Interlocking's pin")
    return panel_port(text, report, "Sargent")


def edit_panel(name: str, text: str, report: list[str]) -> str:
    labels = []
    for s, e, lib_id in es.instances(text):
        if lib_id.split(":")[1].startswith("Driver-I2C-MAX7313"):
            ex, ey, rot = es.inst_at(text[s:e])
            assert rot == 0, (name, rot)
            labels.append(es.hier_label("I2C", round(ex + MAX7313_PIN[0], 3), round(ey + MAX7313_PIN[1], 3), 0))
    assert labels, name
    assert '(hierarchical_label "I2C"' not in text, name
    text = es.insert_before_first(text, "symbol", labels)
    report.append(f"{name}: {len(labels)} MAX7313 bus pins labelled I2C")
    return text


def drop_global_label(text: str, name: str, x: float, y: float) -> str:
    for s, e in blocks(text, "global_label", 1):
        b = text[s:e]
        if b.startswith(f'(global_label "{name}"') and f"\n\t\t(at {cc.num(x)} {cc.num(y)} " in b:
            return es.drop_block(text, s, e)
    raise AssertionError((name, x, y))


def junction(x: float, y: float) -> str:
    return (f'\t(junction\n\t\t(at {cc.num(x)} {cc.num(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "{cc.uid()}")\n\t)')


def drop_junction(text: str, x: float, y: float) -> str:
    for s, e in blocks(text, "junction", 1):
        if f"\n\t\t(at {cc.num(x)} {cc.num(y)})" in text[s:e]:
            return es.drop_block(text, s, e)
    raise AssertionError(("junction", x, y))


def edit_root_two_pass(text: str, report: list[str]) -> str:
    # 1. the three units host themselves: their drops from the host line go, and the line is shortened back to 148.59
    for name, spec in ROOT.items():
        if not spec["host_new"]:
            text = es.drop_wire(text, (spec["host"], HOST_LINE, spec["host"], SHEET_ROW))
    for x1, x2 in HOST_LINE_DROP:
        text = es.drop_wire(text, (x1, HOST_LINE, x2, HOST_LINE))
    for x in HOST_LINE_JUNCTIONS_DROP:
        text = drop_junction(text, x, HOST_LINE)
    # 2. ports on the four boxes
    wires, juncs, ncs, sheet_edits = [], [], [], []
    for s, e in blocks(text, "sheet", 1):
        b = text[s:e]
        name = re.search(r'\(property "Sheetname" "([^"]+)"', b).group(1)
        if name not in ROOT:
            continue
        spec = ROOT[name]
        sx, sy = map(float, re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)\)", b).groups())
        sw = float(re.search(r"\n\t\t\(size ([-\d.]+) ", b).group(1))
        assert sy == SHEET_ROW, (name, sy)
        pins = []
        for pin_name, px in (("Host", spec["host"] if spec["host_new"] else None), ("IOBus", spec["iobus"]), ("OfficeIOBus", spec["office"])):
            if px is None:
                continue
            assert sx < px < sx + sw and f"(at {cc.num(px)} {cc.num(SHEET_ROW)} " not in b, (name, pin_name, px)
            pins.append(es.sheet_pin(pin_name, px, SHEET_ROW))
        if not spec["host_new"]:
            assert f"(at {cc.num(spec['host'])} {cc.num(SHEET_ROW)} " in b, (name, "host pin")
        i = b.index("\n\t\t(instances")
        sheet_edits.append((s, e, b[:i] + "\n" + "\n".join(pins) + b[i:]))
        ncs += [no_connect(spec["host"], SHEET_ROW), no_connect(spec["iobus"], SHEET_ROW)]
        wires.append(es.wire(spec["office"], OFFICE_LINE, spec["office"], SHEET_ROW))
    # 3. the office line extends right to the last new drop; a junction where each drop meets it
    offices = sorted(spec["office"] for spec in ROOT.values())
    assert offices[0] > OFFICE_LINE_END
    wires.append(es.wire(OFFICE_LINE_END, OFFICE_LINE, offices[-1], OFFICE_LINE))
    juncs += [junction(OFFICE_LINE_END, OFFICE_LINE)] + [junction(x, OFFICE_LINE) for x in offices[:-1]]
    assert len(sheet_edits) == len(ROOT)
    text = cc.splice(text, sheet_edits)
    text = es.insert_before_first(text, "wire", juncs + ncs)
    text = es.insert_before_first(text, "global_label", wires)
    report.append("South-cTc: Watsonville, Corporal, Christopher host themselves (host-line drops removed, line shortened); "
                  "four boxes gain IOBus and OfficeIOBus (Sargent also Host) with no-connects; OfficeIOBus drops onto the office line, extended right")
    return text


# ---------------------------------------------------------------- check
def check(before_path: str, after_path: str) -> list[str]:
    sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
    from kicad_services.netlist_reader import NetlistReader
    def fn(n): return n.pinfunction.rsplit("_", 1)[0] if n.pinfunction else n.pin
    def load(p):
        m = NetlistReader().read(Path(p)); c = m.components; seam, plain = {}, []
        for net in m.nets:
            nodes = frozenset((n.reference, fn(n)) for n in net.nodes)
            if len(nodes) < 2:
                continue
            if any(c[r].part in ("Processor", "Processor-Virtual", "Remote-IO-CMRInet", "Remote-IO-JMRI", "OfficeUnit", "Interlocking")
                   or p in ("I2C", "IO_Bus", "Host", "Codeline", "Transport") for r, p in nodes):
                seam[nodes] = net.name
            else:
                plain.append(nodes)
        return c, seam, sorted(plain, key=sorted)
    cb, sb, pb = load(before_path); ca, sa, pa = load(after_path)
    bad = []
    if pb != pa:
        bad.append("connectivity away from the seams changed")
    if set(ca) - set(cb) != {"Proc8", "Proc9", "Proc10"} or set(cb) - set(ca):
        bad.append(f"parts: added {sorted(set(ca) - set(cb))}, removed {sorted(set(cb) - set(ca))}")
    for r, c in cb.items():
        if r in ca and (c.fields != ca[r].fields or c.value != ca[r].value):
            bad.append(f"{r}: fields or value changed")
    def net_with(ref, pin):
        hits = [n for n in sa if (ref, pin) in n]
        return hits[0] if len(hits) == 1 else None
    chips = {(r, "I2C") for r, c in ca.items() if c.part.startswith("Driver-I2C-MAX7313")}
    assert len(chips) == 14, len(chips)
    if net_with("Proc4", "IO_Bus") != frozenset({("Proc4", "IO_Bus")} | chips):
        bad.append(f"desk bus: {sorted(net_with('Proc4', 'IO_Bus') or [])}")
    for unit, proc in (("Plant15001", "Proc8"), ("Plant11001", "Proc9"), ("Plant9001", "Proc10"), ("Plant1", "Proc6"), ("Plant7001", "Proc5")):
        if net_with(unit, "Host") != frozenset({(unit, "Host"), (proc, "Host")}):
            bad.append(f"{unit} host: {sorted(net_with(unit, 'Host') or [])}")
    app = {("Proc7", "Host"), ("Plant3001", "Host"), ("Plant5001", "Host"), ("Transport2007", "Host"), ("Transport2009", "Host")}
    if net_with("Proc7", "Host") != frozenset(app):
        bad.append(f"SPCoastApp: {sorted(net_with('Proc7', 'Host') or [])}")
    exp = {(r, "I2C") for r, c in ca.items() if c.part.startswith("Driver-I2C-") and not c.part.startswith("Driver-I2C-MAX7313")}
    if net_with("Proc6", "IO_Bus") != frozenset({("Proc6", "IO_Bus")} | exp):
        bad.append(f"Sargent bus: {sorted(net_with('Proc6', 'IO_Bus') or [])}")
    for key in ("MQTT", "TIMECODE", "CMRInet", "JMRI_MQTT"):
        nb = [n for n, name in sb.items() if name == key]; na = [n for n, name in sa.items() if name == key]
        if nb != na:
            bad.append(f"{key} net changed")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args(argv)
    if a.check:
        bad = check(*a.check)
        print("\n".join("FAIL " + b for b in bad) or "check passed: local units hosted and bussed as expected, desk bus complete, nothing else changed")
        return 1 if bad else 0
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    hwio = (LIBDIR / f"{HWIO}.kicad_sym").read_text()
    out = {}
    for name in UNITS:
        p = SPCOAST / f"{name}.kicad_sch"
        out[p] = edit_unit(name, p.read_text(), hwio, report)
    p = SPCOAST / "Sargent.kicad_sch"
    out[p] = edit_sargent(p.read_text(), hwio, report)
    for name in ("Sargent", "Watsonville", "Corporal", "Christopher"):
        p = SPCOAST / f"{name}-Panel.kicad_sch"
        out[p] = edit_panel(f"{name}-Panel", p.read_text(), report)
    p = SPCOAST / "South-cTc.kicad_sch"
    out[p] = edit_root_two_pass(p.read_text(), report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    for p, t in out.items():
        p.write_text(t)
    print("wrote " + ", ".join(p.name for p in out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
