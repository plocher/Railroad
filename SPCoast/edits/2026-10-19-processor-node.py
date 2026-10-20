#!/usr/bin/env python3
"""Processor node, 2026-10-19: ADR 0005 §9 applied to the libraries, Gilroy Caltrain and the root sheet.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-19-processor-node.py [--dry-run]

Ruling (FieldUnit-Subdivision ADR 0005, accepted 2026-10-19): a bus is declared once by a symbol that
holds every fact of the bus, and an attachment carries only its own address on that bus. A CMRInet
node is a `Processor` with `Transport` and `Address` (the UA); its drivers carry `Bit` only.

Library Railroad-HardwareIO:
- add `Processor` (Role STRUCTURE, Kind PROCESSOR, no pins; fields Board, Transport, Address, empty
  defaults; shown Value is the processor's name), modelled on Railroad-Trackplan:Interlocking;
- Driver-CMRI-IB / -OB lose `UA` and `Address`; Value renders `IN.${Bit}` / `OUT.${Bit}`; the body text
  follows; the Description says where the node is declared.
Library Railroad-Office: every Codeline-Transport-* gains `Host` (empty = the office processor).

Sheet Gilroy Caltrain: one `Processor` "Caltrain" (Transport CMRInet, Address 30, Board cpNode) placed in
free space at the top of the sheet; the 34 CMRI drivers lose `UA` and `Address` and take the new Value
and Description; the embedded definitions of the three symbols are refreshed from the library.
Root sheet South-cTc: the MQTT transport loses `Station` (an encoding fact, ADR 0001); the four transport
instances gain `Host` ""; their embedded definitions are refreshed.

Only the named definitions on the named sheets are refreshed (ADR 0007 §2.4). Nothing else changes.

Formatting: the two libraries and South-cTc come out byte-identical to KiCad's own forced resave
(`kicad-cli sym upgrade --force`, `sch upgrade --force` on copies). GilroyCalTrain does not: KiCad files a
new placed symbol among the existing ones in its own order (after the last unit-1 symbol here), so the
sheet this script writes was resaved by KiCad on a copy and the copy adopted, after checking that the
only difference was the position of the new block (2026-10-19). A later script that adds a symbol
should end with that step.
Gate: 2026-10-19-processor-node-gate.py on production/pre-processor.net and post-processor.net.
Dry run prints the report and writes nothing. KiCad must be closed.
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
from kicad_services.sch_text import blocks  # noqa: E402

SPCOAST, LIBDIR = cc.SPCOAST, cc.LIBDIR
HWIO, OFFICE = "Railroad-HardwareIO", "Railroad-Office"
CMRI = {"Driver-CMRI-IB": "IN", "Driver-CMRI-OB": "OUT"}
CMRI_DESC = {
    "Driver-CMRI-IB": "CMRInet digital input. Bit = this bit on the node the sheet's Processor declares (ADR 0005).",
    "Driver-CMRI-OB": "CMRInet digital output. Bit = this bit on the node the sheet's Processor declares (ADR 0005).",
}
PROC_DESC = ("A processor: declares the I2C bus and GPIO pins of the chips and drivers in its scope; with "
             "Transport and Address it is a node on that code line (ADR 0005).")
TRANSPORTS = ("Codeline-Transport-CMRInet", "Codeline-Transport-MQTT", "Codeline-Transport-Loconet",
              "Codeline-Transport-TimeCode")
NODE = {"value": "Caltrain", "Transport": "CMRInet", "Address": "30", "Board": "cpNode"}
NODE_REF = "Proc1"
PLACE = (152.4, 25.4)            # free space right of the Interlocking box, inside the frame (checked at run time)
BOX = (-17.018, 1.27, 36.83, 4.826)   # Interlocking's body, widened so the name and the node facts share the line


# ---------------------------------------------------------------- library text
def processor_symbol() -> str:
    x1, y1, x2, y2 = BOX
    props = [cc._prop("Reference", "Proc", "-14.224 5.842 0", hide=True, size=1.27),
             # a shown property carries no (hide ...) line in KiCad 10's own writing
             cc._prop("Value", "", "-3.048 3.048 0", hide=False, size=1.27, autoplace=False,
                      justify="(justify left)").replace("\n\t\t\t(hide no)", ""),
             cc._prop("Footprint", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Datasheet", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Description", PROC_DESC, "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Role", "STRUCTURE", "-11.303 9.652 0", size=1.27, autoplace=True),
             cc._prop("Kind", "PROCESSOR", "-9.906 8.001 0", size=1.27, autoplace=True),
             cc._prop("Board", "", "0 0 0", size=1.27, autoplace=True),
             cc._prop("Transport", "", "0 0 0", size=1.27, autoplace=True),
             cc._prop("Address", "", "0 0 0", size=1.27, autoplace=True)]
    unit0 = '\t\t(symbol "Processor_0_1"\n' + cc._rect(x1, y1, x2, y2) + "\n\t\t)"
    unit1 = ('\t\t(symbol "Processor_1_1"\n' + cc._text("Processor:", -10.16, 3.048, 1.27) + "\n" +
             cc._text("${Board} ${Transport} ${Address}", 36.195, 3.048, 0.889, "right") + "\n\t\t)")
    return ('\t(symbol "Processor"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0)\n\t\t\t(hide yes)\n\t\t)\n'
            '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
            '\t\t(duplicate_pin_numbers_are_jumpers no)\n' + "\n".join(props) + "\n" + unit0 + "\n" + unit1 +
            "\n\t\t(embedded_fonts no)\n\t)")


def insert_symbol(text: str, sym: str, name: str) -> str:
    """Add a top-level symbol where KiCad's own save puts it: symbols in name order."""
    syms = cc.top_symbols(text, 1)
    after = [n for n in syms if n > name]
    if after:
        s, _ = syms[min(after)]
        return text[:s - 2] + "\n" + sym + text[s - 2:]   # on its own lines before "\t(symbol" of the next name
    end = text.rstrip().rfind("\n)")
    assert end > 0
    return text[:end] + "\n" + sym + text[end:]


