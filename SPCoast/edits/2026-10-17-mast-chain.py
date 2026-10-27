#!/usr/bin/env python3
"""One-off, 2026-10-17 (second pass): the mast is the field-side anchor; the indication-to-aspect
table is an explicit multi-unit cast; CMRI bits carry Address (node) and Bit.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python \
        SPCoast/edits/2026-10-17-mast-chain.py [--dry-run]

Decided 2026-10-17 after the first pass (2026-10-17-cast-chain.py): the per-head anchors
Head-CPL/CL/Semaphore were the mast's indication table collapsed into a symbol, a magic cast
again. The chain is now

    [Mast 774NAB] -indication- [Cast-Aspect-CPL unit A] -aspect- [Cast-Encoder-CPL] -bits- [chip]
                               [Cast-Aspect-CPL unit B] -aspect- ...

One unit per head letter, so placing unit B beside mast 774N is head 774NB with nothing typed;
the reader derives every head name from mast plus unit. Style's home is the aspect cast.

What this script does, by text edits that keep every untouched byte:
- Railroad-Field: retires Head-CPL, Head-CL, Head-Semaphore; adds the multi-unit casts
  Cast-Aspect-CPL, Cast-Aspect-CL, Cast-Aspect-Semaphore (units A..E: IND in, ASPECT out).
- Railroad-HardwareIO: Driver-CMRI-IB/OB: Address = the node (the fold key, as every chip),
  Bit = this symbol's bit, UA = ${Address} as a display echo, Value = UA${Address}.IN.${Bit}.
- Sargent, GilroyCalTrain: each Head-* anchor becomes one unit of the aspect cast for its style,
  placed so its ASPECT output lands where the anchor's did; one Mast anchor per mast, joined to
  its units' IND pins by wires. The 34 CMRI bits on Caltrain: Address <- UA, Bit <- Address.
KiCad must be closed. Follow with the field sync, kicad-cli netlist + ERC, and the gate.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cast_chain", HERE / "2026-10-17-cast-chain.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks  # noqa: E402

RAILROAD, SPCOAST, LIBDIR, FIELD, HWIO = cc.RAILROAD, cc.SPCOAST, cc.LIBDIR, cc.FIELD, cc.HWIO
num, uid, _prop, _pin, _rect, _text = cc.num, cc.uid, cc._prop, cc._pin, cc._rect, cc._text
OLD_ANCHORS = {"Head-CPL": "Cast-Aspect-CPL", "Head-CL": "Cast-Aspect-CL", "Head-Semaphore": "Cast-Aspect-Semaphore"}
LETTERS = "ABCDE"
ASPECT_DX = 20.32  # a unit's IND input sits this far left of its ASPECT output
BUS_DX = 2.54      # the mast's indication bus sits this far left of the leftmost IND pin


# ---------------------------------------------------------------- library
def aspect_cast(name: str, style: str, description: str) -> str:
    fields = [("Role", "CAST"), ("Style", style), ("Pin.IND", "indication"), ("Pin.ASPECT", "aspect"), ("ki_locked", "")]
    props = [_prop("Reference", "Cast", "0 2.54 0", hide=True, size=0.762),
             _prop("Value", "", "0 0 0", hide=True, size=1.27, autoplace=False),
             _prop("Footprint", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             _prop("Datasheet", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             _prop("Description", description, "0 -5.08 0", hide=True, size=1.27, autoplace=True)]
    props += [_prop(k, v, "0 0 0") for k, v in fields]
    units = []
    for n, letter in enumerate(LETTERS, 1):
        body = [_rect(-17.78, 1.27, -2.54, -1.27),
                _text(f"{style} {letter}", -10.16, 2.794, 0.762),
                _pin("input", -20.32, 0, 0, "IND", str(2 * n - 1)),
                _pin("output", 0, 0, 180, "ASPECT", str(2 * n))]
        units.append(f'\t\t(symbol "{name}_{n}_1"\n' + "\n".join(body) + "\n\t\t)")
    return (f'\t(symbol "{name}"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0.889)\n\t\t)\n'
            f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
            f'\t\t(duplicate_pin_numbers_are_jumpers no)\n' + "\n".join(props) + "\n" + "\n".join(units) +
            "\n\t\t(embedded_fonts no)\n\t)")


NEW_FIELD = {
    "Cast-Aspect-CPL": aspect_cast("Cast-Aspect-CPL", "CPL",
                                   "Mast indication to one colour-position-light head's aspect by the rulebook's indication table. One unit per head letter: unit B beside mast 774N is head 774NB."),
    "Cast-Aspect-CL": aspect_cast("Cast-Aspect-CL", "CL",
                                  "Mast indication to one colour-light head's aspect by the rulebook's indication table. One unit per head letter."),
    "Cast-Aspect-Semaphore": aspect_cast("Cast-Aspect-Semaphore", "LQ, UQ",
                                         "Mast indication to one semaphore head's aspect (arm and lamp) by the rulebook's indication table, lower or upper quadrant by Style. One unit per head letter."),
}


def edit_field_library(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    edits = []
    for name in OLD_ANCHORS:
        s, e = syms[name]
        edits.append((s - 2, e, ""))
        report.append(f"{FIELD}: retire {name}")
    for name in NEW_FIELD:
        if name in syms:
            raise SystemExit(f"{FIELD} already has {name}")
        report.append(f"{FIELD}: add {name} (units A..E)")
    tail = text.rindex("\n)")
    edits.append((tail, tail, "\n" + "\n".join(NEW_FIELD.values())))
    return cc.splice(text, edits)


def edit_cmri_symbol(block: str, direction: str) -> str:
    b = cc.set_prop(block, "Value", f"UA${{Address}}.{direction}.${{Bit}}", 2)
    b = cc.set_prop(b, "Address", "", 2)
    b = cc.dup_prop(b, "Address", "Bit", 2)
    b = cc.set_prop(b, "UA", "${Address}", 2)
    return cc.set_prop(b, "Description", f"CMRInet digital {'input' if direction == 'IN' else 'output'}. "
                       "Address = the node (UA), the chip every bit of that node folds into; Bit = this bit. UA echoes Address.", 2)


def edit_hwio_library(text: str, report: list[str]) -> str:
    syms = cc.top_symbols(text, 1)
    edits = []
    for name, direction in (("Driver-CMRI-IB", "IN"), ("Driver-CMRI-OB", "OUT")):
        s, e = syms[name]
        edits.append((s, e, edit_cmri_symbol(text[s:e], direction)))
        report.append(f"{HWIO}: {name}: Address = node, Bit = bit, UA = ${{Address}}, Value = UA${{Address}}.{direction}.${{Bit}}")
    return cc.splice(text, edits)


# ---------------------------------------------------------------- sheets
def instance_unit(lib_id, x, y, ref, value, description, fields, pin_numbers, path, unit=1) -> str:
    at = f"{num(x)} {num(y)} 0"
    props = [_prop("Reference", ref, f"{num(x - 2.54)} {num(y - 3.81)} 0", size=0.762),
             _prop("Value", value, at, size=1.27, autoplace=True),
             _prop("Footprint", "", at, size=1.27, autoplace=True),
             _prop("Datasheet", "", at, size=1.27, autoplace=True),
             _prop("Description", description, f"{num(x)} {num(y + 6.604)} 0", size=1.27, autoplace=True)]
    props += [_prop(k, v, at) for k, v in fields]
    pins = "".join(f'\n\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for n in pin_numbers)
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at})\n\t\t(unit {unit})\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n'
            f'\t\t(uuid "{uid()}")\n' + "\n".join(props) + pins +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def junction(x, y) -> str:
    return f'\t(junction\n\t\t(at {num(x)} {num(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "{uid()}")\n\t)'


def cast_fields(lib_text: str, name: str) -> tuple[str, list[tuple[str, str]]]:
    d, f, _ = cc.lib_fields(lib_text, name)
    return d, [(k, v) for k, v in f if k != "ki_locked"]


def rewrite_masts(text: str, field_lib: str, casts: cc.Counter, masts: cc.Counter, report: list[str], sheet: str) -> str:
    heads = []  # (s, e, anchor part, head value, x, y, path)
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        m = re.search(r'\n\t\t\(lib_id "Railroad-Field:(Head-[^"]+)"', b)
        if not m:
            continue
        p = cc.props_in(b, 2)
        x, y, _ = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)", b).groups()
        heads.append((s, e, m.group(1), p["Value"][0], float(x), float(y), re.search(r'\(path "([^"]+)"', b).group(1)))
    if not heads:
        return text
    by_mast = defaultdict(list)
    for h in heads:
        by_mast[h[3][:-1]].append(h)
    edits = [(s - 2, e, "") for s, e, *_ in heads]
    added, used = [], {"Mast"}
    for mast, hs in sorted(by_mast.items()):
        path = hs[0][6]
        ref_by_cast = {}
        ind_points = []
        for s, e, part, value, x, y, _ in sorted(hs, key=lambda h: (h[5], h[4])):
            cast_name = OLD_ANCHORS[part]
            letter = value[-1]
            if letter not in LETTERS:
                raise SystemExit(f"{sheet}: head {value} has no unit letter")
            unit = LETTERS.index(letter) + 1
            if cast_name not in ref_by_cast:
                ref_by_cast[cast_name] = casts.next("Cast")
            d, f = cast_fields(field_lib, cast_name)
            added.append(instance_unit(f"{FIELD}:{cast_name}", x, y, ref_by_cast[cast_name], "", d, f,
                                       [str(2 * unit - 1), str(2 * unit)], path, unit))
            ind_points.append((x - ASPECT_DX, y))
            used.add(cast_name)
            report.append(f"{sheet}: head {value} ({part}) -> {cast_name} {ref_by_cast[cast_name]} unit {letter} at {num(x)} {num(y)}")
        d, f, n = cc.lib_fields(field_lib, "Mast")
        mref = masts.next("DevMast")
        if len(ind_points) == 1:
            (bx, by), = ind_points
        else:
            bx = min(x for x, _ in ind_points) - BUS_DX
            ys = sorted(y for _, y in ind_points)
            by = ys[0]
            for x, y in ind_points:
                added.append(cc.wire(x, y, bx, y))
            for y1, y2 in zip(ys, ys[1:]):
                added.append(cc.wire(bx, y1, bx, y2))
            for y in ys[1:-1]:
                added.append(junction(bx, y))
        added.append(instance_unit(f"{FIELD}:Mast", bx, by, mref, mast, d, f, n, path))
        report.append(f"{sheet}: mast {mast} -> Mast {mref} at {num(bx)} {num(by)}, {len(ind_points)} head(s)")
    first = min(s for s, _, _ in edits)
    edits.append((first, first, "\n" + "\n".join(added)))
    text = cc.splice(text, edits)
    return cc.update_cache(text, {f"{FIELD}:{n}": cc.cached(FIELD, field_lib, n) for n in sorted(used)},
                           [f"{FIELD}:{n}" for n in OLD_ANCHORS])


def rewrite_cmri(text: str, hwio_lib: str, report: list[str], sheet: str) -> str:
    edits, used = [], set()
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        m = re.search(r'\n\t\t\(lib_id "Railroad-HardwareIO:(Driver-CMRI-[IO]B)"', b)
        if not m:
            continue
        name = m.group(1)
        used.add(name)
        p = cc.props_in(b, 2)
        node, bit = p["UA"][0], p["Address"][0]
        direction = "IN" if name.endswith("IB") else "OUT"
        nb = cc.set_prop(b, "Value", f"UA${{Address}}.{direction}.${{Bit}}", 2)
        nb = cc.set_prop(nb, "Address", node, 2)
        nb = cc.set_prop(nb, "UA", "${Address}", 2)
        if "Bit" not in p:
            nb = cc.dup_prop(nb, "Address", "Bit", 2)
        nb = cc.set_prop(nb, "Bit", bit, 2)
        edits.append((s, e, nb))
    if not edits:
        return text
    report.append(f"{sheet}: {len(edits)} CMRI bits: Address <- UA, Bit <- Address, UA = ${{Address}}")
    text = cc.splice(text, edits)
    return cc.update_cache(text, {f"{HWIO}:{n}": cc.cached(HWIO, hwio_lib, n) for n in sorted(used)},
                           [f"{HWIO}:{n}" for n in used])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(SPCOAST.glob("~*.lck")):
        print("KiCad holds a lock on the project; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    field_path, hwio_path = LIBDIR / f"{FIELD}.kicad_sym", LIBDIR / f"{HWIO}.kicad_sym"
    field_lib = edit_field_library(field_path.read_text(), report)
    hwio_lib = edit_hwio_library(hwio_path.read_text(), report)
    casts, masts = cc.Counter(12), cc.Counter(0)  # Cast1..12 were placed by the first pass
    sheets = {}
    for name in ("Sargent", "GilroyCalTrain"):
        p = SPCOAST / f"{name}.kicad_sch"
        t = rewrite_masts(p.read_text(), field_lib, casts, masts, report, name)
        sheets[p] = rewrite_cmri(t, hwio_lib, report, name)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    field_path.write_text(field_lib)
    hwio_path.write_text(hwio_lib)
    for p, t in sheets.items():
        p.write_text(t)
    print(f"wrote {field_path.name}, {hwio_path.name}, {', '.join(p.name for p in sheets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
