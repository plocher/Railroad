#!/usr/bin/env python3
"""One-off, 2026-10-17: make the head casts explicit symbols (no magic casts).

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python \
        SPCoast/edits/2026-10-17-cast-chain.py [--dry-run]

Decided 2026-10-17: a bundled head device (Device-Head-CPL-Encoder = indication table + CPL
style + two-bit encoder) hides casts the drawing should state. The chain becomes

    [Head-CPL 836NA] -aspect- [Cast-Encoder-CPL] -2 binary- [chip pins]

where the anchor (Role DEVICE, Value = the head, one ASPECT output) joins the appliance by
Value as every device does, and each cast (Role CAST, no identity) takes one ASPECT input and
produces typed outputs. Drivers are generic sinks; a JMRI driver's Address is derived from the
served appliance unless written.

What this script does, by text edits that keep every untouched byte:
- Railroad-Field: retires the six Device-Head-* symbols; adds Head-CPL, Head-CL, Head-Semaphore,
  Mast and the casts Cast-Lamps-RYG, Cast-Encoder-CPL, Cast-Lamps-RGB, Cast-Color, Cast-Arm.
- Railroad-HardwareIO: the four Driver-JMRI-* symbols lose topic/States and the Address
  template, and gain a Pin.* per pin; adds Driver-JMRI-SignalMast (one `indication` input);
  Driver-GPIO-Pixel's pin kind becomes `color`.
- Sargent and GilroyCalTrain: every placed head device becomes anchor + cast(s). Casts keep the
  old pin geometry so the chip pins they touch stay touched; the anchor's ASPECT output touches
  the cast's input. 836SB (semaphore with RGB lamps, four units) gets two casts joined by a
  local label, and three short wires to the chip pins whose order differs from the cast's.
- GilroyInterchange: the six JMRI driver instances lose their copied Value/Address/topic/States.
Sheet lib_symbols caches are updated. KiCad must be closed (no ~*.lck).
Follow with 2026-10-16-sync-library-fields.py, kicad-cli netlist + ERC, and the gate.
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks, end_of  # noqa: E402

RAILROAD = Path.home() / "Dropbox/KiCad/Railroad"
SPCOAST = RAILROAD / "SPCoast"
LIBDIR = RAILROAD / "symbols"
FIELD, HWIO = "Railroad-Field", "Railroad-HardwareIO"
OLD_HEADS = ("Device-Head-CPL", "Device-Head-CPL-Encoder", "Device-Head-CL", "Device-Head-CL-Pixel",
             "Device-Head-Semaphore", "Device-Head-Semaphore-RGB")
JMRI = ("Driver-JMRI-Turnout", "Driver-JMRI-Turnout-Feedback", "Driver-JMRI-Sensor", "Driver-JMRI-Sensor-Feedback")


def num(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------- library symbol text
def _prop(name, value, at="0 0 0", hide=True, size=0.635, autoplace=False, justify=None, depth=2):
    t = "\t" * depth
    j = f"\n{t}\t\t{justify}" if justify else ""
    return (f'{t}(property "{name}" "{value}"\n{t}\t(at {at})\n{t}\t(show_name no)\n'
            f'{t}\t(do_not_autoplace {"no" if autoplace else "yes"})\n{t}\t(hide {"yes" if hide else "no"})\n'
            f'{t}\t(effects\n{t}\t\t(font\n{t}\t\t\t(size {size} {size})\n{t}\t\t){j}\n{t}\t)\n{t})')


def _pin(etype, x, y, rot, name, number, depth=3):
    t = "\t" * depth
    return (f'{t}(pin {etype} line\n{t}\t(at {num(x)} {num(y)} {rot})\n{t}\t(length 2.54)\n'
            f'{t}\t(name "{name}"\n{t}\t\t(effects\n{t}\t\t\t(font\n{t}\t\t\t\t(size 1.016 1.016)\n{t}\t\t\t)\n{t}\t\t)\n{t}\t)\n'
            f'{t}\t(number "{number}"\n{t}\t\t(effects\n{t}\t\t\t(font\n{t}\t\t\t\t(size 0.381 0.381)\n{t}\t\t\t)\n{t}\t\t)\n{t}\t)\n{t})')


def _rect(x1, y1, x2, y2, depth=3):
    t = "\t" * depth
    return (f'{t}(rectangle\n{t}\t(start {num(x1)} {num(y1)})\n{t}\t(end {num(x2)} {num(y2)})\n'
            f'{t}\t(stroke\n{t}\t\t(width 0)\n{t}\t\t(type default)\n{t}\t)\n{t}\t(fill\n{t}\t\t(type none)\n{t}\t)\n{t})')


def _text(s, x, y, size=0.762, justify=None, depth=3):
    t = "\t" * depth
    j = f"\n{t}\t\t(justify {justify})" if justify else ""
    return (f'{t}(text "{s}"\n{t}\t(at {num(x)} {num(y)} 0)\n{t}\t(effects\n{t}\t\t(font\n{t}\t\t\t(size {size} {size})\n'
            f'{t}\t\t){j}\n{t}\t)\n{t})')


def symbol(name, reference, description, fields, body, pins, texts, ref_at="0 2.54 0"):
    """A top-level library symbol (depth 1). fields: [(name, value)] after the standard five."""
    props = [_prop("Reference", reference, ref_at, hide=True, size=0.762),
             _prop("Value", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             _prop("Footprint", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             _prop("Datasheet", "", "0 0 0", hide=True, size=1.27, autoplace=True),
             _prop("Description", description, "0 -5.08 0", hide=True, size=1.27, autoplace=True)]
    props += [_prop(k, v, "0 0 0") for k, v in fields]
    unit0 = f'\t\t(symbol "{name}_0_1"\n' + "\n".join(body) + "\n\t\t)"
    unit1 = f'\t\t(symbol "{name}_1_1"\n' + "\n".join(texts + pins) + "\n\t\t)"
    return (f'\t(symbol "{name}"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0.889)\n\t\t)\n'
            f'\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
            f'\t\t(duplicate_pin_numbers_are_jumpers no)\n' + "\n".join(props) + "\n" + unit0 + "\n" + unit1 +
            "\n\t\t(embedded_fonts no)\n\t)")


def anchor(name, appliance, style, description, pin_name, kind, label, reference):
    fields = [("Role", "DEVICE"), ("Appliance", appliance)] + ([("Style", style)] if style else []) + [(f"Pin.{pin_name}", kind)]
    return symbol(name, reference, description, fields, [_rect(-21.59, 1.27, -2.54, -1.27)],
                  [_pin("output", 0, 0, 180, pin_name, "1")], [_text(f"{label} ${{VALUE}}", -20.955, 0, 1.016, "left")])


def cast(name, description, outputs, label, half, settings=(), extra_texts=()):
    """outputs: [(y, pin name, number, kind)]; the ASPECT input is the last number."""
    fields = [("Role", "CAST"), ("Pin.ASPECT", "aspect")]
    fields += [(f"Pin.{re.sub(r'^~\{(.+)\}$', r'\1', n)}", k) for _, n, _, k in outputs]
    fields += [(s, "") for s in settings]
    pins = [_pin("input", 0, y, 180, n, no) for y, n, no, _ in outputs]
    pins.append(_pin("input", -15.24, 0, 0, "ASPECT", str(len(outputs) + 1)))
    texts = [_text(label, -7.62, half + 1.524, 0.762)] + list(extra_texts)  # above the body, clear of the pin names
    return symbol(name, "Cast", description, fields, [_rect(-12.7, half, -2.54, -half)], pins, texts)


NEW_FIELD = {
    "Head-CPL": anchor("Head-CPL", "head", "CPL",
                       "Colour-position-light head. Value = the head (836NA). ASPECT is this head's aspect by the rulebook's indication table; wire it to a cast.",
                       "ASPECT", "aspect", "HEAD", "DevHead"),
    "Head-CL": anchor("Head-CL", "head", "CL",
                      "Colour-light head. Value = the head. ASPECT is this head's aspect by the rulebook's indication table; wire it to a cast.",
                      "ASPECT", "aspect", "HEAD", "DevHead"),
    "Head-Semaphore": anchor("Head-Semaphore", "head", "LQ, UQ",
                             "Semaphore head, lower or upper quadrant by the plant head's Style. Value = the head. ASPECT feeds Cast-Arm and a lamp cast.",
                             "ASPECT", "aspect", "HEAD", "DevHead"),
    "Mast": anchor("Mast", "mast", "",
                   "A mast as one device: IND is the mast's indication (the rule name), for drivers that take a whole mast, e.g. Driver-JMRI-SignalMast. Value = the mast (788).",
                   "IND", "indication", "MAST", "DevMast"),
    "Cast-Lamps-RYG": cast("Cast-Lamps-RYG", "Aspect to three lamps, one wire each: R, Y, G. Brightness and fade are settings when a lamp lands on a level-out pin.",
                           [(2.54, "~{G}", "1", "binary"), (0, "~{Y}", "2", "binary"), (-2.54, "~{R}", "3", "binary")],
                           "CPL\\nlamps", 3.81),
    "Cast-Encoder-CPL": cast("Cast-Encoder-CPL", "Aspect to a two-bit select code; the decoder on the head is field hardware.",
                             [(1.27, "S0", "1", "binary"), (-1.27, "S1", "2", "binary")], "CPL\\n2-bit", 2.54,
                             extra_texts=[_text("0 0 Green\\n0 1 Yellow\\n1 0 Red\\n1 1 Dark", -7.62, -5.715, 0.635)]),
    "Cast-Lamps-RGB": cast("Cast-Lamps-RGB", "Aspect to one RGB LED, three legs: red is R, yellow is R plus G, green is G, lunar is all three (E71).",
                           [(-2.54, "~{R}", "1", "binary"), (0, "~{G}", "2", "binary"), (2.54, "~{B}", "3", "binary")],
                           "RGB\\nlamps", 3.81),
    "Cast-Color": cast("Cast-Color", "Aspect to one color point, for a pixel or a lamp behind a roundel (E71).",
                       [(0, "RGB", "1", "color")], "color", 1.27),
    "Cast-Arm": cast("Cast-Arm", "Aspect to a semaphore arm position; the angles are this cast's settings.",
                     [(0, "ARM", "1", "position")], "arm", 1.27, settings=("stop_deg", "approach_deg", "clear_deg")),
}

NEW_HWIO = {
    "Driver-JMRI-SignalMast": symbol(
        "Driver-JMRI-SignalMast", "JMRI_MQTT",
        "JMRI MQTT signal mast: sends the mast's indication as JMRI's aspect name, with Lit and Held from the unit. Address = the JMRI mast name; empty = the mast this driver serves.",
        [("Role", "IODRIVER"), ("IC", "MQTT"), ("Address", ""), ("Pin.IND", "indication")],
        [_rect(2.54, 1.27, 21.59, -1.27)], [_pin("input", 0, 0, 0, "IND", "1")],
        [_text("MQTT mast ${ADDRESS}", 8.255, 0, 0.762, "left")], ref_at="1.27 2.54 0"),
}

JMRI_EDITS = {  # name: (pins to declare, text, description)
    "Driver-JMRI-Turnout": (["M"], "MQTT turnout ${ADDRESS}",
                            "JMRI MQTT turnout command (CLOSED/THROWN). Address = the JMRI turnout name; empty = the switch this driver serves."),
    "Driver-JMRI-Turnout-Feedback": (["N", "R"], "MQTT turnout ${ADDRESS}",
                                     "JMRI MQTT turnout feedback (CLOSED/THROWN/INCONSISTENT/UNKNOWN) as N and R. Address as Driver-JMRI-Turnout."),
    "Driver-JMRI-Sensor": (["S"], "MQTT sensor ${ADDRESS}",
                           "JMRI MQTT sensor published by the unit (ACTIVE/INACTIVE). Address = the JMRI sensor name; empty = the circuit this driver serves."),
    "Driver-JMRI-Sensor-Feedback": (["S"], "MQTT sensor ${ADDRESS}",
                                    "JMRI MQTT sensor read by the unit (ACTIVE/INACTIVE). Address as Driver-JMRI-Sensor."),
}


# ---------------------------------------------------------------- text surgery helpers
def top_symbols(text: str, depth: int) -> dict[str, tuple[int, int]]:
    out = {}
    for s, e in blocks(text, "symbol", depth):
        out[re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', text[s:e]).group(1)] = (s, e)
    return out


def props_in(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def set_prop(block: str, name: str, value: str, depth: int) -> str:
    v, s, e = props_in(block, depth)[name]
    m = re.match(r'\(property "(?:[^"\\]|\\.)*" "', block[s:])
    vs = s + m.end()
    ve = block.index('"', vs)
    while block[ve - 1] == "\\":
        ve = block.index('"', ve + 1)
    return block[:vs] + value + block[ve:]


def drop_prop(block: str, name: str, depth: int) -> str:
    p = props_in(block, depth)
    if name not in p:
        return block
    _, s, e = p[name]
    return block[:s - depth - 1] + block[e:]  # the preceding "\n" + tabs go too


def rename_prop(block: str, old: str, new: str, depth: int) -> str:
    _, s, e = props_in(block, depth)[old]
    return block[:s] + block[s:e].replace(f'(property "{old}"', f'(property "{new}"', 1) + block[e:]


def dup_prop(block: str, name: str, new: str, depth: int) -> str:
    _, s, e = props_in(block, depth)[name]
    copy = block[s:e].replace(f'(property "{name}"', f'(property "{new}"', 1)
    return block[:e] + "\n" + "\t" * depth + copy + block[e:]


def splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    out, pos = [], 0
    for s, e, new in sorted(edits):
        assert s >= pos, "overlapping edits"
        out += [text[pos:s], new]
        pos = e
    return "".join(out) + text[pos:]


# ---------------------------------------------------------------- libraries
def edit_field_library(text: str, report: list[str]) -> str:
    syms = top_symbols(text, 1)
    edits = []
    for name in OLD_HEADS:
        if name in syms:
            s, e = syms[name]
            edits.append((s - 2, e, ""))
            report.append(f"{FIELD}: retire {name}")
    for name, body in NEW_FIELD.items():
        if name in syms:
            raise SystemExit(f"{FIELD} already has {name}")
        report.append(f"{FIELD}: add {name}")
    tail = text.rindex("\n)")
    edits.append((tail, tail, "\n" + "\n".join(NEW_FIELD.values())))
    return splice(text, edits)


def edit_jmri_symbol(block: str, name: str) -> str:
    pins, label, desc = JMRI_EDITS[name]
    b = set_prop(block, "Description", desc, 2)
    b = set_prop(b, "Address", "", 2)
    for junk in ("topic", "Topic", "States"):
        b = drop_prop(b, junk, 2)
    b = rename_prop(b, "Pin.D", f"Pin.{pins[0]}", 2)
    for extra in pins[1:]:
        b = dup_prop(b, f"Pin.{pins[0]}", f"Pin.{extra}", 2)
    b = re.sub(r'\(text "MQTT \$\{Topic\}/\$\{VALUE\}"', f'(text "{label}"', b)
    return b


def edit_hwio_library(text: str, report: list[str]) -> str:
    syms = top_symbols(text, 1)
    edits = []
    for name in JMRI:
        s, e = syms[name]
        edits.append((s, e, edit_jmri_symbol(text[s:e], name)))
        report.append(f"{HWIO}: {name}: Pin.* per pin, Address empty, topic/States dropped")
    s, e = syms["Driver-GPIO-Pixel"]
    edits.append((s, e, set_prop(text[s:e], "Pin.D", "color", 2)))
    report.append(f"{HWIO}: Driver-GPIO-Pixel: Pin.D pixel -> color")
    for name in NEW_HWIO:
        if name in syms:
            raise SystemExit(f"{HWIO} already has {name}")
        report.append(f"{HWIO}: add {name}")
    tail = text.rindex("\n)")
    edits.append((tail, tail, "\n" + "\n".join(NEW_HWIO.values())))
    return splice(text, edits)


# ---------------------------------------------------------------- sheets
def cached(lib: str, lib_text: str, name: str) -> str:
    """The sheet lib_symbols form of a library symbol: prefixed name, one more tab."""
    s, e = top_symbols(lib_text, 1)[name]
    b = lib_text[s:e].replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    return "\t\t" + b.replace("\n", "\n\t")


def update_cache(text: str, add: dict[str, str], remove: list[str]) -> str:
    (ls, le), = blocks(text, "lib_symbols", 1)
    block = text[ls:le]
    have = top_symbols(block, 2)
    edits = [(s - 3, e, "") for n, (s, e) in have.items() if n in remove]
    new = "".join("\n" + body for n, body in add.items() if n not in have or n in remove)
    edits.append((len(block) - 2, len(block) - 2, new))  # before the closing "\t)"
    return text[:ls] + splice(block, edits) + text[le:]


def instance(lib_id: str, x: float, y: float, ref: str, value: str, description: str,
             fields: list[tuple[str, str]], pin_numbers: list[str], path: str) -> str:
    at = f"{num(x)} {num(y)} 0"
    props = [_prop("Reference", ref, f"{num(x - 2.54)} {num(y - 3.81)} 0", size=0.762),
             _prop("Value", value, at, size=1.27, autoplace=True),
             _prop("Footprint", "", at, size=1.27, autoplace=True),
             _prop("Datasheet", "", at, size=1.27, autoplace=True),
             _prop("Description", description, f"{num(x)} {num(y + 6.604)} 0", size=1.27, autoplace=True)]
    props += [_prop(k, v, at) for k, v in fields]
    pins = "".join(f'\n\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for n in pin_numbers)
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at})\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n'
            f'\t\t(uuid "{uid()}")\n' + "\n".join(props) + pins +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


def wire(x1, y1, x2, y2) -> str:
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {num(x1)} {num(y1)}) (xy {num(x2)} {num(y2)})\n\t\t)\n'
            f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)')


def label(name, x, y) -> str:
    return (f'\t(label "{name}"\n\t\t(at {num(x)} {num(y)} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n'
            f'\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)')


def lib_fields(lib_text: str, name: str) -> tuple[str, list[tuple[str, str]], list[str]]:
    """(description, [(owned field, value)], [pin numbers]) of a library symbol."""
    s, e = top_symbols(lib_text, 1)[name]
    b = lib_text[s:e]
    p = props_in(b, 2)
    fields = [(k, v) for k, (v, _, _) in p.items() if k in ("Role", "Appliance", "Style") or k.startswith("Pin.")
              or (k not in ("Reference", "Value", "Footprint", "Datasheet", "Description") and not k.startswith("ki_"))]
    numbers = re.findall(r'\(number "([^"]*)"', b)
    return p["Description"][0], fields, numbers


CHAIN = {  # old part: (anchor, cast)
    "Device-Head-CPL": ("Head-CPL", "Cast-Lamps-RYG"),
    "Device-Head-CPL-Encoder": ("Head-CPL", "Cast-Encoder-CPL"),
    "Device-Head-CL": ("Head-CL", "Cast-Lamps-RGB"),
}
ASPECT_DX = 15.24  # the cast's ASPECT input sits this far left of its output pins


class Counter:
    def __init__(self, start: int):
        self.n = start

    def next(self, prefix: str) -> str:
        self.n += 1
        return f"{prefix}{self.n}"


def rewrite_heads(text: str, field_lib: str, casts: Counter, report: list[str], sheet: str) -> str:
    old = {}  # ref -> list of (s, e, part, value, x, y, unit, path)
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        m = re.search(r'\n\t\t\(lib_id "([^:"]+):([^"]+)"', b)
        if not m or m.group(2) not in OLD_HEADS:
            continue
        p = props_in(b, 2)
        x, y, _ = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)", b).groups()
        unit = int(re.search(r"\n\t\t\(unit (\d+)\)", b).group(1))
        path = re.search(r'\(path "([^"]+)"', b).group(1)
        old.setdefault(p["Reference"][0], []).append((s, e, m.group(2), p["Value"][0], float(x), float(y), unit, path))
    if not old:
        return text
    edits, added = [], []
    used = set()
    for ref, inst in old.items():
        for s, e, *_ in inst:
            edits.append((s - 2, e, ""))
        part, value, path = inst[0][2], inst[0][3], inst[0][7]
        if part in CHAIN:
            (s, e, _, _, x, y, _, _), = inst
            a_name, c_name = CHAIN[part]
            d, f, n = lib_fields(field_lib, c_name)
            c_ref = casts.next("Cast")
            added.append(instance(f"{FIELD}:{c_name}", x, y, c_ref, "", d, f, n, path))
            d, f, n = lib_fields(field_lib, a_name)
            added.append(instance(f"{FIELD}:{a_name}", x - ASPECT_DX, y, ref, value, d, f, n, path))
            used.update((a_name, c_name))
            report.append(f"{sheet}: {ref} {value} {part} -> {a_name} + {c_name} ({c_ref})")
        elif part == "Device-Head-Semaphore-RGB":
            # Library Y points up, sheet Y points down: a pin at library (0, +1.27) sits 1.27 above the
            # instance origin on the sheet, i.e. at y - 1.27.
            by_unit = {u: (x, y) for _, _, _, _, x, y, u, _ in inst}
            ax, ay = by_unit[1]
            arm = (ax, ay - 1.27)  # unit 1 ARM pin, library (0, 1.27)
            lx, ly = by_unit[2]
            chip = {"G": (lx, ly + 1.27), "B": (lx, ly + 3.81), "R": (lx, ly + 6.35)}  # units 2, 3, 4
            cx, cy = lx - 12.7, chip["B"][1]  # lamp cast: library R (0,-2.54), G (0,0), B (0,+2.54)
            pins = {"R": (cx, cy + 2.54), "G": (cx, cy), "B": (cx, cy - 2.54)}
            c1 = casts.next("Cast")
            d, f, n = lib_fields(field_lib, "Cast-Lamps-RGB")
            added.append(instance(f"{FIELD}:Cast-Lamps-RGB", cx, cy, c1, "", d, f, n, path))
            c2 = casts.next("Cast")
            d, f, n = lib_fields(field_lib, "Cast-Arm")
            added.append(instance(f"{FIELD}:Cast-Arm", arm[0], arm[1], c2, "", d, f, n, path))
            d, f, n = lib_fields(field_lib, "Head-Semaphore")
            added.append(instance(f"{FIELD}:Head-Semaphore", cx - ASPECT_DX, cy, ref, value, d, f, n, path))
            for leg in "RGB":
                added.append(wire(*pins[leg], *chip[leg]))
            net = f"{value}_ASPECT"
            added.append(wire(cx - ASPECT_DX, cy, cx - ASPECT_DX, cy + 7.62))
            added.append(label(net, cx - ASPECT_DX, cy + 7.62))
            added.append(wire(arm[0] - ASPECT_DX, arm[1], arm[0] - ASPECT_DX, arm[1] + 7.62))
            added.append(label(net, arm[0] - ASPECT_DX, arm[1] + 7.62))
            used.update(("Head-Semaphore", "Cast-Lamps-RGB", "Cast-Arm"))
            report.append(f"{sheet}: {ref} {value} {part} (4 units) -> Head-Semaphore + Cast-Lamps-RGB ({c1}) + "
                          f"Cast-Arm ({c2}); 3 wires to the chip pins; label {net}")
        else:
            raise SystemExit(f"{sheet}: no chain for {part}")
    first = min(s for s, _, _ in edits)
    edits.append((first, first, "\n" + "\n".join(added)))
    text = splice(text, edits)
    return update_cache(text, {f"{FIELD}:{n}": cached(FIELD, field_lib, n) for n in sorted(used)},
                        [f"{FIELD}:{n}" for n in OLD_HEADS])


def rewrite_jmri(text: str, hwio_lib: str, report: list[str], sheet: str) -> str:
    edits, used = [], set()
    taken = {int(m) for m in re.findall(r'\(property "Reference" "JMRI_MQTT(\d+)"', text)}
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        m = re.search(r'\n\t\t\(lib_id "Railroad-HardwareIO:(Driver-JMRI-[^"]+)"', b)
        if not m:
            continue
        name = m.group(1)
        used.add(name)
        nb = b
        if props_in(nb, 2)["Reference"][0] == "JMRI_MQTT":  # placed but never annotated
            n = next(i for i in range(1, 999) if i not in taken)
            taken.add(n)
            nb = set_prop(nb, "Reference", f"JMRI_MQTT{n}", 2).replace('(reference "JMRI_MQTT")', f'(reference "JMRI_MQTT{n}")')
            report.append(f"{sheet}: annotated JMRI_MQTT -> JMRI_MQTT{n}")
        nb = set_prop(nb, "Value", "", 2)
        if "Address" in props_in(nb, 2):
            nb = set_prop(nb, "Address", "", 2)
        for junk in ("topic", "Topic", "States", "Pin.D"):
            nb = drop_prop(nb, junk, 2)
        ref = props_in(b, 2)["Reference"][0]
        report.append(f"{sheet}: {ref} {name}: Value {props_in(b, 2)['Value'][0]!r} -> '' (derived); Address, topic, States dropped")
        edits.append((s, e, nb))
    if not edits:
        return text
    text = splice(text, edits)
    return update_cache(text, {f"{HWIO}:{n}": cached(HWIO, hwio_lib, n) for n in sorted(used)},
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
    casts = Counter(0)
    sheets = {}
    for name in ("Sargent", "GilroyCalTrain"):
        p = SPCOAST / f"{name}.kicad_sch"
        sheets[p] = rewrite_heads(p.read_text(), field_lib, casts, report, name)
    p = SPCOAST / "GilroyInterchange.kicad_sch"
    sheets[p] = rewrite_jmri(p.read_text(), hwio_lib, report, "GilroyInterchange")
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
