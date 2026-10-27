#!/usr/bin/env python3
"""Railroad, 2026-10-24: Name on every device, office unit and encoding; Kind on the JMRI drivers; Driver-JMRI-Light.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-24-names-kind-light.py
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-24-names-kind-light.py \\
        --check production/SPCoast.net production/names-after.net \\
        [--erc-before production/heads-after.erc.json --erc-after production/names-after.erc.json]

The owner's rulings (2026-10-24, on the review of ADR 0008 rev 4):
- `Name` is the identity key everywhere; a device "needs a Name attribute with content ${Value}". The OfficeUnit, the
  five Encoding-* symbols, every Railroad-Field DEVICE and every Railroad-Office PANEL symbol gain `Name` = `${Value}`
  (hidden), as Processor, Transport-*, Interlocking and Railroad already have.
- The OfficeUnit's `Columns` is derived from its columns and is struck from the library.
- A JMRI driver carries no address; it is keyed by what it serves. Its JMRI object class is a fact the drawer states
  by choosing the symbol, carried by the classifier the libraries already use: `Kind`. TURNOUT on Driver-JMRI-Turnout
  and -Turnout-Feedback (one JMRI Turnout, commanded and fed back), SENSOR on -Sensor and -Sensor-Feedback,
  SIGNALMAST on -SignalMast, LIGHT on the new Driver-JMRI-Light.
- `Driver-JMRI-Light` (ADR 0005 §8: ON binary, INTENSITY level) for a lamp JMRI drives. The two Gilroy Interchange
  maintainer-call lamps MC1 and MC2 are drawn with Driver-JMRI-Sensor, which is what JMRI only displays; they become
  Lights. The symbol keeps the Sensor's pin positions (1 = ON where S was, 2 = IOBus) and adds INTENSITY as pin 3
  below, with a no-connect flag on the two placed instances, so ERC stays at zero.

Edit:
- Libraries: Name added after Role on the symbols above; Columns dropped from OfficeUnit; Kind added after IC on the
  five JMRI drivers; Driver-JMRI-Light added to Railroad-HardwareIO.
- Every sheet: placed instances of those symbols gain the Name (and Kind) instance field; the OfficeUnit loses
  Columns; the two Driver-JMRI-Sensor instances become Driver-JMRI-Light (Pin.S -> Pin.ON, Pin.INTENSITY added,
  pin 3 entry, no-connect at pin 3); cached copies refreshed (no pin moved on any refreshed symbol).
Gate (--check): same parts and connectivity; lib ids change only Sensor -> Light on the two lamp drivers (their
pin 1 reads ON); fields change only as listed: Name added == Value on every instance of a NAMED symbol, Columns
dropped once, Kind added on every JMRI driver with the value its symbol gives, Pin.S/Pin.ON/Pin.INTENSITY on the
two Lights; ERC no new (sheet, type), no count grown. KiCad must be closed.
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

OFFICE, HWIO, FIELD = es.OFFICE, es.HWIO, cc.FIELD
OU = f"{OFFICE}:OfficeUnit"
ENCODINGS = {f"{OFFICE}:Encoding-{k}" for k in ("AAR", "Bits", "CMRInet", "JMRI", "US&S-506")}
PANEL = {f"{OFFICE}:{n}" for n in ("ModelLamp-AMBER", "ModelLamp-BLUE", "ModelLamp-GREEN", "ModelLamp-RED", "ModelLamp-YELLOW",
                                  "PanelAuxiliary", "PanelCode", "PanelLock", "PanelMCall", "PanelMCall-Lamp", "PanelSignal", "PanelSwitch")}
DEVICE = {f"{FIELD}:{n}" for n in ("Device-Contact", "Device-Head-CL-Pixel", "Device-Head-CL-RGB", "Device-Head-CPL", "Device-Head-CPL-Encoded",
                                  "Device-Head-CPL-Pixel", "Device-Head-Semaphore-LQ", "Device-Head-Semaphore-UQ", "Device-Lamp", "Device-Lock",
                                  "Device-Switch", "Device-Switch-ManualSensed", "Device-Switch-OS", "Device-TrackCircuit-Current",
                                  "Device-TrackCircuit-Optical", "Local-Lock", "Local-Switch", "Mast")}
NAMED = {OU} | ENCODINGS | PANEL | DEVICE
KIND = {f"{HWIO}:Driver-JMRI-Turnout": "TURNOUT", f"{HWIO}:Driver-JMRI-Turnout-Feedback": "TURNOUT",
        f"{HWIO}:Driver-JMRI-Sensor": "SENSOR", f"{HWIO}:Driver-JMRI-Sensor-Feedback": "SENSOR",
        f"{HWIO}:Driver-JMRI-SignalMast": "SIGNALMAST", f"{HWIO}:Driver-JMRI-Light": "LIGHT"}
SENSOR, LIGHT = f"{HWIO}:Driver-JMRI-Sensor", f"{HWIO}:Driver-JMRI-Light"
LIGHT_DESC = ("JMRI MQTT light driven by the FieldUnit: ON (OFF/ON) and INTENSITY (a level, for a variable light). "
              "No Address: the JMRI object is named by the lamp this driver serves (ADR 0005 R11); Address overrides it.")
SKIP = ("Description", "Sheetname", "Sheetfile", "Footprint", "Datasheet")


def light_symbol(hwio: str) -> str:
    """Driver-JMRI-Light from Driver-JMRI-Sensor's text: ON where S was, INTENSITY one row below, the body grown."""
    s, e = cc.top_symbols(hwio, 1)["Driver-JMRI-Sensor"]
    b = hwio[s:e].replace('(symbol "Driver-JMRI-Sensor"', '(symbol "Driver-JMRI-Light"', 1)
    b = b.replace('(symbol "Driver-JMRI-Sensor_0_1"', '(symbol "Driver-JMRI-Light_0_1"', 1)
    b = b.replace('(symbol "Driver-JMRI-Sensor_1_1"', '(symbol "Driver-JMRI-Light_1_1"', 1)
    b = cc.set_prop(b, "Description", LIGHT_DESC, 2)
    b = cc.rename_prop(b, "Pin.S", "Pin.ON", 2)
    b = es.add_prop_after(b, "Pin.ON", cc._prop("Pin.INTENSITY", "level", "7.62 4.699 0", size=0.635, justify="(justify left)"), 2)
    b = es.add_prop_after(b, "IC", cc._prop("Kind", "LIGHT", "7.6322 3.675 0", size=0.635, justify="(justify left)"), 2)
    b = es.rename_pin(b, "S", "ON")
    b = es.replace_text(b, "(end 20.32 -1.27)", "(end 20.32 -3.81)")
    b = es.replace_text(b, '(text "sensor"', '(text "light"')
    # the INTENSITY row: the Sensor's out-arrow and pin, 2.54 lower
    arrow = ('\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy 1.651 -2.54) (xy 2.286 -3.175) (xy 2.286 -1.905) (xy 1.651 -2.54)\n\t\t\t\t)\n'
             '\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n\t\t\t\t\t(type solid)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type color)\n\t\t\t\t\t(color 132 0 0 1)\n\t\t\t\t)\n\t\t\t)')
    pin = cc._pin("output", 0, -2.54, 0, "INTENSITY", "3")
    label = ('\t\t\t(text "intensity"\n\t\t\t\t(at 4.953 -2.54 0)\n\t\t\t\t(effects\n\t\t\t\t\t(font\n\t\t\t\t\t\t(size 0.635 0.635)\n\t\t\t\t\t)\n'
             '\t\t\t\t\t(justify left)\n\t\t\t\t)\n\t\t\t)')
    first_pin = b.index("\t\t\t(pin output line")
    return b[:first_pin] + arrow + "\n" + label + "\n" + pin + "\n" + b[first_pin:]