def add_prop_before_units(block: str, prop: str) -> str:
    """Insert a depth-2 property as the last property of a library symbol (before its first unit)."""
    i = block.index('\n\t\t(symbol "')
    return block[:i] + "\n" + prop + block[i:]


def edit_hwio(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    assert "Processor" not in syms, "Processor already exists"
    edits = []
    for name, direction in CMRI.items():
        s, e = syms[name]
        b = text[s:e]
        b = cc.drop_prop(b, "UA", 2)
        b = cc.drop_prop(b, "Address", 2)
        b = cc.set_prop(b, "Value", f"{direction}.${{Bit}}", 2)
        b = cc.set_prop(b, "Description", CMRI_DESC[name], 2)
        old = f'(text "CMRI UA${{Address}}.{direction}.${{Bit}}"'
        assert b.count(old) == 1, (name, old)
        b = b.replace(old, f'(text "CMRI {direction}.${{Bit}}"')
        edits.append((s, e, b))
        report.append(f"{HWIO}: {name}: UA and Address dropped; Value {direction}.${{Bit}}; body text and Description follow")
    text = cc.splice(text, edits)
    text = insert_symbol(text, processor_symbol(), "Processor")
    report.append(f"{HWIO}: Processor added (Role STRUCTURE, Kind PROCESSOR; Board, Transport, Address)")
    return text


def edit_office(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    edits = []
    for name in TRANSPORTS:
        s, e = syms[name]
        b = text[s:e]
        assert "Host" not in cc.props_in(b, 2), name
        edits.append((s, e, add_prop_before_units(b, cc._prop("Host", "", "0 0 0", size=1.27, autoplace=True))))
        report.append(f"{OFFICE}: {name}: Host added (empty = the office processor)")
    return cc.splice(text, edits)


# ---------------------------------------------------------------- sheet text
def update_cache_sorted(text: str, add: dict[str, str]) -> str:
    """Replace or add lib_symbols entries where KiCad's own save puts them: in name order."""
    (ls, le), = blocks(text, "lib_symbols", 1)
    block = text[ls:le]
    have = cc.top_symbols(block, 2)
    edits = [(s - 3, e, "") for n, (s, e) in have.items() if n in add]       # drop the old entry with its "\n\t\t"
    keep = [n for n in have if n not in add]
    for name, body in add.items():
        after = [n for n in keep if n > name]
        if after:
            s, _ = have[min(after)]
            edits.append((s - 3, s - 3, "\n" + body))
        else:
            edits.append((len(block) - 2, len(block) - 2, "\n" + body))     # before the closing "\t)"
    return text[:ls] + cc.splice(block, edits) + text[le:]


def instances(text: str):
    for s, e in blocks(text, "symbol", 1):
        m = re.match(r'\(symbol\n\t\t\(lib_id "([^"]+)"', text[s:e])
        if m:
            yield s, e, m.group(1)


def sheet_prop(name, value, at, hide=True, autoplace=True, size=1.27, justify=None):
    """A property as KiCad 10 writes it on a placed symbol: (at) (hide) (show_name) (do_not_autoplace) (effects)."""
    j = f"\n\t\t\t\t{justify}" if justify else ""
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {at}){h}\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace {"no" if autoplace else "yes"})\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {size} {size})\n\t\t\t\t){j}\n\t\t\t)\n\t\t)')


