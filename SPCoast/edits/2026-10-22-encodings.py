#!/usr/bin/env python3
"""Encodings, 2026-10-22: a transport is a mechanism, an encoding is what rides it, and what an encoding provides is a net of its own.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-encodings.py [--dry-run]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-encodings.py --check after.net

Owner's design (2026-10-22). Three kinds of net, three pin names:
- Transport net: provided by a Transport-* symbol (Broker, or Port and Baud; Host). Only an encoding's Transport pin lands on it.
- Codeline net: provided by a code line encoding (Encoding-AAR with its topic root, Encoding-US&S-506 with its chart) through
  its Codeline pin; the units' Codeline ports land on it.
- IOBus net: provided by a processor, or by an I/O encoding on a transport (Encoding-JMRI with its topic root,
  Encoding-CMRInet) through its IOBus pin; every driver's IOBus pin lands on it, the CMRInet node included.
Library: Codeline-Transport-* -> Transport-* (Role TRANSPORT; MQTT loses Topic and Railroad); Codeline-Encoding-* ->
Encoding-* with a Codeline pin (AAR gains Topic and Railroad; Bits loses Station and Address); new Encoding-JMRI and
Encoding-CMRInet (Role IO_ENCODING) with an IOBus pin. The node's and the remote drivers' pins are IOBus again (the owner's
Transport playtest reversed); the OfficeUnit's pin that lands on the transports' Host pins is Transport.
South-cTc: the JMRI_MQTT transport becomes an Encoding-JMRI on the MQTT transport; an Encoding-CMRInet sits on CMRInet;
the units' Codeline ports move from the transport nets to the AAR and USS506 nets; the I/O ports to the JMRI and CMRI nets.
KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc, blocks = es.cc, es.blocks
SPCOAST, LIBDIR, HWIO, OFFICE = es.SPCOAST, es.LIBDIR, es.HWIO, es.OFFICE
TRANSPORTS = {"Codeline-Transport-MQTT": "Transport-MQTT", "Codeline-Transport-TimeCode": "Transport-TimeCode",
              "Codeline-Transport-CMRInet": "Transport-CMRInet", "Codeline-Transport-LocoNet": "Transport-LocoNet"}
ENCODINGS = {"Codeline-Encoding-AAR": "Encoding-AAR", "Codeline-Encoding-US&S-506": "Encoding-US&S-506", "Codeline-Encoding-Bits": "Encoding-Bits"}
OUT_PIN = (17.78, -7.62, 90)                 # the encoding's provided net, below the body
REMOTE_DRIVERS = ("Driver-CMRInet-Node", "Driver-CMRInet-IB", "Driver-CMRInet-OB", "Driver-JMRI-Sensor", "Driver-JMRI-Sensor-Feedback",
                  "Driver-JMRI-SignalMast", "Driver-JMRI-Turnout", "Driver-JMRI-Turnout-Feedback")
JMRI_AT, CMRI_AT = (41.91, 57.15), (86.36, 57.15)          # on the JMRI_MQTT label point / on the CMRInet transport's pin point
LABEL_ROW = 106.68


def renamed(b: str, old: str, new: str) -> str:
    return b.replace(f'(symbol "{old}"', f'(symbol "{new}"', 1).replace(f'(symbol "{old}_', f'(symbol "{new}_')


def add_pin(b: str, name: str, number: int) -> str:
    """Append a pin to the symbol's last unit (the one carrying its pins)."""
    i = b.rfind("\n\t\t(symbol \"")
    ue = es.end_of(b, i + 3)
    unit = b[i + 3:ue]
    assert unit.endswith("\n\t\t)")
    new_unit = unit[:-len("\n\t\t)")] + "\n" + es.lib_pin(name, *OUT_PIN, number=number, length=1.27) + "\n\t\t)"
    return b[:i + 3] + new_unit + b[ue:]


def add_prop(b: str, after: str, name: str, value: str) -> str:
    return es.add_prop_after(b, after, cc._prop(name, value, "0 0 0", size=1.27, autoplace=True), 2)


