#!/usr/bin/env python3
"""Explicit seams, 2026-10-21: the Luchessa pattern applied to every sheet, the libraries aligned to it.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-explicit-seams.py [--dry-run]

Settled with the owner, 2026-10-21 (FieldUnit-Subdivision ADR 0008 discussion), building on the owner's
mockup committed as 5288025:
- A `Host` wire always ends on a processor; a `Codeline` wire always ends on a transport's attachment net.
  A transport's `Host` pin takes the machine or the processor that serves its host end.
- A unit's sheet exposes `Codeline` (its line) and `Host` (where its logic runs) as hierarchical pins; the
  parent (South-cTc) wires each to a transport or a processor. Houses sit on the unit's Codeline net.
- Remote I/O is an attachment to a transport, not a processor: `Remote-IO-CMRInet` (Board, Address = UA)
  and `Remote-IO-JMRI`, each with a `Transport` pin, exposed as a sheet pin named for the transport.
- A virtual host is `Processor-Virtual`: Role STRUCTURE, Kind PROCESSOR, Type VIRTUAL, a Host pin, no bus.
- Processor pins: `Host` (passive) and `IO_Bus`; its Transport and Address fields go (they were the node's).
- Transports' attachment pin is `Transport` (was Encoding); MQTT loses `Station`. Encodings lose `Station`
  and `Address` (the station is derived from house and column). FieldUnit, FieldUnit_Virtual and the stray
  Codeline-Encoding-AAR_1 go.
- MAIN HOUSE gains `CP Name`, the one key every join reads; its Value becomes a display macro of it.
  Luchessa's appliances carried `CP Luchessa` etc.; they now carry the bare name like the columns do.
- CMRInet and JMRI_MQTT are I/O transports, not code lines: Gilroy Caltrain and Gilroy Interchange ride
  AAR Tokens on MQTT like every unit without a field processor; their remote I/O rides CMRInet / JMRI_MQTT.
  Sargent gets its own processor (it draws local chips); Watsonville, Caltrain, Interchange, Corporal and
  Christopher run on SPCoastApp.

Gate: 2026-10-21-explicit-seams-gate.py on the netlists before and after. Dry run prints the report and
writes nothing. KiCad must be closed. New blocks are filed where KiCad's own save would put them where that
is cheap (placed symbols by position); labels, wires and sheet pins go at the end of their kind.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cast_chain", HERE / "2026-10-17-cast-chain.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)
sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks, end_of  # noqa: E402

SPCOAST, LIBDIR = cc.SPCOAST, cc.LIBDIR
HWIO, OFFICE, TRACK = "Railroad-HardwareIO", "Railroad-Office", "Railroad-Trackplan"
TRANSPORTS = ("Codeline-Transport-CMRInet", "Codeline-Transport-MQTT", "Codeline-Transport-TimeCode")
ENCODINGS = ("Codeline-Encoding-AAR", "Codeline-Encoding-US&S-506")
BODY = (-17.018, 2.54, 17.018, -2.54)       # Processor / Remote-IO body, library units
SHEET_TOP, LABEL_Y = 90.17, 85.09           # the CP sheet boxes' top edge on South-cTc; the owner's label row
PROC_DESC = "A processor: runs the logic of the units wired to its Host pin and owns the chips on its IO_Bus (ADR 0005, 0008)."
VIRT_DESC = "A virtual processor: an application that hosts units and I/O transports; no hardware bus (ADR 0008 §4.9)."
RIO_DESC = {
    "Remote-IO-CMRInet": "Remote I/O over CMRInet: one node (Board, Address = UA) behind the transport's host; its CMRI drivers attach by sheet (ADR 0008).",
    "Remote-IO-JMRI": "Remote I/O through JMRI over MQTT: the JMRI objects of this sheet behind the transport's host; its JMRI drivers attach by sheet (ADR 0008).",
}


# ---------------------------------------------------------------- generic text helpers
def instances(text: str):
    for s, e in blocks(text, "symbol", 1):
        m = re.match(r'\(symbol\n\t\t\(lib_id "([^"]+)"', text[s:e])
        if m:
            yield s, e, m.group(1)


def inst_at(block: str) -> tuple[float, float, int]:
    x, y, r = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+) (\d+)\)", block).groups()
    return float(x), float(y), int(r)


def sheet_prop(name, value, at, hide=True, autoplace=True, size=1.27, justify=None):
    j = f"\n\t\t\t\t{justify}" if justify else ""
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {at}){h}\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace {"no" if autoplace else "yes"})\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {size} {size})\n\t\t\t\t){j}\n\t\t\t)\n\t\t)')


def add_prop_after(block: str, after: str, prop: str, depth: int) -> str:
    _, s, e = cc.props_in(block, depth)[after]
    return block[:e] + "\n" + prop + block[e:]


def symbol_instance(lib_id: str, ref: str, value: str, x: float, y: float, path: str, props: list[tuple[str, str]],
                    desc: str, pins: int, value_at: tuple[float, float] | None = None) -> str:
    at = f"{cc.num(x)} {cc.num(y)} 0"
    vx, vy = value_at or (x - 7.239, y)
    body = [sheet_prop("Reference", ref, f"{cc.num(x - 14.224)} {cc.num(y - 5.842)} 0", autoplace=False),
            sheet_prop("Value", value, f"{cc.num(vx)} {cc.num(vy)} 0", hide=False, justify="(justify left)"),
            sheet_prop("Footprint", "", at), sheet_prop("Datasheet", "", at), sheet_prop("Description", desc, at)]
    body += [sheet_prop(k, v, at) for k, v in props]
    pin_blocks = "".join(f'\n\t\t(pin "{i}"\n\t\t\t(uuid "{cc.uid()}")\n\t\t)' for i in range(1, pins + 1))
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{cc.uid()}")\n'
            + "\n".join(body) + pin_blocks +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def hier_label(name: str, x: float, y: float, rot: int, shape: str = "bidirectional") -> str:
    just = {0: "left", 180: "right", 90: "left", 270: "right"}[rot]
    return (f'\t(hierarchical_label "{name}"\n\t\t(shape {shape})\n\t\t(at {cc.num(x)} {cc.num(y)} {rot})\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{cc.uid()}")\n\t)')


def global_label(name: str, x: float, y: float, rot: int) -> str:
    just = {0: "left", 180: "right", 90: "left", 270: "right"}[rot]
    return (f'\t(global_label "{name}"\n\t\t(shape input)\n\t\t(at {cc.num(x)} {cc.num(y)} {rot})\n\t\t(fields_autoplaced yes)\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify {just})\n\t\t)\n\t\t(uuid "{cc.uid()}")\n'
            f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n\t\t\t(at {cc.num(x)} {cc.num(y)} 0)\n\t\t\t(hide yes)\n'
            f'\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t\t)\n\t\t\t\t(justify {just})\n\t\t\t)\n\t\t)\n\t)')


def wire(x1, y1, x2, y2) -> str:
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {cc.num(x1)} {cc.num(y1)}) (xy {cc.num(x2)} {cc.num(y2)})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{cc.uid()}")\n\t)')


def sheet_pin(name: str, x: float, y: float) -> str:
    return (f'\t\t(pin "{name}" bidirectional\n\t\t\t(at {cc.num(x)} {cc.num(y)} 90)\n\t\t\t(uuid "{cc.uid()}")\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)\n\t\t)')


def insert_before_first(text: str, head: str, new: list[str]) -> str:
    """Insert top-level blocks just before the first '(head' block (or before the closing paren)."""
    if not new:
        return text
    first = next(blocks(text, head, 1), None)
    body = "\n" + "\n".join(new)
    if first:
        s = first[0] - 2
        return text[:s] + body + text[s:]
    end = text.rstrip().rfind("\n)")
    return text[:end] + body + text[end:]


def insert_symbol_in_order(text: str, block: str, x: float, y: float) -> str:
    """Place a new symbol where KiCad's save order (unit, x, y) would file it."""
    last = None
    for s, e, _ in instances(text):
        b = text[s:e]
        unit = int(re.search(r"\n\t\t\(unit (\d+)\)", b).group(1))
        ax, ay, _ = inst_at(b)
        if (unit, ax, ay) > (1, x, y):
            return text[:s - 2] + "\n" + block + text[s - 2:]
        last = e
    if last is None:
        return insert_before_first(text, "sheet", [block])
    return text[:last] + "\n" + block + text[last:]


