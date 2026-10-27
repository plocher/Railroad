#!/usr/bin/env python3
"""Third pass, 2026-10-18: one-step head casts with an explicit Head letter.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-18-head-cast.py [--dry-run]

Owner ruling (2026-10-18): the multi-unit aspect casts hid the head assignment in a KiCad unit
number. The head letter is a railroad fact and belongs on the symbol as a field. And the two-step
chain (indication to aspect, aspect to lamps) said "CPL" twice; one cast per head rendering is
enough. The aspect is a fact the reader derives from style and indication; it is no longer drawn.

Before:  [Mast 774N] -IND- [Cast-Aspect-CPL unit B] -ASPECT- [Cast-Lamps-RYG] -R/Y/G- chip
After:   [Mast 774N] -IND- [Cast-Head-CPL Head=B] -R/Y/G- chip

Library (Railroad-Field): retire Cast-Aspect-CPL/CL/Semaphore, Cast-Lamps-RYG, Cast-Encoder-CPL,
Cast-Lamps-RGB, Cast-Color, Cast-Arm; add Cast-Head-CPL, Cast-Head-CPL-Encoded, Cast-Head-RGB,
Cast-Head-Color, Cast-Head-Semaphore. Each is Role CAST, one IND input (indication), the old
symbol's output pins unchanged in name, number, position and type, a shown `Head` field, and
`Style` fixed (CPL) or instance-written (RGB, Color, Semaphore). Bodies follow the owner's tidy of
2026-10-18: one width (-20.32 .. -2.54), every visible text inside the body, hidden Pin.* fields
beside their pins. The encoder keeps the owner's select-code table.

Sheets (Sargent, GilroyCalTrain): each aspect-cast unit and the casts on its ASPECT net collapse
into head casts placed where the downstream casts stand, so the output pins and every chip
connection stay put. Head = the unit's letter; Style = the unit's Style where the symbol does not
fix it. The unit, its aspect wires and labels go; a wire runs from the unit's old IND tap to the
new IND pin, or a `<mast>_IND` label pair when the cast is not on the tap's row. Pairing comes
from the baseline netlist (production/pre-head.net), never from coordinates.

Project: the ERC severities set to ignore for the multi-unit casts go back to warning.
Dry run prints the report and writes nothing. KiCad must be closed.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cast_chain", HERE / "2026-10-17-cast-chain.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)
sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.netlist_reader import NetlistReader  # noqa: E402
from kicad_services.sch_text import blocks  # noqa: E402

FIELD = "Railroad-Field"
SPCOAST, LIBDIR = cc.SPCOAST, cc.LIBDIR
BASELINE = SPCOAST / "production/pre-head.net"
ASPECT_CASTS = ("Cast-Aspect-CPL", "Cast-Aspect-CL", "Cast-Aspect-Semaphore")
LETTERS = "ABCDE"
IND_DX = 24.13          # the IND pin's connection point sits this far left of the output pins (owner's tidy, 2026-10-18)
BOX_LEFT, BOX_RIGHT = -21.59, -2.54  # one width for every cast, the Mast's width (owner's tidy)
ARROW_IN, ARROW_BASE, ARROW_HALF = 0.889, 0.254, 0.635  # direction arrowheads just inside the body edge (owner, 2026-10-18)
MID = (BOX_LEFT + BOX_RIGHT) / 2
STUB = 7.62             # a label stub hangs this far below a remote IND pin
PIN_FIELD_DX = 5.588    # a hidden Pin.* field sits this far beyond its pin's connection point

# old downstream cast: (new symbol, body label, fixed Style or None, description)
NEW = {
    "Cast-Lamps-RYG": ("Cast-Head-CPL", "CPL\\nlamps", "CPL",
                       "Mast indication to one CPL head's lamps, one wire each: R, Y, G. Head is the head letter: "
                       "Head B beside mast 774N is head 774NB. The aspect is derived, not drawn."),
    "Cast-Encoder-CPL": ("Cast-Head-CPL-Encoded", "CPL 2-bit", "CPL",
                         "Mast indication to one CPL head's two-bit select code; the decoder on the head is field "
                         "hardware. Head is the head letter."),
    "Cast-Lamps-RGB": ("Cast-Head-RGB", "RGB\\nlamps", None,
                       "Mast indication to one head's aspect on one RGB LED, three legs. Head is the head letter; "
                       "Style names the head style the rulebook's table is read for (CL, CPL, LQ, UQ)."),
    "Cast-Color": ("Cast-Head-Color", "color", None,
                   "Mast indication to one head's aspect as one color point, for a pixel or a lamp behind a roundel "
                   "(E71). Head is the head letter; Style as for Cast-Head-RGB."),
    "Cast-Arm": ("Cast-Head-Semaphore", "arm", None,
                 "Mast indication to one semaphore head's arm position; the angles are this cast's settings. "
                 "Head is the head letter; Style is the quadrant (LQ or UQ)."),
}
STANDARD = ("Reference", "Value", "Footprint", "Datasheet", "Description")
PIN_RE = re.compile(r'\(pin (\w+) line\s+\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\s+\(length [\d.]+\)\s+'
                    r'\(name "([^"]*)".*?\(number "([^"]*)"', re.S)


# ---------------------------------------------------------------- library
def _arrow(edge: float, y: float, inward: int, depth=3) -> str:
    """A filled arrowhead at a body edge, apex pointing inward (inward = +1 at the left edge, -1 at the right)."""
    t = "\t" * depth
    apex, base = edge + inward * ARROW_IN, edge + inward * ARROW_BASE
    pts = f"(xy {cc.num(apex)} {cc.num(y)}) (xy {cc.num(base)} {cc.num(y + inward * ARROW_HALF)}) (xy {cc.num(base)} {cc.num(y - inward * ARROW_HALF)}) (xy {cc.num(apex)} {cc.num(y)})"
    return (f"{t}(polyline\n{t}\t(pts\n{t}\t\t{pts}\n{t}\t)\n{t}\t(stroke\n{t}\t\t(width 0)\n{t}\t\t(type solid)\n{t}\t)\n"
            f"{t}\t(fill\n{t}\t\t(type color)\n{t}\t\t(color 132 0 0 1)\n{t}\t)\n{t})")


def shown(prop: str) -> str:
    return prop.replace("(show_name no)", "(show_name yes)", 1)


def head_cast(field_lib: str, old: str) -> str:
    """The one-step symbol built from the old downstream cast: its output pins, an IND input, Head."""
    new, label, fixed, description = NEW[old]
    s, e = cc.top_symbols(field_lib, 1)[old]
    b = field_lib[s:e]
    kinds = {k[4:]: v for k, (v, _, _) in cc.props_in(b, 2).items() if k.startswith("Pin.")}
    pins = PIN_RE.findall(b)
    outs = [(et, float(x), float(y), r, n, no) for et, x, y, r, n, no in pins if n != "ASPECT"]
    (ind_num,) = [no for *_, n, no in pins if n == "ASPECT"]
    table = old == "Cast-Encoder-CPL"
    rows = 3 if fixed is None else 2   # label, Style, Head; the encoder's table sits left of its two rows
    half = max(max(abs(y) for _, _, y, *_ in outs) + 1.27, 1.27 * rows)  # bodies tile at the chip's pin pitch
    top = half - 1.27
    lx = MID if not table else -9.525  # between the table and the pin names
    texts = [cc._text(label, lx, top, 0.762)]
    if table:  # the owner's table, verbatim, inside the body right of the IND pin name
        for ts, te in blocks(b, "text", 3):
            if "Green" in b[ts:te]:
                texts.append("\t\t\t" + re.sub(r"\(at [-\d.]+ [-\d.]+ 0\)", f"(at {cc.num(BOX_LEFT + 3.81)} 0 0)", b[ts:te], count=1))
    props = [cc._prop("Reference", "Cast", f"{cc.num(MID)} {cc.num(half + 0.889)} 0", hide=True, size=0.762),
             cc._prop("Value", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Footprint", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Datasheet", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Description", description, f"0 {cc.num(-half - 1.27)} 0", hide=True, size=1.27, autoplace=True),
             cc._prop("Role", "CAST", f"{cc.num(MID)} {cc.num(half + 1.651)} 0")]
    if fixed:
        props.append(cc._prop("Style", fixed, f"{cc.num(MID)} {cc.num(half + 2.413)} 0"))
    else:
        props.append(shown(cc._prop("Style", "", f"{cc.num(lx)} 0 0", hide=False, size=0.762)))
    props.append(shown(cc._prop("Head", "", f"{cc.num(lx)} {cc.num(-top)} 0", hide=False, size=0.762)))
    for k, (v, _, _) in cc.props_in(b, 2).items():  # the old cast's settings (the semaphore's angles) carry over
        if k not in STANDARD and not k.startswith(("Pin.", "ki_")) and k not in ("Role", "Style"):
            props.append(cc._prop(k, v, f"{cc.num(MID)} {cc.num(-half - 2.54)} 0"))
    props.append(cc._prop("Pin.IND", "indication", f"{cc.num(-IND_DX - PIN_FIELD_DX)} 0 0"))
    for _, x, y, _, n, _ in outs:
        props.append(cc._prop(f"Pin.{cc.re.sub(r'^~\{(.+)\}$', r'\1', n)}", kinds[cc.re.sub(r'^~\{(.+)\}$', r'\1', n)],
                              f"{cc.num(x + PIN_FIELD_DX)} {cc.num(y)} 0"))
    pin_text = [cc._pin("input", -IND_DX, 0, 0, "IND", ind_num)]
    pin_text += [cc._pin(et, x, y, int(float(r)), n, no) for et, x, y, r, n, no in outs]
    arrows = [_arrow(BOX_LEFT, 0, +1)] + [_arrow(BOX_RIGHT, y, -1) for _, _, y, *_ in outs]  # the owner's direction marks
    pin_text += arrows
    unit0 = f'\t\t(symbol "{new}_0_1"\n' + cc._rect(BOX_LEFT, half, BOX_RIGHT, -half) + "\n\t\t)"
    unit1 = f'\t\t(symbol "{new}_1_1"\n' + "\n".join(texts + pin_text) + "\n\t\t)"
    return (f'\t(symbol "{new}"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0.889)\n\t\t)\n'
            f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
            f'\t\t(duplicate_pin_numbers_are_jumpers no)\n' + "\n".join(props) + "\n" + unit0 + "\n" + unit1 +
            "\n\t\t(embedded_fonts no)\n\t)")


def edit_field_library(text: str, report: list[str]) -> tuple[str, dict[str, str]]:
    syms = cc.top_symbols(text, 1)
    new = {NEW[old][0]: head_cast(text, old) for old in NEW}
    edits = []
    for name in list(ASPECT_CASTS) + list(NEW):
        s, e = syms[name]
        edits.append((s - 2, e, ""))
        report.append(f"{FIELD}: retire {name}")
    for name in new:
        if name in syms:
            raise SystemExit(f"{FIELD} already has {name}")
        report.append(f"{FIELD}: add {name}")
    tail = text.rindex("\n)")
    edits.append((tail, tail, "\n" + "\n".join(new.values())))
    return cc.splice(text, edits), new


# ---------------------------------------------------------------- sheet
def instance_shown(lib_id, x, y, ref, description, fields, shown_at, pin_numbers, path) -> str:
    """cc.instance with some fields visible: shown_at = {field: (lib x, lib y)} (library axes, Y up)."""
    at = f"{cc.num(x)} {cc.num(y)} 0"
    props = [cc._prop("Reference", ref, f"{cc.num(x - 2.54)} {cc.num(y - 3.81)} 0", size=0.762),
             cc._prop("Value", "", at, size=1.27, autoplace=True),
             cc._prop("Footprint", "", at, size=1.27, autoplace=True),
             cc._prop("Datasheet", "", at, size=1.27, autoplace=True),
             cc._prop("Description", description, f"{cc.num(x)} {cc.num(y + 6.604)} 0", size=1.27, autoplace=True)]
    for k, v in fields:
        if k in shown_at:
            lx, ly = shown_at[k]
            props.append(shown(cc._prop(k, v, f"{cc.num(x + lx)} {cc.num(y - ly)} 0", hide=False, size=0.762)))
        else:
            props.append(cc._prop(k, v, at))
    pins = "".join(f'\n\t\t(pin "{n}"\n\t\t\t(uuid "{cc.uid()}")\n\t\t)' for n in pin_numbers)
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n'
            f'\t\t(uuid "{cc.uid()}")\n' + "\n".join(props) + pins +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def symbol_shown_at(sym_text: str) -> tuple[dict[str, tuple[float, float]], float]:
    """{shown field: (x, y)} and the IND pin's x from a new library symbol's text."""
    out = {}
    for k, (v, s, e) in cc.props_in(sym_text, 2).items():
        blk = sym_text[s:e]
        if "(hide no)" in blk:
            x, y = re.search(r"\(at ([-\d.]+) ([-\d.]+)", blk).groups()
            out[k] = (float(x), float(y))
    return out


def cached_pin_dx(text: str, lib_id: str, pin: str) -> float:
    """How far left of an instance's origin the cached symbol's pin connects (every unit alike)."""
    (ls, le), = blocks(text, "lib_symbols", 1)
    s, e = cc.top_symbols(text[ls:le], 2)[lib_id]
    for _, x, _, _, n, _ in PIN_RE.findall(text[ls + s:ls + e]):
        if n == pin:
            return -float(x)
    raise SystemExit(f"{lib_id}: no {pin} pin in the sheet cache")


def pairs_from_netlist(model, unit_refs: set[str], down_refs: set[str], mast_refs: set[str]):
    """{(unit ref, unit n): (letter, mast ref, [downstream refs])} from the baseline connectivity."""
    out, mast_of = {}, {}
    for net in model.nets:
        nodes = [(n.reference, n.pin) for n in net.nodes]
        for ref, pin in nodes:
            if ref in unit_refs:
                n = (int(pin) + 1) // 2
                if int(pin) % 2 == 0:  # ASPECT
                    ds = [r for r, _ in nodes if r in down_refs]
                    out[(ref, n)] = ds
                else:  # IND
                    ms = [r for r, _ in nodes if r in mast_refs]
                    if len(ms) != 1:
                        raise SystemExit(f"{ref} unit {n}: IND net has {len(ms)} masts")
                    mast_of[(ref, n)] = ms[0]
    return {k: (LETTERS[k[1] - 1], mast_of[k], ds) for k, ds in out.items()}


def rewrite_sheet(text: str, field_lib: str, new_syms: dict[str, str], model, report: list[str], sheet: str) -> str:
    units, downs, masts = {}, {}, {}
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        m = re.search(r'\n\t\t\(lib_id "Railroad-Field:([^"]+)"', b)
        if not m:
            continue
        p = cc.props_in(b, 2)
        x, y, rot = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)", b).groups()
        unit = int(re.search(r"\n\t\t\(unit (\d+)\)", b).group(1))
        rec = dict(s=s, e=e, x=float(x), y=float(y), rot=rot, ref=p["Reference"][0], style=p.get("Style", ("",))[0],
                   path=re.search(r'\(path "([^"]+)"', b).group(1), part=m.group(1), value=p["Value"][0])
        if m.group(1) in ASPECT_CASTS:
            units[(rec["ref"], unit)] = rec
        elif m.group(1) in NEW:
            downs[rec["ref"]] = rec
        elif m.group(1) == "Mast":
            masts[rec["ref"]] = rec
    if not units:
        return text
    for rec in list(units.values()) + list(downs.values()):
        if rec["rot"] != "0" or "(mirror" in text[rec["s"]:rec["e"]]:
            raise SystemExit(f"{sheet}: {rec['ref']} is rotated or mirrored; not handled")
    pairs = pairs_from_netlist(model, {r for r, _ in units}, set(downs), set(masts))
    if set(pairs) != set(units):
        raise SystemExit(f"{sheet}: units on the sheet {sorted(units)} differ from the netlist {sorted(pairs)}")
    claimed = [d for _, _, ds in pairs.values() for d in ds]
    if sorted(claimed) != sorted(downs):
        raise SystemExit(f"{sheet}: downstream casts {sorted(downs)} vs paired {sorted(claimed)}")

    # points whose wires, labels and junctions go: every unit's ASPECT pin and every old ASPECT input
    gone = [(u["x"], u["y"]) for u in units.values()]
    gone += [(d["x"] - cached_pin_dx(text, f"{FIELD}:{d['part']}", "ASPECT"), d["y"]) for d in downs.values()]

    def at_gone(x, y):
        return any(abs(x - gx) < 0.01 and abs(y - gy) < 0.01 for gx, gy in gone)

    edits = [(u["s"] - 2, u["e"], "") for u in units.values()]
    label_pts = []
    for s, e in blocks(text, "wire", 1):
        pts = [(float(a), float(b)) for a, b in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", text[s:e])]
        if any(at_gone(*p) for p in pts):
            edits.append((s - 2, e, ""))
            label_pts += pts
            report.append(f"{sheet}: drop wire {pts}")
    for head in ("label", "junction"):
        for s, e in blocks(text, head, 1):
            x, y = map(float, re.search(r"\(at ([-\d.]+) ([-\d.]+)", text[s:e]).groups())
            if at_gone(x, y) or any(abs(x - a) < 0.01 and abs(y - b) < 0.01 for a, b in label_pts):
                edits.append((s - 2, e, ""))
                report.append(f"{sheet}: drop {head} at ({cc.num(x)}, {cc.num(y)})")

    added, used, labelled = [], set(), set()
    for (uref, n), (letter, mref, ds) in sorted(pairs.items()):
        u, mast = units[(uref, n)], masts[mref]["value"]
        tap = (u["x"] - cached_pin_dx(text, f"{FIELD}:{u['part']}", "IND"), u["y"])  # the old unit's IND point: the bus stub ends here
        straight = False
        for dref in sorted(ds, key=lambda r: (abs(downs[r]["y"] - u["y"]), downs[r]["x"])):
            d = downs[dref]
            new, _, fixed, _ = NEW[d["part"]]
            sym = new_syms[new]
            desc, fields, numbers = cc.lib_fields(field_lib, new)
            own = {k: v for k, (v, _, _) in cc.props_in(text[d["s"]:d["e"]], 2).items()}  # the instance's settings
            fields = [(k, {"Head": letter, "Style": fixed or u["style"]}.get(k, own.get(k, v) if not k.startswith("Pin.") else v))
                      for k, v in fields]
            lib_id = f"{FIELD}:{new}"
            added_inst = instance_shown(lib_id, d["x"], d["y"], dref, desc, fields, symbol_shown_at(sym), numbers, d["path"])
            edits.append((d["s"], d["e"], added_inst.lstrip("\t")))
            used.add(new)
            ind = (d["x"] - IND_DX, d["y"])
            if abs(ind[1] - tap[1]) < 0.01 and ind[0] > tap[0] + 0.01 and not straight:
                added.append(cc.wire(*tap, *ind))
                straight = True
                how = "wire from the tap"
            else:
                name = f"{mast}_IND"
                if mast not in labelled:
                    if not straight:
                        added.append(cc.wire(*tap, tap[0] + 5.08, tap[1]))
                    added.append(cc.label(name, tap[0] + 2.54, tap[1]))
                    labelled.add(mast)
                added.append(cc.wire(*ind, ind[0], ind[1] + STUB))
                added.append(cc.label(name, ind[0], ind[1] + STUB))
                how = f"label {name}"
            report.append(f"{sheet}: {uref} unit {letter} + {dref} ({d['part']}) -> {new} {dref} Head={letter} "
                          f"Style={fields_dict(fields)['Style']!r} at {cc.num(d['x'])} {cc.num(d['y'])}; {how}; head {mast}{letter}")
    first = min(s for s, _, _ in edits)
    edits.append((first, first, "\n" + "\n".join(added)))
    text = cc.splice(text, edits)
    return cc.update_cache(text, {f"{FIELD}:{n}": cc.cached(FIELD, field_lib, n) for n in sorted(used)},
                           [f"{FIELD}:{n}" for n in list(ASPECT_CASTS) + list(NEW)])


def fields_dict(fields):
    return dict(fields)


def edit_project(text: str, report: list[str]) -> str:
    for key in ("missing_input_pin", "missing_unit"):
        old = f'"{key}": "ignore"'
        if old in text:
            text = text.replace(old, f'"{key}": "warning"')
            report.append(f"SPCoast.kicad_pro: {key} back to warning")
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(SPCOAST.glob("~*.lck")):
        print("KiCad holds a lock on the project; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    field_path = LIBDIR / f"{FIELD}.kicad_sym"
    field_lib, new_syms = edit_field_library(field_path.read_text(), report)
    model = NetlistReader().read(BASELINE)
    sheets = {}
    for name in ("Sargent", "GilroyCalTrain"):
        p = SPCOAST / f"{name}.kicad_sch"
        sheets[p] = rewrite_sheet(p.read_text(), field_lib, new_syms, model, report, name)
    pro = SPCOAST / "SPCoast.kicad_pro"
    pro_text = edit_project(pro.read_text(), report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    field_path.write_text(field_lib)
    for p, t in sheets.items():
        p.write_text(t)
    pro.write_text(pro_text)
    print(f"wrote {field_path.name}, {', '.join(p.name for p in sheets)}, {pro.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
