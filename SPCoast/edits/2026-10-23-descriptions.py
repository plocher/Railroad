#!/usr/bin/env python3
"""Descriptions and the bit drivers' Node field, 2026-10-23 (ADR 0009 §3.10, §3.11 and the owner's TBDs).

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-descriptions.py

- Library Descriptions that still say "cast", "node that hosts", or describe the CMRInet encoding as providing a bus are
  rewritten in the ratified vocabulary.
- Driver-CMRInet-IB and -OB gain an empty `Node` field: the implicit fallback naming the node's UA when a sheet holds two
  CMRInet nodes, the same pattern as `Processor` on a chip (ADR 0005 E44). Caltrain's 34 bits get the field, empty.
Gate: netlist connectivity identical; only the new empty field differs. KiCad must be closed.
"""
import importlib.util, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
DESC = {
 ("Railroad-Field", "Device-Head-CL-Pixel"): "Mast indication to one head's aspect as one color point, for a pixel or a lamp behind a roundel (E71). Head is the head letter; Style is fixed: CL.",
 ("Railroad-Field", "Device-Head-Semaphore-UQ"): "Mast indication to one upper-quadrant semaphore head's arm position; the angles are this device's settings. Head is the head letter; Style is fixed: UQ.",
 ("Railroad-Field", "Device-Head-Semaphore-LQ"): "Mast indication to one lower-quadrant semaphore head's arm position; the angles are this device's settings. Head is the head letter; Style is fixed: LQ.",
 ("Railroad-Office", "Encoding-CMRInet"): "CMRInet polling: an I/O encoding on a CMRInet transport. It provides no net; the CMRInet nodes on the line provide the buses their bits sit on (ADR 0009 §3.5).",
 ("Railroad-HardwareIO", "Driver-CMRInet-IB"): "CMRInet digital input: one bit of the IB array of the CMRInet node whose IOBus it sits on. Bit = the bit number; Node = the node's UA, only when a sheet holds two nodes (ADR 0009).",
 ("Railroad-HardwareIO", "Driver-CMRInet-OB"): "CMRInet digital output: one bit of the OB array of the CMRInet node whose IOBus it sits on. Bit = the bit number; Node = the node's UA, only when a sheet holds two nodes (ADR 0009).",
 ("Railroad-HardwareIO", "Driver-CMRInet-Node"): "A CMRInet node: a driver on the CMRInet line, addressed by its UA, providing the IOBus its bits sit on; declares NodeType (C, M, N) and its IB/OB byte arrays, checked against the bits in use (ADR 0009 §3.5).",
}
libs = {}
for (lib, name), desc in DESC.items():
    p = es.LIBDIR / f"{lib}.kicad_sym"; t = libs.get(lib) or p.read_text()
    s, e = cc.top_symbols(t, 1)[name]; b = cc.set_prop(t[s:e], "Description", desc, 2)
    if name in ("Driver-CMRInet-IB", "Driver-CMRInet-OB"):
        assert "Node" not in cc.props_in(b, 2)
        b = es.add_prop_after(b, "Bit", cc._prop("Node", "", "0 0 0", size=1.27, autoplace=True), 2)
    libs[lib] = cc.splice(t, [(s, e, b)]); print(f"{lib}:{name}: Description" + (" + Node field" if name.startswith("Driver-CMRInet-") and name != "Driver-CMRInet-Node" else ""))
for lib, t in libs.items():
    (es.LIBDIR / f"{lib}.kicad_sym").write_text(t)
# the sheets: Caltrain's bits get the empty field; definitions refreshed where placed
for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
    t = p.read_text(); add = {}; n = 0
    for (lib, name) in DESC:
        if f'(lib_id "{lib}:{name}")' in t:
            add[f"{lib}:{name}"] = cc.cached(lib, libs[lib], name)
    if add:
        edits = []
        for s, e, lib_id in es.instances(t):
            nm = lib_id.split(":")[1]
            if nm in ("Driver-CMRInet-IB", "Driver-CMRInet-OB"):
                b = t[s:e]
                if "Node" not in cc.props_in(b, 2):
                    x, y, _ = es.inst_at(b)
                    b = es.add_prop_after(b, "Bit", es.sheet_prop("Node", "", f"{cc.num(x)} {cc.num(y)} 0"), 2); n += 1
                b = cc.set_prop(b, "Description", DESC[("Railroad-HardwareIO", nm)], 2)
                edits.append((s, e, b))
            elif nm in [k[1] for k in DESC]:
                lib = [k[0] for k in DESC if k[1] == nm][0]
                edits.append((s, e, cc.set_prop(t[s:e], "Description", DESC[(lib, nm)], 2)))
        t = cc.splice(t, edits)
        p.write_text(es.update_cache(t, add)); print(f"{p.name}: {len(add)} definitions refreshed" + (f", {n} bits gained an empty Node field" if n else ""))