def drop_block(text: str, s: int, e: int) -> str:
    return text[:s - 2] + text[e:]          # with its leading "\n\t"


def occupied(text: str, x: float, y: float, margin: float = 2.54) -> list[str]:
    x1, y1, x2, y2 = BODY
    lo_x, hi_x = x + x1 - margin, x + x2 + margin
    lo_y, hi_y = y - y1 - margin, y - y2 + margin      # sheet y points down
    hits = []
    for head in ("symbol", "wire", "label", "text", "global_label", "hierarchical_label", "junction", "sheet", "bus"):
        for s, e in blocks(text, head, 1):
            for m in re.finditer(r"\((?:at|xy) ([-\d.]+) ([-\d.]+)", text[s:e]):
                px, py = float(m.group(1)), float(m.group(2))
                if lo_x <= px <= hi_x and lo_y <= py <= hi_y:
                    hits.append(f"{head} at {px} {py}")
    return hits


def update_cache(text: str, add: dict[str, str], drop: tuple[str, ...] = ()) -> str:
    (ls, le), = blocks(text, "lib_symbols", 1)
    block = text[ls:le]
    have = cc.top_symbols(block, 2)
    edits = [(s - 3, e, "") for n, (s, e) in have.items() if n in add or n in drop]
    keep = [n for n in have if n not in add and n not in drop]
    for name, body in add.items():
        after = [n for n in keep if n > name]
        if after:
            s, _ = have[min(after)]
            edits.append((s - 3, s - 3, "\n" + body))
        else:
            edits.append((len(block) - 2, len(block) - 2, "\n" + body))
    return text[:ls] + cc.splice(block, edits) + text[le:]