# ---------------------------------------------------------------- libraries
def edit_office(text, report):
    syms = cc.top_symbols(text, 1)
    out = {}
    for old, new in TRANSPORTS.items():
        s, e = syms[old]; b = cc.set_prop(text[s:e], "Role", "TRANSPORT", 2)
        if old.endswith("MQTT"):
            b = cc.drop_prop(cc.drop_prop(b, "Topic", 2), "Railroad", 2)
        out[new] = renamed(b, old, new)
    for old, new in ENCODINGS.items():
        s, e = syms[old]; b = text[s:e]
        b = add_pin(b, "Codeline", 2)
        if old.endswith("AAR"):
            b = add_prop(add_prop(b, "Kind", "Topic", "ctc/${Railroad}/codeline/"), "Topic", "Railroad", "")
        if old.endswith("Bits"):
            b = cc.drop_prop(cc.drop_prop(b, "Station", 2), "Address", 2)
        out[new] = renamed(b, old, new)
    # the two I/O encodings, modelled on the AAR one
    s, e = syms["Codeline-Encoding-AAR"]; aar = text[s:e]
    jmri = add_pin(cc.set_prop(cc.set_prop(cc.set_prop(aar, "Value", "JMRI", 2), "Role", "IO_ENCODING", 2), "Kind", "JMRI", 2), "IOBus", 2)
    jmri = add_prop(jmri, "Kind", "Topic", "jmri_channel/")
    jmri = cc.set_prop(jmri, "Description", "JMRI's MQTT objects: an I/O encoding on an MQTT transport; provides an IOBus for JMRI drivers (ADR 0008).", 2)
    out["Encoding-JMRI"] = renamed(jmri, "Codeline-Encoding-AAR", "Encoding-JMRI")
    cmri = add_pin(cc.set_prop(cc.set_prop(cc.set_prop(aar, "Value", "CMRInet", 2), "Role", "IO_ENCODING", 2), "Kind", "CMRI", 2), "IOBus", 2)
    cmri = cc.set_prop(cmri, "Description", "CMRInet polling: an I/O encoding on a CMRInet transport; provides an IOBus for its nodes and their bits (ADR 0008).", 2)
    out["Encoding-CMRInet"] = renamed(cmri, "Codeline-Encoding-AAR", "Encoding-CMRInet")
    # OfficeUnit: its pin lands on the transports' Host pins
    s, e = syms["OfficeUnit"]; b = es.rename_pin(text[s:e], "Codeline", "Transport")
    assert b.count('(text "Codeline"') == 1
    out["OfficeUnit"] = b.replace('(text "Codeline"', '(text "Transport"')
    drops = sorted([syms[o] for o in list(TRANSPORTS) + list(ENCODINGS) + ["OfficeUnit"]], reverse=True)
    for s, e in drops:
        text = text[:s - 2] + text[e:]
    for name, b in out.items():
        text = es.insert_lib_symbol(text, "\t" + b, name)
    report.append(f"{OFFICE}: transports -> Transport-* (Role TRANSPORT, MQTT without Topic/Railroad); encodings -> Encoding-* with a Codeline pin "
                  "(AAR gains Topic, Railroad); Encoding-JMRI and Encoding-CMRInet added with an IOBus pin; OfficeUnit pin Codeline -> Transport")
    return text


def edit_hwio(text, report):
    syms = cc.top_symbols(text, 1)
    edits = []
    for name in REMOTE_DRIVERS:
        s, e = syms[name]; b = text[s:e]
        b = es.rename_pin(b, "Transport", "IOBus")
        b = b.replace('(text "Transport"', '(text "IOBus"')
        if name == "Driver-CMRInet-Node":
            p = cc.props_in(b, 2)
            if p["IC"][0] != "CMRI":
                b = cc.set_prop(b, "IC", "CMRI", 2)
            if p["Transport"][0]:
                b = cc.set_prop(b, "Transport", "", 2)
        edits.append((s, e, b))
    text = cc.splice(text, edits)
    report.append(f"{HWIO}: {len(REMOTE_DRIVERS)} remote drivers' pin Transport -> IOBus; node IC = CMRI, Transport default empty")
    return text