def shown_prop(name, value, at, size=1.27, justify=None):
    j = f"\n\t\t\t\t{justify}" if justify else ""
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at {at})\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size {size} {size})\n\t\t\t\t){j}\n\t\t\t)\n\t\t)')


def processor_instance(x: float, y: float, path: str) -> str:
    at = f"{cc.num(x)} {cc.num(y)} 0"
    props = [sheet_prop("Reference", NODE_REF, f"{cc.num(x - 14.224)} {cc.num(y - 5.842)} 0", autoplace=False),
             sheet_prop("Value", NODE["value"], f"{cc.num(x - 3.048)} {cc.num(y - 3.048)} 0", hide=False, justify="(justify left)"),
             sheet_prop("Footprint", "", at),
             sheet_prop("Datasheet", "", at),
             sheet_prop("Description", PROC_DESC, at),
             sheet_prop("Role", "STRUCTURE", at),
             sheet_prop("Kind", "PROCESSOR", at),
             sheet_prop("Board", NODE["Board"], at),
             sheet_prop("Transport", NODE["Transport"], at),
             sheet_prop("Address", NODE["Address"], at)]
    return (f'\t(symbol\n\t\t(lib_id "{HWIO}:Processor")\n\t\t(at {at})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n'
            f'\t\t(uuid "{cc.uid()}")\n' + "\n".join(props) +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{NODE_REF}")\n'
            f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def occupied(text: str, x: float, y: float, margin: float = 2.54) -> list[str]:
    """Anything with a coordinate inside the Processor's body box at (x, y), plus a margin."""
    x1, y1, x2, y2 = BOX
    lo_x, hi_x = x + x1 - margin, x + x2 + margin
    lo_y, hi_y = y - y2 - margin, y - y1 + margin   # the sheet's y axis points down
    hits = []
    for head in ("symbol", "wire", "label", "text", "global_label", "hierarchical_label", "junction", "sheet", "bus"):
        for s, e in blocks(text, head, 1):
            for m in re.finditer(r"\((?:at|xy) ([-\d.]+) ([-\d.]+)", text[s:e]):
                px, py = float(m.group(1)), float(m.group(2))
                if lo_x <= px <= hi_x and lo_y <= py <= hi_y:
                    hits.append(f"{head} at {px} {py}")
    return hits


def edit_caltrain(text: str, hwio_lib: str, report: list[str]) -> str:
    assert f'(lib_id "{HWIO}:Processor")' not in text
    hits = occupied(text, *PLACE)
    assert not hits, f"placement {PLACE} is not free: {hits[:5]}"
    refs = {m.group(1) for m in re.finditer(r'\(reference "([^"]+)"\)', text)}
    assert NODE_REF not in refs
    path = re.search(r'\(path "([^"]+)"', text).group(1)
    edits, n, insert_at = [], 0, None
    for s, e, lib_id in instances(text):
        # KiCad saves placed symbols in (unit, body style, x, y) order (SCH_ITEM::compare); keep that order
        b = text[s:e]
        unit = int(re.search(r"\n\t\t\(unit (\d+)\)", b).group(1))
        ax, ay = map(float, re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", b).groups())
        if insert_at is None and (unit, ax, ay) > (1, *PLACE):
            insert_at = s - 2      # before "\t(symbol" of this block
        last = e
        name = lib_id.split(":")[1]
        if lib_id.split(":")[0] != HWIO or name not in CMRI:
            continue
        b = text[s:e]
        p = cc.props_in(b, 2)
        assert p["Address"][0] == "30" and p["UA"][0] == "${Address}", (p["Address"], p["UA"])
        b = cc.drop_prop(b, "UA", 2)
        b = cc.drop_prop(b, "Address", 2)
        b = cc.set_prop(b, "Value", f"{CMRI[name]}.${{Bit}}", 2)
        b = cc.set_prop(b, "Description", CMRI_DESC[name], 2)
        edits.append((s, e, b))
        n += 1
    assert n == 34, n
    if insert_at is None:
        edits.append((last, last, "\n" + processor_instance(*PLACE, path)))
    else:
        edits.append((insert_at, insert_at, "\n" + processor_instance(*PLACE, path)))
    text = cc.splice(text, edits)
    add = {f"{HWIO}:{nm}": cc.cached(HWIO, hwio_lib, nm) for nm in ("Processor", *CMRI)}
    text = update_cache_sorted(text, add)
    report.append(f"GilroyCalTrain: {n} CMRI drivers: UA and Address dropped, Value and Description follow the library; "
                  f"Processor {NODE_REF} '{NODE['value']}' (Transport {NODE['Transport']}, Address {NODE['Address']}, "
                  f"Board {NODE['Board']}) placed at {PLACE}; embedded definitions refreshed: Processor, Driver-CMRI-IB, Driver-CMRI-OB")
    return text


def edit_root(text: str, office_lib: str, report: list[str]) -> str:
    edits, seen = [], []
    for s, e, lib_id in instances(text):
        lib, name = lib_id.split(":")
        if lib != OFFICE or name not in TRANSPORTS:
            continue
        b = text[s:e]
        p = cc.props_in(b, 2)
        assert "Host" not in p, name
        if name == "Codeline-Transport-MQTT":
            assert "Station" in p, "MQTT transport has no Station to drop"
            b = cc.drop_prop(b, "Station", 2)
        at = re.search(r"\(at ([-\d.]+ [-\d.]+) \d+\)", b).group(1)
        host = sheet_prop("Host", "", f"{at} 0")
        i = b.index("\n\t\t(pin ") if "\n\t\t(pin " in b else b.index("\n\t\t(instances")
        b = b[:i] + "\n" + host + b[i:]
        edits.append((s, e, b))
        seen.append(name)
    assert sorted(seen) == sorted(TRANSPORTS), seen
    text = cc.splice(text, edits)
    add = {f"{OFFICE}:{nm}": cc.cached(OFFICE, office_lib, nm) for nm in TRANSPORTS}
    text = update_cache_sorted(text, add)
    report.append("South-cTc: MQTT transport: Station dropped; four transports: Host \"\" added; embedded definitions refreshed")
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock on the project or a library; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    hwio_path, office_path = LIBDIR / f"{HWIO}.kicad_sym", LIBDIR / f"{OFFICE}.kicad_sym"
    hwio = edit_hwio(hwio_path.read_text(), report)
    office = edit_office(office_path.read_text(), report)
    caltrain_path, root_path = SPCOAST / "GilroyCalTrain.kicad_sch", SPCOAST / "South-cTc.kicad_sch"
    caltrain = edit_caltrain(caltrain_path.read_text(), hwio, report)
    root = edit_root(root_path.read_text(), office, report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    for p, t in ((hwio_path, hwio), (office_path, office), (caltrain_path, caltrain), (root_path, root)):
        p.write_text(t)
    print(f"wrote {hwio_path.name}, {office_path.name}, {caltrain_path.name}, {root_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