def rename_pin(block: str, old: str, new: str, etype: str | None = None) -> str:
    pat = re.compile(r'\(pin (\w+) line\n(\t+)\(at [^)]*\)\n\t+\(length [^)]*\)\n\t+\(name "' + re.escape(old) + '"')
    m = pat.search(block)
    assert m and len(pat.findall(block)) == 1, (old, len(pat.findall(block)))
    head = block[m.start():m.end()]
    new_head = head.replace(f'(name "{old}"', f'(name "{new}"')
    if etype:
        new_head = new_head.replace(f"(pin {m.group(1)} line", f"(pin {etype} line", 1)
    return block[:m.start()] + new_head + block[m.end():]


def replace_text(block: str, old: str, new: str) -> str:
    assert block.count(old) == 1, (old, block.count(old))
    return block.replace(old, new)


# ---------------------------------------------------------------- libraries
def lib_symbol(name: str, ref: str, props: list[str], unit0: str, unit1: str) -> str:
    return ('\t(symbol "' + name + '"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0)\n\t\t\t(hide yes)\n\t\t)\n'
            '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
            '\t\t(duplicate_pin_numbers_are_jumpers no)\n' + "\n".join(props) + "\n" + unit0 + "\n" + unit1 +
            "\n\t\t(embedded_fonts no)\n\t)")


def lib_pin(name: str, x: float, y: float, rot: int, number: int = 1, length: float = 2.54) -> str:
    return (f'\t\t\t(pin passive line\n\t\t\t\t(at {cc.num(x)} {cc.num(y)} {rot})\n\t\t\t\t(length {cc.num(length)})\n'
            f'\t\t\t\t(name "{name}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 0.762 0.762)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n'
            f'\t\t\t\t(number "{number}"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 0.381 0.381)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)')


def std_props(ref: str, desc: str, value: str = "") -> list[str]:
    return [cc._prop("Reference", ref, "-14.224 5.842 0", hide=True, size=1.27),
            cc._prop("Value", value, "-7.239 0 0", hide=False, size=1.27, autoplace=False,
                     justify="(justify left)").replace("\n\t\t\t(hide no)", ""),
            cc._prop("Footprint", "", "0 0 0", hide=True, size=1.27, autoplace=True),
            cc._prop("Datasheet", "", "0 0 0", hide=True, size=1.27, autoplace=True),
            cc._prop("Description", desc, "0 0 0", hide=True, size=1.27, autoplace=True)]


def processor_virtual_symbol() -> str:
    props = std_props("Proc", VIRT_DESC) + [
        cc._prop("Role", "STRUCTURE", "-11.303 9.652 0", size=1.27, autoplace=True),
        cc._prop("Kind", "PROCESSOR", "-9.906 8.001 0", size=1.27, autoplace=True),
        cc._prop("Type", "VIRTUAL", "0 0 0", size=1.27, autoplace=True),
        cc._prop("Board", "", "0 0 0", size=1.27, autoplace=True)]
    x1, y1, x2, y2 = BODY
    unit0 = '\t\t(symbol "Processor-Virtual_0_1"\n' + cc._rect(x1, y1, x2, y2) + "\n\t\t)"
    unit1 = ('\t\t(symbol "Processor-Virtual_1_1"\n' + cc._text("Virtual:", -12.7, 1.27, 1.016) + "\n" +
             cc._text("${Board}", 16.51, 1.27, 0.889, "right") + "\n" + cc._text("Host", 12.7, -1.27, 0.635) + "\n" +
             lib_pin("Host", 12.7, -5.08, 90) + "\n\t\t)")
    return lib_symbol("Processor-Virtual", "Proc", props, unit0, unit1)