def edit() -> int:
    if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
        sys.exit("KiCad holds a lock; close it first")
    libs = {lib: (es.LIBDIR / f"{lib}.kicad_sym").read_text() for lib in (OFFICE, HWIO, FIELD)}
    # libraries: Name
    for lib_id in sorted(NAMED):
        lib, name = lib_id.split(":"); t = libs[lib]; s, e = cc.top_symbols(t, 1)[name]; b = t[s:e]
        assert "Name" not in cc.props_in(b, 2), f"{name} already has Name"
        b = es.add_prop_after(b, "Role", cc._prop("Name", "${Value}", "0 0 0", size=1.27, autoplace=True), 2)
        if lib_id == OU:
            assert "Columns" in cc.props_in(b, 2); b = cc.drop_prop(b, "Columns", 2)
        libs[lib] = cc.splice(t, [(s, e, b)])
    # libraries: Kind on the JMRI drivers, and the Light
    t = libs[HWIO]
    assert "Driver-JMRI-Light" not in cc.top_symbols(t, 1), "Driver-JMRI-Light exists"
    for lib_id, kind in sorted(KIND.items()):
        if lib_id == LIGHT:
            continue
        lib, name = lib_id.split(":"); s, e = cc.top_symbols(t, 1)[name]; b = t[s:e]
        assert "Kind" not in cc.props_in(b, 2), f"{name} already has Kind"
        t = cc.splice(t, [(s, e, es.add_prop_after(b, "IC", cc._prop("Kind", kind, "7.6322 3.675 0", size=0.635, justify="(justify left)"), 2))])
    light = light_symbol(t)
    s, e = cc.top_symbols(t, 1)["Driver-JMRI-Sensor"]
    t = t[:s] + light + "\n\t" + t[s:]
    libs[HWIO] = t
    for lib, text in libs.items():
        (es.LIBDIR / f"{lib}.kicad_sym").write_text(text)
    print(f"libraries: Name added to {len(NAMED)} symbols; Columns dropped from OfficeUnit; Kind on {len(KIND) - 1} JMRI drivers; Driver-JMRI-Light added")
    # sheets
    totals = Counter()
    for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
        t = p.read_text(); edits = []; add = {}; report = Counter(); ncs = []
        for s, e, lib_id in es.instances(t):
            b = t[s:e]; props = cc.props_in(b, 2)
            x, y, _ = es.inst_at(b)
            at = f"{cc.num(x)} {cc.num(y)} 0"
            if lib_id in NAMED and "Name" not in props:
                b = es.add_prop_after(b, "Role", es.sheet_prop("Name", "${Value}", at), 2); report["name"] += 1
            if lib_id == OU and "Columns" in props:
                b = cc.drop_prop(b, "Columns", 2); report["drop Columns"] += 1
            if lib_id == SENSOR:
                b = b.replace(f'(lib_id "{SENSOR}")', f'(lib_id "{LIGHT}")', 1)
                b = cc.rename_prop(b, "Pin.S", "Pin.ON", 2)
                b = es.add_prop_after(b, "Pin.ON", es.sheet_prop("Pin.INTENSITY", "level", at), 2)
                i = b.index("\n\t\t(instances")
                b = b[:i] + f'\n\t\t(pin "3"\n\t\t\t(uuid "{cc.uid()}")\n\t\t)' + b[i:]
                ncs.append(f'\t(no_connect\n\t\t(at {cc.num(x)} {cc.num(y + 2.54)})\n\t\t(uuid "{cc.uid()}")\n\t)')
                lib_id = LIGHT; report["light"] += 1
            if lib_id in KIND and "Kind" not in cc.props_in(b, 2):
                b = es.add_prop_after(b, "IC", es.sheet_prop("Kind", KIND[lib_id], at), 2); report["kind"] += 1
            if b != t[s:e]:
                lib, name = lib_id.split(":"); add[lib_id] = cc.cached(lib, libs[lib], name)
                edits.append((s, e, b))
        if edits:
            t = es.update_cache(cc.splice(t, edits), add, drop=(SENSOR,) if report["light"] else ())
            t = es.insert_before_first(t, "symbol", ncs)
            p.write_text(t); totals.update(report)
            print(f"{p.name}: " + ", ".join(f"{k} {v}" for k, v in sorted(report.items())) + f"; cache refreshed {len(add)}")
    assert totals["drop Columns"] == 1 and totals["light"] == 2 and totals["kind"] == 16, dict(totals)
    print("total: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())))
    return 0


def check(before: Path, after: Path, erc_before: Path | None, erc_after: Path | None) -> int:
    b, a = NetlistReader().read(before), NetlistReader().read(after)
    fails: list[str] = []
    if set(b.components) != set(a.components):
        fails.append(f"parts differ: -{sorted(set(b.components) - set(a.components))} +{sorted(set(a.components) - set(b.components))}")
    counts = Counter()
    for ref in sorted(set(b.components) & set(a.components)):
        cb, ca = b.components[ref], a.components[ref]
        if cb.value != ca.value:
            fails.append(f"{ref}: Value changed")
        light = cb.lib_id == SENSOR and ca.lib_id == LIGHT
        if cb.lib_id != ca.lib_id and not light:
            fails.append(f"{ref}: lib id {cb.lib_id} -> {ca.lib_id}")
        if light:
            counts["sensor -> light"] += 1
        fb = {k: v for k, v in cb.fields.items() if k not in SKIP}; fa = {k: v for k, v in ca.fields.items() if k not in SKIP}
        for k in set(fb) | set(fa):
            if fb.get(k) == fa.get(k):
                continue
            if k == "Name" and cb.lib_id in NAMED and k not in fb and fa[k] == ("" if ca.value == "~" else ca.value):   # KiCad resolves ${Value} of "~" to nothing
                counts["name == value"] += 1
            elif k == "Columns" and cb.lib_id == OU and k not in fa:
                counts["drop Columns"] += 1
            elif k == "Kind" and ca.lib_id in KIND and k not in fb and fa[k] == KIND[ca.lib_id]:
                counts["kind"] += 1
            elif light and ((k == "Pin.S" and k not in fa) or (k == "Pin.ON" and fa.get(k) == "binary") or (k == "Pin.INTENSITY" and fa.get(k) == "level")):
                counts["light pins"] += 1
            else:
                fails.append(f"{ref}: field {k} {fb.get(k)!r} -> {fa.get(k)!r}")
    named = [c for c in a.components.values() if c.lib_id in NAMED]
    if counts["name == value"] != len(named):
        fails.append(f"{len(named)} named symbols but {counts['name == value']} gained Name")
    kinds = [c for c in a.components.values() if c.lib_id in KIND]
    if counts["kind"] != len(kinds):
        fails.append(f"{len(kinds)} JMRI drivers but {counts['kind']} gained Kind")
    if counts["sensor -> light"] != 2 or counts["light pins"] != 6 or counts["drop Columns"] != 1:
        fails.append(f"expected 2 lights with 6 pin field changes and 1 Columns drop: {dict(counts)}")

    def nets(m):
        return Counter(frozenset((n.reference, n.pin) for n in net.nodes) for net in m.nets if len(net.nodes) > 1)
    if nets(b) != nets(a):
        fails.append("connectivity differs")
    on = [n for net in a.nets for n in net.nodes if a.components[n.reference].lib_id == LIGHT and n.pin == "1"]
    if len(on) != 2 or any(n.pinfunction != "ON_1" for n in on):
        fails.append(f"light pin 1 should read ON on both: {[(n.reference, n.pinfunction) for n in on]}")
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
