#!/usr/bin/env python3
"""Roles, 2026-10-23: head devices are DEVICE with Appliance head; the OfficeUnit's Role is OFFICE_UNIT; stale instance Roles follow the libraries.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-roles.py

ADR 0009 §3.10, approved 2026-10-23, and the owner's rulings: CAST and MACHINE are implementation words.
- Railroad-Field Device-Head-*: Role CAST -> DEVICE, Appliance "head" added (hidden); Device-Switch's description loses "cast".
- Railroad-Office OfficeUnit: Role MACHINE -> OFFICE_UNIT; description in the ratified words.
- Railroad-HardwareIO JMRI drivers: "the unit" -> "the FieldUnit" in descriptions.
- Sheets: every placed head device, the OfficeUnit and the four transport instances still saying CODELINE_TRANSPORT get the
  library's Role (and the head devices their Appliance); definitions refreshed.
Gate: connectivity and parts identical; fields differ only in Role, Appliance and Description. KiCad must be closed.
"""
import importlib.util, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
FIELD, OFFICE, HWIO = "Railroad-Field", es.OFFICE, es.HWIO
if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
libs = {lib: (es.LIBDIR / f"{lib}.kicad_sym").read_text() for lib in (FIELD, OFFICE, HWIO)}
touched = {}      # lib:name -> (new Role, add Appliance?, new Description or None)
# Field: head devices
t = libs[FIELD]
for name, (s, e) in list(cc.top_symbols(t, 1).items()):
    if not name.startswith("Device-Head-"):
        continue
    b = t[s:e]
    assert cc.props_in(b, 2)["Role"][0] == "CAST", name
    b = cc.set_prop(b, "Role", "DEVICE", 2)
    b = es.add_prop_after(b, "Role", cc._prop("Appliance", "head", "0 0 0", size=1.27, autoplace=True), 2)
    t = cc.splice(t, [(s, e, b)]); touched[f"{FIELD}:{name}"] = ("DEVICE", True, None)
s, e = cc.top_symbols(t, 1)["Device-Switch"]; b = t[s:e]
d = cc.props_in(b, 2)["Description"][0]
assert "the cast on M" in d
t = cc.splice(t, [(s, e, cc.set_prop(b, "Description", d.replace("the cast on M", "the driver on M"), 2))])
libs[FIELD] = t
# Office: the OfficeUnit
t = libs[OFFICE]; s, e = cc.top_symbols(t, 1)["OfficeUnit"]; b = t[s:e]
assert cc.props_in(b, 2)["Role"][0] == "MACHINE"
OU_DESC = "The OfficeUnit: the dispatcher's office logic and its desk; one per CTC machine. Its columns are its interlockings (ADR 0009)."
b = cc.set_prop(cc.set_prop(b, "Role", "OFFICE_UNIT", 2), "Description", OU_DESC, 2)
libs[OFFICE] = cc.splice(t, [(s, e, b)]); touched[f"{OFFICE}:OfficeUnit"] = ("OFFICE_UNIT", False, OU_DESC)
# HardwareIO: JMRI driver descriptions
t = libs[HWIO]; edits = []
for name, (s, e) in cc.top_symbols(t, 1).items():
    if name.startswith("Driver-JMRI-"):
        b = t[s:e]; d = cc.props_in(b, 2)["Description"][0]
        nd = d.replace("by the unit", "by the FieldUnit").replace("from the unit", "from the FieldUnit")
        if nd != d:
            edits.append((s, e, cc.set_prop(b, "Description", nd, 2))); touched[f"{HWIO}:{name}"] = (None, False, nd)
libs[HWIO] = cc.splice(t, edits)
for lib, text in libs.items():
    (es.LIBDIR / f"{lib}.kicad_sym").write_text(text)
print(f"libraries: {sum(1 for k in touched if k.startswith(FIELD))} head devices DEVICE/head, OfficeUnit OFFICE_UNIT, {sum(1 for k in touched if k.startswith(HWIO))} JMRI descriptions")
# sheets
for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
    t = p.read_text(); n = 0; edits = []; add = {}
    for s, e, lib_id in es.instances(t):
        b = t[s:e]; props = cc.props_in(b, 2)
        lib, name = lib_id.split(":")
        if lib_id in touched:
            role, app, desc = touched[lib_id]
            if role: b = cc.set_prop(b, "Role", role, 2)
            if app and "Appliance" not in props:
                x, y, _ = es.inst_at(b); b = es.add_prop_after(b, "Role", es.sheet_prop("Appliance", "head", f"{cc.num(x)} {cc.num(y)} 0"), 2)
            if desc: b = cc.set_prop(b, "Description", desc, 2)
            edits.append((s, e, b)); n += 1
            add[lib_id] = cc.cached(lib, libs[lib], name)
        elif name.startswith("Transport-") and props.get("Role", ("",))[0] == "CODELINE_TRANSPORT":
            edits.append((s, e, cc.set_prop(b, "Role", "TRANSPORT", 2))); n += 1
            add[lib_id] = cc.cached(lib, libs[lib], name)
    if edits:
        t = cc.splice(t, edits); t = es.update_cache(t, add); p.write_text(t)
        print(f"{p.name}: {n} instances updated, {len(add)} definitions refreshed")