def remote_io_symbol(name: str, title: str, board: str) -> str:
    props = std_props("RIO", RIO_DESC[name]) + [
        cc._prop("Role", "STRUCTURE", "-11.303 9.652 0", size=1.27, autoplace=True),
        cc._prop("Kind", "REMOTE_IO", "-9.906 8.001 0", size=1.27, autoplace=True),
        cc._prop("Board", board, "0 0 0", size=1.27, autoplace=True),
        cc._prop("Address", "", "0 0 0", size=1.27, autoplace=True),
        cc._prop("Transport", "", "0 0 0", size=1.27, autoplace=True)]
    x1, y1, x2, y2 = BODY
    unit0 = f'\t\t(symbol "{name}_0_1"\n' + cc._rect(x1, y1, x2, y2) + "\n\t\t)"
    unit1 = (f'\t\t(symbol "{name}_1_1"\n' + cc._text(title, -12.7, 1.27, 1.016) + "\n" +
             cc._text("${Board} ${Address}", 16.51, 1.27, 0.889, "right") + "\n" + cc._text("Transport", 12.7, -1.27, 0.635) + "\n" +
             lib_pin("Transport", 12.7, -5.08, 90) + "\n\t\t)")
    return lib_symbol(name, "RIO", props, unit0, unit1)


def insert_lib_symbol(text: str, sym: str, name: str) -> str:
    syms = cc.top_symbols(text, 1)
    assert name not in syms, name
    after = [n for n in syms if n > name]
    if after:
        s, _ = syms[min(after)]
        return text[:s - 2] + "\n" + sym + text[s - 2:]
    end = text.rstrip().rfind("\n)")
    return text[:end] + "\n" + sym + text[end:]


