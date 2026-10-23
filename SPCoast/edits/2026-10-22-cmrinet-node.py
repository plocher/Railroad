#!/usr/bin/env python3
"""CMRInet node, 2026-10-22: the node is a driver on the CMRInet bus; the JMRI attachment symbol retires.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-cmrinet-node.py [--dry-run]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-cmrinet-node.py --check before.net after.net

Owner's rulings (2026-10-22): a CMRInet node is a chip on the CMRInet bus, attaching upward by its UA and
declaring its IB/OB arrays downward, exactly as an MCP23017 on I2C: `Driver-CMRInet-Node`, Role IODRIVER, with
NodeType, Address, InputBytes, OutputBytes and the Transport fallback field. Its bit drivers are
`Driver-CMRInet-IB` / `-OB`, one spelling of the bus. Its title reads `Node:` `CMRInet`; "what processor runs
this logic" is the Interlocking's Processor wire, not this symbol. `Remote-IO-JMRI` carries no fact of its own
(transport by wire, kind on the drivers, no address, no bytes) and retires from the library and the Interchange
sheet; its wires stay, the drivers' bus reaches the sheet's IOBus port as before. KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
SPCOAST, LIBDIR, HWIO = es.SPCOAST, es.LIBDIR, es.HWIO
RENAMES = {"Remote-IO-CMRInet": "Driver-CMRInet-Node", "Driver-CMRI-IB": "Driver-CMRInet-IB", "Driver-CMRI-OB": "Driver-CMRInet-OB"}
NODE_DESC = "A CMRInet node: a driver on the CMRInet bus, attached by its UA; declares its IB/OB arrays (NodeType, InputBytes, OutputBytes), checked against the bits its drivers use (ADR 0008)."
BIT_DESC = {"Driver-CMRInet-IB": "CMRInet digital input. Bit = this bit on the sheet's CMRInet node (Driver-CMRInet-Node).",
            "Driver-CMRInet-OB": "CMRInet digital output. Bit = this bit on the sheet's CMRInet node (Driver-CMRInet-Node)."}


def renamed_block(b: str, old: str, new: str) -> str:
    return b.replace(f'(symbol "{old}"', f'(symbol "{new}"', 1).replace(f'(symbol "{old}_', f'(symbol "{new}_')


def edit_hwio(text, report):
    syms = cc.top_symbols(text, 1)
    out = {}
    for old, new in RENAMES.items():
        s, e = syms[old]; b = text[s:e]
        if old == "Remote-IO-CMRInet":
            b = cc.set_prop(b, "Role", "IODRIVER", 2)
            b = cc.drop_prop(b, "Kind", 2)
            b = cc.set_prop(b, "Description", NODE_DESC, 2)
            assert b.count('(text "Processor:"') == 1 and b.count('(text "Remote I/O"') == 1
            b = b.replace('(text "Processor:"', '(text "Node:"').replace('(text "Remote I/O"', '(text "CMRInet"')
        else:
            b = cc.set_prop(b, "Description", BIT_DESC[new], 2)
        out[new] = renamed_block(b, old, new)
    drops = sorted([syms[o] for o in RENAMES] + [syms["Remote-IO-JMRI"]], reverse=True)
    for s, e in drops:
        text = text[:s - 2] + text[e:]
    for new, b in out.items():
        text = es.insert_lib_symbol(text, "\t" + b, new)
    report.append(f"{HWIO}: {', '.join(f'{o} -> {n}' for o, n in RENAMES.items())}; node Role IODRIVER, Kind dropped, title Node: CMRInet; Remote-IO-JMRI removed")
    return text


def edit_caltrain(text, lib, report):
    n = 0
    for old, new in RENAMES.items():
        n += text.count(f'(lib_id "{HWIO}:{old}")')
        text = text.replace(f'(lib_id "{HWIO}:{old}")', f'(lib_id "{HWIO}:{new}")')
    s, e = es.find_one(text, f"{HWIO}:Driver-CMRInet-Node")
    b = cc.set_prop(cc.drop_prop(cc.set_prop(text[s:e], "Role", "IODRIVER", 2), "Kind", 2), "Description", NODE_DESC, 2)
    text = cc.splice(text, [(s, e, b)])
    edits = []
    for s, e, lib_id in es.instances(text):
        name = lib_id.split(":")[1]
        if name in BIT_DESC:
            edits.append((s, e, cc.set_prop(text[s:e], "Description", BIT_DESC[name], 2)))
    text = cc.splice(text, edits)
    text = es.update_cache(text, {f"{HWIO}:{n_}": cc.cached(HWIO, lib, n_) for n_ in RENAMES.values()},
                           drop=tuple(f"{HWIO}:{o}" for o in RENAMES))
    report.append(f"GilroyCalTrain: {n} instances renamed (1 node, {n - 1} bit drivers); node Role IODRIVER, Kind dropped")
    return text


def edit_interchange(text, report):
    s, e = es.find_one(text, f"{HWIO}:Remote-IO-JMRI")
    text = es.drop_block(text, s, e)
    text = es.update_cache(text, {}, drop=(f"{HWIO}:Remote-IO-JMRI",))
    report.append("GilroyInterchange: Remote-IO-JMRI instance removed; its wires and the IOBus port stay")
    return text


def check(before_path, after_path):
    sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
    from kicad_services.netlist_reader import NetlistReader
    b = NetlistReader().read(Path(before_path)); a = NetlistReader().read(Path(after_path))
    def fn(n): return n.pinfunction.rsplit("_", 1)[0] if n.pinfunction else n.pin
    def nets(m, skip=()):
        return {frozenset((n.reference, fn(n)) for n in net.nodes if n.reference not in skip) for net in m.nets
                if len([n for n in net.nodes if n.reference not in skip]) > 1}
    bad = []
    if set(b.components) - set(a.components) != {"RIO2"} or set(a.components) - set(b.components):
        bad.append(f"parts: removed {sorted(set(b.components) - set(a.components))}, added {sorted(set(a.components) - set(b.components))}")
    if nets(b, skip=("RIO2",)) != nets(a):
        bad.append("connectivity differs beyond RIO2's removal")
    for r, cb in b.components.items():
        if r not in a.components:
            continue
        ca = a.components[r]
        exp = RENAMES.get(cb.part, cb.part)
        if ca.part != exp:
            bad.append(f"{r}: part {cb.part} -> {ca.part}")
        fb, fa = dict(cb.fields), dict(ca.fields)
        for k in ("Description", "Sheetname", "Sheetfile"):
            fb.pop(k, None); fa.pop(k, None)
        if cb.part == "Remote-IO-CMRInet":
            if fb.pop("Role", None) != "REMOTE_IO" or fa.pop("Role", None) != "IODRIVER" or fb.pop("Kind", None) != "CMRI" or "Kind" in fa:
                bad.append(f"{r}: Role/Kind")
        if fb != fa or cb.value != ca.value:
            bad.append(f"{r}: fields changed")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args(argv)
    if a.check:
        bad = check(*a.check)
        print("\n".join("FAIL " + x for x in bad) or "check passed: node and bit drivers renamed, RIO2 gone, connectivity otherwise identical, no other field changed")
        return 1 if bad else 0
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    report = []
    lib_path = LIBDIR / f"{HWIO}.kicad_sym"
    lib = edit_hwio(lib_path.read_text(), report)
    cal_path, int_path = SPCOAST / "GilroyCalTrain.kicad_sch", SPCOAST / "GilroyInterchange.kicad_sch"
    cal = edit_caltrain(cal_path.read_text(), lib, report)
    inter = edit_interchange(int_path.read_text(), report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written"); return 0
    lib_path.write_text(lib); cal_path.write_text(cal); int_path.write_text(inter)
    print("wrote", lib_path.name, cal_path.name, int_path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