# ---------------------------------------------------------------- sheets
def relabel_at(text: str, kind: str, old: str, new: str, x: float, y: float) -> str:
    for s, e in blocks(text, kind, 1):
        b = text[s:e]
        if b.startswith(f'({kind} "{old}"') and f"\n\t\t(at {cc.num(x)} {cc.num(y)} " in b:
            return cc.splice(text, [(s, e, b.replace(f'({kind} "{old}"', f'({kind} "{new}"', 1))])
    raise AssertionError((kind, old, x, y))


def encoding_instance(name: str, ref: str, value: str, x: float, y: float, path: str, props: list, desc: str) -> str:
    body = es.symbol_instance(f"{OFFICE}:{name}", ref, value, x, y, path, props, desc, pins=2, value_at=(x + 2.54, y + 2.54))
    return body


def edit_root(text, libs, report):
    # 1. renames of the placed symbols
    for old, new in {**TRANSPORTS, **ENCODINGS}.items():
        text = text.replace(f'(lib_id "{OFFICE}:{old}")', f'(lib_id "{OFFICE}:{new}")')
    # 2. the MQTT transport loses Topic and Railroad; the AAR encoding gains them
    s, e = es.find_one(text, f"{OFFICE}:Transport-MQTT", "Transport2006"); b = text[s:e]
    assert cc.props_in(b, 2)["Topic"][0].startswith("ctc/")
    text = cc.splice(text, [(s, e, cc.drop_prop(cc.drop_prop(b, "Topic", 2), "Railroad", 2))])
    s, e = es.find_one(text, f"{OFFICE}:Encoding-AAR"); b = text[s:e]
    x, y, _ = es.inst_at(b); at = f"{cc.num(x)} {cc.num(y)} 0"
    b = es.add_prop_after(b, "Kind", es.sheet_prop("Topic", "ctc/${Railroad}/codeline/", at), 2)
    b = es.add_prop_after(b, "Topic", es.sheet_prop("Railroad", "SPCoast", at), 2)
    text = cc.splice(text, [(s, e, b)])
    aar_out = (round(x + OUT_PIN[0], 3), round(y + OUT_PIN[1] * -1, 3))
    s, e = es.find_one(text, f"{OFFICE}:Encoding-US&S-506"); x6, y6, _ = es.inst_at(text[s:e])
    uss_out = (round(x6 + OUT_PIN[0], 3), round(y6 - OUT_PIN[1], 3))
    # 3. the JMRI_MQTT transport goes; an Encoding-JMRI takes its label point, an Encoding-CMRInet the CMRInet pin point
    s, e = es.find_one(text, f"{OFFICE}:Transport-MQTT", "Transport2009")
    assert es.inst_at(text[s:e])[:2] == (57.15, 43.18)
    text = es.drop_block(text, s, e)
    text = relabel_at(text, "global_label", "JMRI_MQTT", "MQTT", *JMRI_AT)             # the encoding's Transport pin sits on the MQTT net here
    path = es.sheet_path(text)
    jm = encoding_instance("Encoding-JMRI", "Encoding3", "JMRI", *JMRI_AT, path,
                           [("Role", "IO_ENCODING"), ("Kind", "JMRI"), ("Topic", "jmri_channel/")],
                           "JMRI's MQTT objects: an I/O encoding on an MQTT transport; provides an IOBus for JMRI drivers (ADR 0008).")
    cm = encoding_instance("Encoding-CMRInet", "Encoding4", "CMRInet", *CMRI_AT, path,
                           [("Role", "IO_ENCODING"), ("Kind", "CMRI")],
                           "CMRInet polling: an I/O encoding on a CMRInet transport; provides an IOBus for its nodes and their bits (ADR 0008).")
    text = es.insert_symbol_in_order(text, jm, *JMRI_AT)
    text = es.insert_symbol_in_order(text, cm, *CMRI_AT)
    jmri_out = (round(JMRI_AT[0] + OUT_PIN[0], 3), round(JMRI_AT[1] - OUT_PIN[1], 3))
    cmri_out = (round(CMRI_AT[0] + OUT_PIN[0], 3), round(CMRI_AT[1] - OUT_PIN[1], 3))
    labels = [es.global_label("AAR", *aar_out, 0), es.global_label("USS506", *uss_out, 0),
              es.global_label("JMRI", *jmri_out, 0), es.global_label("CMRI", *cmri_out, 0)]
    text = es.insert_before_first(text, "symbol", labels)
    # 4. the unit boxes' ports: code lines onto the encodings' nets, I/O onto the I/O buses
    n_aar = 0
    for s, e in blocks(text, "global_label", 1):
        pass
    edits = []
    for s, e in blocks(text, "global_label", 1):
        b = text[s:e]
        m = re.match(r'\(global_label "([^"]+)"\n\t\t\(shape \w+\)\n\t\t\(at ([-\d.]+) ([-\d.]+) ', b)
        name, lx, ly = m.group(1), float(m.group(2)), float(m.group(3))
        if ly != LABEL_ROW:
            continue
        new = {"MQTT": "AAR", "TimeCode": "USS506", "CMRInet": "CMRI", "JMRI_MQTT": "JMRI"}.get(name)
        if new:
            edits.append((s, e, b.replace(f'(global_label "{name}"', f'(global_label "{new}"', 1))); n_aar += 1
    text = cc.splice(text, edits)
    n_pins = text.count('\n\t\t(pin "Transport" ')
    text = text.replace('\n\t\t(pin "Transport" ', '\n\t\t(pin "IOBus" ')
    add = {f"{OFFICE}:{n}": cc.cached(OFFICE, libs[OFFICE], n) for n in list(TRANSPORTS.values())[:3] + list(ENCODINGS.values())[:2] + ["Encoding-JMRI", "Encoding-CMRInet", "OfficeUnit"]}
    text = es.update_cache(text, add, drop=tuple(f"{OFFICE}:{o}" for o in list(TRANSPORTS) + list(ENCODINGS)))
    report.append(f"South-cTc: JMRI_MQTT transport -> Encoding-JMRI at {JMRI_AT}; Encoding-CMRInet at {CMRI_AT}; labels AAR {aar_out}, USS506 {uss_out}, "
                  f"JMRI {jmri_out}, CMRI {cmri_out}; {n_aar} unit-port labels moved to the provided nets; {n_pins} sheet pins Transport -> IOBus")
    return text