def edit_hwio(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    s, e = syms["Processor"]
    b = text[s:e]
    b = rename_pin(b, "Transport", "Host", "passive")
    b = rename_pin(b, "IO", "IO_Bus")
    b = replace_text(b, '(text "I/O"', '(text "IO_Bus"')          # the owner's body already says Host over the host pin
    b = replace_text(b, '(text "${Board} ${Address}"', '(text "${Board}"')
    b = cc.drop_prop(b, "Transport", 2)
    b = cc.drop_prop(b, "Address", 2)
    b = cc.set_prop(b, "Description", PROC_DESC, 2)
    text = cc.splice(text, [(s, e, b)])
    report.append(f"{HWIO}: Processor: pins Host (passive) and IO_Bus; Transport and Address fields dropped")
    text = insert_lib_symbol(text, processor_virtual_symbol(), "Processor-Virtual")
    text = insert_lib_symbol(text, remote_io_symbol("Remote-IO-CMRInet", "Remote I/O", "cpNode"), "Remote-IO-CMRInet")
    text = insert_lib_symbol(text, remote_io_symbol("Remote-IO-JMRI", "Remote I/O", "JMRI"), "Remote-IO-JMRI")
    report.append(f"{HWIO}: Processor-Virtual, Remote-IO-CMRInet, Remote-IO-JMRI added")
    return text


def edit_office(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    edits = []
    for name in TRANSPORTS:
        s, e = syms[name]
        b = rename_pin(text[s:e], "Encoding", "Transport")
        if '(text "Encoding"' in b:
            b = replace_text(b, '(text "Encoding"', '(text "Transport"')
        if name.endswith("MQTT"):
            b = cc.drop_prop(b, "Station", 2)
        edits.append((s, e, b))
    for name in ENCODINGS:
        s, e = syms[name]
        b = cc.drop_prop(cc.drop_prop(text[s:e], "Station", 2), "Address", 2)
        edits.append((s, e, b))
    s, e = syms["OfficeUnit"]
    b = text[s:e]
    assert b.count('(number ""') == 1, "OfficeUnit: expected exactly one unnumbered pin (Host)"
    edits.append((s, e, b.replace('(number ""', '(number "2"', 1)))
    gone = [n for n in ("FieldUnit", "FieldUnit_Virtual", "Codeline-Encoding-AAR_1") if n in syms]
    assert "FieldUnit_Virtual" in gone
    for name in gone:
        s, e = syms[name]
        edits.append((s - 2, e, ""))
    text = cc.splice(text, edits)
    report.append(f"{OFFICE}: transports' pin Encoding -> Transport, MQTT loses Station; encodings lose Station and Address; OfficeUnit's Host pin numbered 2; "
                  f"removed: {gone}")
    return text


def edit_track(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    s, e = syms["MAIN HOUSE"]
    b = text[s:e]
    assert "CP Name" not in cc.props_in(b, 2)
    b = add_prop_after(b, "Kind", cc._prop("CP Name", "", "0 0 0", size=1.27, autoplace=True), 2)
    b = cc.set_prop(b, "Value", "${CP Name}", 2)
    text = cc.splice(text, [(s, e, b)])
    report.append(f"{TRACK}: MAIN HOUSE: CP Name added; Value defaults to ${{CP Name}}")
    return text


# ---------------------------------------------------------------- sheets
def houses_cp_name(text: str, report: list[str], sheet: str) -> str:
    edits, names = [], []
    for s, e, lib_id in instances(text):
        if lib_id != f"{TRACK}:MAIN HOUSE":
            continue
        b = text[s:e]
        p = cc.props_in(b, 2)
        assert "CP Name" not in p
        value = p["Value"][0]
        bare = value[3:] if value.startswith("CP ") else value
        x, y, _ = inst_at(b)
        b = add_prop_after(b, "Kind", sheet_prop("CP Name", bare, f"{cc.num(x)} {cc.num(y)} 0"), 2)
        b = cc.set_prop(b, "Value", "CP ${CP Name}" if value.startswith("CP ") else "${CP Name}", 2)
        edits.append((s, e, b))
        names.append(bare)
    text = cc.splice(text, edits)
    report.append(f"{sheet}: MAIN HOUSE CP Name = {names}; Value is the display macro")
    return text


def bare_cp_fields(text: str, report: list[str], sheet: str) -> str:
    edits, n = [], 0
    for s, e, _ in instances(text):
        b = text[s:e]
        p = cc.props_in(b, 2)
        if "CP" in p and p["CP"][0].startswith("CP "):
            edits.append((s, e, cc.set_prop(b, "CP", p["CP"][0][3:], 2)))
            n += 1
    if n:
        report.append(f"{sheet}: {n} appliances: CP 'CP X' -> 'X' (the house's CP Name)")
    return cc.splice(text, edits)


def find_one(text: str, lib_id: str, ref: str | None = None) -> tuple[int, int]:
    hits = [(s, e) for s, e, l in instances(text) if l == lib_id and (ref is None or f'(reference "{ref}")' in text[s:e])]
    assert len(hits) == 1, (lib_id, ref, len(hits))
    return hits[0]


def interlocking_pins(text: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Sheet coordinates of the Interlocking symbol's Codeline and Host pins (rotation 0 only)."""
    s, e = find_one(text, f"{TRACK}:Interlocking")
    x, y, r = inst_at(text[s:e])
    assert r == 0
    return (x, y), (x + 17.78, y - 2.54)


def drop_wire(text: str, pts: tuple) -> str:
    want = f"(xy {cc.num(pts[0])} {cc.num(pts[1])}) (xy {cc.num(pts[2])} {cc.num(pts[3])})"
    for s, e in blocks(text, "wire", 1):
        if want in text[s:e]:
            return drop_block(text, s, e)
    raise AssertionError(f"wire {want} not found")


def drop_label(text: str, name: str, x: float, y: float) -> str:
    for s, e in blocks(text, "hierarchical_label", 1):
        b = text[s:e]
        if b.startswith(f'(hierarchical_label "{name}"') and f"(at {cc.num(x)} {cc.num(y)} " in b:
            return drop_block(text, s, e)
    raise AssertionError(f"label {name} at {x} {y} not found")


def sheet_path(text: str) -> str:
    return re.search(r'\(path "([^"]+)"', text).group(1)


def edit_unit_sheet(name: str, text: str, libs: dict[str, str], report: list[str], *,
                    codeline_label: bool, host_label: bool, drop_procs: tuple[str, ...] = (),
                    extra: list[str] | None = None) -> str:
    """The common part: houses keyed by CP Name; Codeline / Host labels on the Interlocking's pins."""
    text = houses_cp_name(text, report, name)
    text = bare_cp_fields(text, report, name)
    for ref in drop_procs:
        s, e = find_one(text, f"{HWIO}:Processor", ref)
        text = drop_block(text, s, e)
        report.append(f"{name}: Processor {ref} removed")
    (cx, cy), (hx, hy) = interlocking_pins(text)
    new = list(extra or [])
    if codeline_label:
        new.append(hier_label("Codeline", cx, cy, 180))
    if host_label:
        new.append(hier_label("Host", hx, hy, 0))
    text = insert_before_first(text, "symbol", new)
    add = {f"{TRACK}:MAIN HOUSE": cc.cached(TRACK, libs[TRACK], "MAIN HOUSE")}
    text = update_cache(text, add, drop=(f"{HWIO}:Processor",) if drop_procs else ())
    report.append(f"{name}: labels Codeline at {(cx, cy)} and Host at {(hx, hy)} as needed; MAIN HOUSE definition refreshed")
    return text


def edit_watsonville(text, libs, report):
    # the owner's Codeline label at (44.45, 22.86) reaches the Interlocking's pin once the placeholder is gone
    return edit_unit_sheet("Watsonville", text, libs, report, codeline_label=False, host_label=True,
                           drop_procs=("Proc3",), extra=[wire(44.45, 22.86, 44.45, 33.02)])


def edit_caltrain(text, libs, report):
    s, e = find_one(text, f"{HWIO}:Processor", "Proc1")
    x, y, _ = inst_at(text[s:e])
    assert (x, y) == (74.93, 16.51)
    p = cc.props_in(text[s:e], 2)
    assert p["Board"][0] == "cpNode" and p["Address"][0] == "30" and p["Transport"][0] == "CMRInet", p
    rio = symbol_instance(f"{HWIO}:Remote-IO-CMRInet", "RIO1", "Caltrain", x, y, sheet_path(text),
                          [("Role", "STRUCTURE"), ("Kind", "REMOTE_IO"), ("Board", "cpNode"), ("Address", "30"), ("Transport", "")],
                          RIO_DESC["Remote-IO-CMRInet"], pins=1)
    text = cc.splice(text, [(s, e, rio[1:])])        # the block replaces text after the leading tab
    text = drop_wire(text, (87.63, 21.59, 87.63, 26.67))       # Processor.Transport -> Interlocking.Host, the placeholder's host wire
    report.append("GilroyCalTrain: Processor Proc1 -> Remote-IO-CMRInet RIO1 'Caltrain' (cpNode, UA 30); its Transport pin labelled CMRInet")
    text = edit_unit_sheet("GilroyCalTrain", text, libs, report, codeline_label=False, host_label=True,
                           extra=[hier_label("CMRInet", 87.63, 21.59, 0)])
    return update_cache(text, {f"{HWIO}:Remote-IO-CMRInet": cc.cached(HWIO, libs[HWIO], "Remote-IO-CMRInet")}, drop=(f"{HWIO}:Processor",))


def edit_interchange(text, libs, report):
    text = drop_label(text, "Codeline", 74.93, 25.4)
    place = (74.93, 16.51)
    s, e = find_one(text, f"{HWIO}:Processor", "Proc2")
    text = drop_block(text, s, e)
    hits = occupied(text, *place)
    assert not hits, hits[:5]
    rio = symbol_instance(f"{HWIO}:Remote-IO-JMRI", "RIO2", "JMRI", *place, sheet_path(text),
                          [("Role", "STRUCTURE"), ("Kind", "REMOTE_IO"), ("Board", "JMRI"), ("Address", ""), ("Transport", "")],
                          RIO_DESC["Remote-IO-JMRI"], pins=1)
    text = insert_symbol_in_order(text, rio, *place)
    report.append(f"GilroyInterchange: Processor Proc2 removed; Remote-IO-JMRI RIO2 'JMRI' placed at {place}, Transport pin labelled JMRI_MQTT")
    text = edit_unit_sheet("GilroyInterchange", text, libs, report, codeline_label=True, host_label=True,
                           extra=[hier_label("JMRI_MQTT", place[0] + 12.7, place[1] + 5.08, 0)])
    return update_cache(text, {f"{HWIO}:Remote-IO-JMRI": cc.cached(HWIO, libs[HWIO], "Remote-IO-JMRI")}, drop=(f"{HWIO}:Processor",))


def edit_sargent(text, libs, report):
    place = (165.1, 27.94)       # above the Interlocking, clear of its hidden field anchors
    hits = occupied(text, *place)
    assert not hits, hits[:5]
    proc = symbol_instance(f"{HWIO}:Processor", "Proc6", "Sargent", *place, sheet_path(text),
                           [("Role", "STRUCTURE"), ("Kind", "PROCESSOR"), ("Board", "cpNode-Xiao")], PROC_DESC, pins=2)
    text = insert_symbol_in_order(text, proc, *place)
    hx, hy = round(place[0] + 12.7, 3), round(place[1] + 5.08, 3)   # the Processor's Host pin
    report.append(f"Sargent: Processor Proc6 'Sargent' (cpNode-Xiao) placed at {place}; Host wired to the Interlocking")
    text = edit_unit_sheet("Sargent", text, libs, report, codeline_label=True, host_label=False,
                           extra=[wire(hx, hy, hx, 40.64)])
    assert (hx, 40.64) == interlocking_pins(text)[1], interlocking_pins(text)
    return update_cache(text, {f"{HWIO}:Processor": cc.cached(HWIO, libs[HWIO], "Processor")})


def edit_plain(name):
    def f(text, libs, report):
        return edit_unit_sheet(name, text, libs, report, codeline_label=True, host_label=True)
    return f


def edit_luchessa(text, libs, report):
    s, e = find_one(text, f"{HWIO}:Processor", "Proc5")
    b = cc.drop_prop(cc.drop_prop(text[s:e], "Transport", 2), "Address", 2)
    b = cc.set_prop(b, "Description", PROC_DESC, 2)
    text = cc.splice(text, [(s, e, b)])
    text = edit_unit_sheet("Luchessa", text, libs, report, codeline_label=False, host_label=False)
    return update_cache(text, {f"{HWIO}:Processor": cc.cached(HWIO, libs[HWIO], "Processor")})


# the CP sheet boxes on South-cTc: (sheet name, codeline pin x if new, host pin x if new, remote-I/O (pin name, x))
ROOT_PINS = {
    "Watsonville":       dict(codeline=None,   host=238.76, remote=None),
    "Gilroy Caltrain":   dict(codeline=None,   host=38.1,   remote=("CMRInet", 43.18)),
    "Gilroy Interchange": dict(codeline=None,  host=66.04,  remote=("JMRI_MQTT", 71.12)),
    "Corporal":          dict(codeline=186.69, host=181.61, remote=None),
    "Christopher":       dict(codeline=160.02, host=154.94, remote=None),
    "Sargent":           dict(codeline=215.9,  host=None,   remote=None),
}
RELABEL = {(48.26, 85.09): ("CMRInet", "MQTT"), (76.2, 85.09): ("JMRI_MQTT", "MQTT")}   # Caltrain's and Interchange's Codeline ports


def edit_root(text, libs, report):
    # 1. SPCoastApp: FieldUnit_Virtual -> Processor-Virtual, same place, Host pin at the same offset
    s, e = find_one(text, f"{OFFICE}:FieldUnit_Virtual", "HOST1")
    x, y, _ = inst_at(text[s:e])
    assert (x, y) == (146.05, 19.05)
    # FieldUnit_Virtual's Host pin sat at (30.48, -5.08); Processor-Virtual's sits at (12.7, -5.08): place the symbol so
    # the pin lands on the owner's wire end at (176.53, 24.13)
    nx = round(x + 30.48 - 12.7, 3)
    virt = symbol_instance(f"{HWIO}:Processor-Virtual", "Proc7", "SPCoastApp", nx, y, sheet_path(text),
                           [("Role", "STRUCTURE"), ("Kind", "PROCESSOR"), ("Type", "VIRTUAL"), ("Board", "macOS")],
                           VIRT_DESC, pins=1)
    text = cc.splice(text, [(s, e, virt[1:])])
    assert (round(nx + 12.7, 3), round(y + 5.08, 3)) == (176.53, 24.13)
    report.append(f"South-cTc: SPCoastApp: FieldUnit_Virtual HOST1 -> Processor-Virtual Proc7 at ({cc.num(nx)}, {y}), Host pin on the owner's wire")
    # 2. JohnCTC loses the node fields; encodings lose Station / Address
    s, e = find_one(text, f"{HWIO}:Processor", "Proc4")
    b = cc.set_prop(cc.drop_prop(cc.drop_prop(text[s:e], "Transport", 2), "Address", 2), "Description", PROC_DESC, 2)
    text = cc.splice(text, [(s, e, b)])
    edits = []
    for s, e, lib_id in instances(text):
        if lib_id in (f"{OFFICE}:{n}" for n in ENCODINGS):
            edits.append((s, e, cc.drop_prop(cc.drop_prop(text[s:e], "Station", 2), "Address", 2)))
        if lib_id == f"{OFFICE}:Codeline-Transport-MQTT":
            edits.append((s, e, cc.drop_prop(text[s:e], "Station", 2)))
    text = cc.splice(text, edits)
    report.append("South-cTc: JohnCTC: Transport and Address dropped; AAR and 506 encodings: Station and Address dropped")
    # 3. the Codeline ports of Caltrain and Interchange go to MQTT, not to their I/O transports
    edits = []
    for s, e in blocks(text, "global_label", 1):
        b = text[s:e]
        m = re.match(r'\(global_label "([^"]+)"\n\t\t\(shape \w+\)\n\t\t\(at ([-\d.]+) ([-\d.]+) ', b)
        key = (float(m.group(2)), float(m.group(3)))
        if key in RELABEL:
            old, new = RELABEL[key]
            assert m.group(1) == old, (key, m.group(1))
            edits.append((s, e, b.replace(f'(global_label "{old}"', f'(global_label "{new}"', 1)))
    assert len(edits) == len(RELABEL)
    text = cc.splice(text, edits)
    report.append("South-cTc: Gilroy Caltrain's and Gilroy Interchange's Codeline ports rewired from CMRInet / JMRI_MQTT to MQTT")
    # 4. new sheet pins, labels and wires
    new_wires, new_labels = [], [global_label("SPCoastApp", 176.53, 30.48, 0)]      # on the app's Host wire
    sheet_edits = []
    for s, e in blocks(text, "sheet", 1):
        b = text[s:e]
        name = re.search(r'\(property "Sheetname" "([^"]+)"', b).group(1)
        if name not in ROOT_PINS:
            continue
        sx, sy = map(float, re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)\)", b).groups())
        sw = float(re.search(r"\n\t\t\(size ([-\d.]+) ", b).group(1))
        assert sy == SHEET_TOP, (name, sy)
        spec = ROOT_PINS[name]
        pins = []
        for pin_name, px, net in ((("Codeline", spec["codeline"], "MQTT"), ("Host", spec["host"], "SPCoastApp")) +
                                  ((spec["remote"] + (spec["remote"][0],),) if spec["remote"] else ())):
            if px is None:
                continue
            assert sx < px < sx + sw, (name, pin_name, px)
            assert f"(at {cc.num(px)} {cc.num(SHEET_TOP)} " not in b, (name, pin_name, px)
            pins.append(sheet_pin(pin_name, px, SHEET_TOP))
            new_wires.append(wire(px, LABEL_Y, px, SHEET_TOP))
            new_labels.append(global_label(net, px, LABEL_Y, 90))
        i = b.index("\n\t\t(instances")
        sheet_edits.append((s, e, b[:i] + "\n" + "\n".join(pins) + b[i:]))
    text = cc.splice(text, sheet_edits)
    text = insert_before_first(text, "global_label", new_wires)
    text = insert_before_first(text, "symbol", new_labels)
    report.append(f"South-cTc: {sum(1 for v in ROOT_PINS.values() for k in ('codeline', 'host') if v[k]) + sum(1 for v in ROOT_PINS.values() if v['remote'])} "
                  "sheet pins added with their labels and wires; SPCoastApp labelled on its Host wire")
    s, e = find_one(text, f"{OFFICE}:OfficeUnit", "MACHINE2002")
    b = text[s:e]
    assert b.count('\n\t\t(pin ""\n') == 1, "OfficeUnit instance: expected one unnumbered pin entry"
    text = cc.splice(text, [(s, e, b.replace('\n\t\t(pin ""\n', '\n\t\t(pin "2"\n', 1))])
    report.append("South-cTc: OfficeUnit's Host pin entry numbered 2")
    add = {f"{HWIO}:Processor": cc.cached(HWIO, libs[HWIO], "Processor"),
           f"{HWIO}:Processor-Virtual": cc.cached(HWIO, libs[HWIO], "Processor-Virtual")}
    add |= {f"{OFFICE}:{n}": cc.cached(OFFICE, libs[OFFICE], n) for n in TRANSPORTS + ENCODINGS + ("OfficeUnit",)}
    return update_cache(text, add, drop=(f"{OFFICE}:FieldUnit_Virtual",))


def edit_caltrain_panel(text, libs, report):
    s, e = find_one(text, f"{OFFICE}:Codeline-Encoding-AAR", "Encoding1")
    assert 'Station" "Luchessa"' in text[s:e]
    text = drop_block(text, s, e)
    report.append("GilroyCalTrain-Panel: stray AAR Tokens instance Encoding1 (Station Luchessa) removed; encodings are declared once beside their transport")
    return update_cache(text, {}, drop=(f"{OFFICE}:Codeline-Encoding-AAR",))


SHEETS = [("GilroyCalTrain-Panel", edit_caltrain_panel), ("Watsonville", edit_watsonville), ("GilroyCalTrain", edit_caltrain), ("GilroyInterchange", edit_interchange),
          ("Sargent", edit_sargent), ("Corporal", edit_plain("Corporal")), ("Christopher", edit_plain("Christopher")),
          ("Luchessa", edit_luchessa), ("South-cTc", edit_root)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock on the project or a library; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    paths = {lib: LIBDIR / f"{lib}.kicad_sym" for lib in (HWIO, OFFICE, TRACK)}
    libs = {HWIO: edit_hwio(paths[HWIO].read_text(), report),
            OFFICE: edit_office(paths[OFFICE].read_text(), report),
            TRACK: edit_track(paths[TRACK].read_text(), report)}
    sheets = {}
    for name, fn in SHEETS:
        p = SPCOAST / f"{name}.kicad_sch"
        sheets[p] = fn(p.read_text(), libs, report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    for lib, t in libs.items():
        paths[lib].write_text(t)
    for p, t in sheets.items():
        p.write_text(t)
    print(f"wrote {', '.join(p.name for p in paths.values())} and {', '.join(p.name for p in sheets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