def edit_unit(name, text, libs, report):
    n = text.count('(hierarchical_label "Transport"')
    text = text.replace('(hierarchical_label "Transport"', '(hierarchical_label "IOBus"')
    add = {f"{HWIO}:{d}": cc.cached(HWIO, libs[HWIO], d) for d in REMOTE_DRIVERS if f'(lib_id "{HWIO}:{d}")' in text}
    text = es.update_cache(text, add)
    report.append(f"{name}: {n} labels Transport -> IOBus; {len(add)} remote driver definitions refreshed")
    return text


# ---------------------------------------------------------------- check
def check(after_path):
    sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
    from kicad_services.netlist_reader import NetlistReader
    a = NetlistReader().read(Path(after_path)); c = a.components
    def fn(n): return n.pinfunction.rsplit("_", 1)[0] if n.pinfunction else n.pin
    nets = {net.name: {(n.reference, fn(n)) for n in net.nodes} for net in a.nets if len(net.nodes) > 1}
    def net_with(ref, pin):
        hits = [v for v in nets.values() if (ref, pin) in v]
        return hits[0] if len(hits) == 1 else None
    by_part = {}
    for r, comp in c.items():
        by_part.setdefault(comp.part, []).append(r)
    bad = []
    aar, uss, jm, cm = by_part["Encoding-AAR"][0], by_part["Encoding-US&S-506"][0], by_part["Encoding-JMRI"][0], by_part["Encoding-CMRInet"][0]
    mqtt = [r for r in by_part["Transport-MQTT"]]; assert len(mqtt) == 1, mqtt
    want_mqtt = {(mqtt[0], "Transport"), (aar, "Transport"), (jm, "Transport")}
    if net_with(mqtt[0], "Transport") != want_mqtt: bad.append(f"MQTT net: {sorted(net_with(mqtt[0], 'Transport') or [])}")
    tc = by_part["Transport-TimeCode"][0]; cmt = by_part["Transport-CMRInet"][0]
    if net_with(tc, "Transport") != {(tc, "Transport"), (uss, "Transport")}: bad.append("TimeCode net")
    if net_with(cmt, "Transport") != {(cmt, "Transport"), (cm, "Transport")}: bad.append(f"CMRInet net: {sorted(net_with(cmt, 'Transport') or [])}")
    units = {r: comp.sheetpath for r, comp in c.items() if comp.part == "Interlocking"}
    houses = {r: comp.sheetpath for r, comp in c.items() if comp.part == "House"}
    aar_net = net_with(aar, "Codeline"); uss_net = net_with(uss, "Codeline")
    for u, sp in units.items():
        want = uss_net if "Luchessa" in sp else aar_net
        if want is None or (u, "Codeline") not in want: bad.append(f"{sp} Codeline not on its encoding's net")
    for h, sp in houses.items():
        want = uss_net if "Luchessa" in sp else aar_net
        if want is None or (h, "Codeline") not in want: bad.append(f"{sp} house {h} not on its line")
    if aar_net and any(p == "Transport" for _, p in aar_net): bad.append("AAR net touches a transport pin")
    jm_net = net_with(jm, "IOBus"); cm_net = net_with(cm, "IOBus")
    jdrv = {(r, "IOBus") for r, comp in c.items() if comp.part.startswith("Driver-JMRI")}
    cdrv = {(r, "IOBus") for r, comp in c.items() if comp.part.startswith("Driver-CMRInet")}
    if jm_net != jdrv | {(jm, "IOBus")}: bad.append(f"JMRI IOBus net: {len(jm_net or [])} vs {len(jdrv) + 1}")
    if cm_net != cdrv | {(cm, "IOBus")}: bad.append(f"CMRI IOBus net: {len(cm_net or [])} vs {len(cdrv) + 1}")
    mach = by_part["OfficeUnit"][0]
    if net_with(mach, "Transport") != {(mach, "Transport"), (tc, "Host"), (mqtt[0], "Host")}: bad.append("machine Transport net")
    app = [r for r, comp in c.items() if comp.value == "SPCoastApp"][0]
    if net_with(app, "Processor") != {(app, "Processor"), (cmt, "Host")} | {(u, "Processor") for u, sp in units.items() if "Caltrain" in sp}:
        bad.append(f"SPCoastApp net: {sorted(net_with(app, 'Processor') or [])}")
    if "Transport2009" in c: bad.append("JMRI_MQTT transport still present")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", metavar="AFTER")
    a = ap.parse_args(argv)
    if a.check:
        bad = check(a.check)
        print("\n".join("FAIL " + x for x in bad) or "check passed: three net kinds as designed; units on their lines, drivers on their I/O buses, machine and app as before")
        return 1 if bad else 0
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    report = []
    paths = {lib: LIBDIR / f"{lib}.kicad_sym" for lib in (OFFICE, HWIO)}
    libs = {OFFICE: edit_office(paths[OFFICE].read_text(), report), HWIO: edit_hwio(paths[HWIO].read_text(), report)}
    out = {}
    for name in ("GilroyCalTrain", "GilroyInterchange"):
        p = SPCOAST / f"{name}.kicad_sch"; out[p] = edit_unit(name, p.read_text(), libs, report)
    p = SPCOAST / "South-cTc.kicad_sch"; out[p] = edit_root(p.read_text(), libs, report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written"); return 0
    for lib, t in libs.items():
        paths[lib].write_text(t)
    for p, t in out.items():
        p.write_text(t)
    print("wrote 2 libraries and", len(out), "sheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
