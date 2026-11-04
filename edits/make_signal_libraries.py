"""Generate the signal symbol libraries under the supply/demand shape (worklist of 2026-11-03).

Reads `symbols/Railroad-Trackplan.kicad_sym` and `symbols/Railroad-Field.kicad_sym` and writes
`symbols/Railroad-Trackplan-Signals.kicad_sym` (the masts: demand, `Indications`) and
`symbols/Railroad-Field-Signals.kicad_sym` (the head devices: supply, Style = model, pins = wiring).
Every target symbol is a clone of a named source symbol's whole block, renamed with its unit
sub-symbols, its properties rewritten to exactly the worklist's set, its pins rewritten to exactly
the worklist's set with the source's electrical types and overbar names, and one `Pin.<name>`
property per function pin. Hidden properties keep the shape KiCad writes, copied from a hidden
property of the same symbol. The existing libraries are never written.

Trackplan masts lose their head pins (H, H1, H2). The line each pin drew becomes a polyline, so the
picture is unchanged, and one head glyph (a circle) per head is added beyond the crossbar: one for
single and dwarf, two for double, three for triple; the Stop Sign's one glyph is filled red.

Run from the Railroad repo with the Subdivision venv:

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python edits/make_signal_libraries.py

Deterministic: a second run writes identical files. The worklist is
FieldUnit-Subdivision/docs/review/signal-symbols-worklist.md.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBDIVISION = Path(os.environ.get("FIELDUNIT_SUBDIVISION", Path.home() / "Dropbox/workspace/FieldUnit-Subdivision"))
sys.path.insert(0, str(SUBDIVISION / "tools"))
from kicad_services.sch_text import blocks, replace_spans  # noqa: E402

SYMBOLS = ROOT / "symbols"

# ---------------------------------------------------------------------------------------------
# The worklist. Properties are in the order KiCad writes them after the five standard ones.
# pins: [(name as drawn, Pin.<base> vocabulary word)]; a mast's SIGNAL pin is passive and carries no Pin.*.

TRACKPLAN = [
    # (target, source, style, kind, indications, description, heads)
    ("Signal Mast Single CONTROLLED", "Signal Mast Single CONTROLLED", "single", "CONTROLLED", "",
     "Interlocking signal, one head drawn. Indications: the rulebook names this mast must show, comma-separated.", 1),
    ("Signal Mast Single ABSOLUTE", "Signal Mast Single ABSOLUTE", "single", "ABSOLUTE", "",
     "Block signal, Stop and Hold, one head drawn.", 1),
    ("Signal Mast Single PERMISSIVE", "Signal Mast Single PERMISSIVE", "single", "PERMISSIVE", "",
     "Block signal with number plate, one head drawn.", 1),
    ("Signal Mast Double CONTROLLED", "Signal Mast Double CONTROLLED", "double", "CONTROLLED", "",
     "Two heads drawn; the head count is picture, the devices decide.", 2),
    ("Signal Mast Triple CONTROLLED", "Signal Mast Double CONTROLLED", "triple", "CONTROLLED", "",
     "Three heads drawn.", 3),
    ("Signal Mast Dwarf CONTROLLED", "Signal Mast Dwarf CONTROLLED", "dwarf", "CONTROLLED", "",
     "Dwarf; Style dwarf is a model fact.", 1),
    ("Stop Sign", "Signal Mast Single ABSOLUTE", "stop_sign", "ABSOLUTE", "Stop",
     "A fixed Stop: painted post or one red lamp. The only form with a fixed demand.", 1),
]

FIELD = [
    # (target, source, style, settings [(field, value)], pins [(name, word)], description, text relabels)
    ("Device-Head-TypeD", "Device-Head-CPL", "TypeD", [],
     [("IND", "indication"), ("~{R}", "binary"), ("~{Y}", "binary"), ("~{G}", "binary")],
     "GRS Type D, three lamps, one wire each. Name = mast + head letter (784A). Was Device-Head-CPL.",
     {"CPL": "TypeD"}),
    ("Device-Head-TypeD-Encoded", "Device-Head-CPL-Encoded", "TypeD", [],
     [("IND", "indication"), ("S0", "binary"), ("S1", "binary")],
     "Type D behind a two-bit decoder on the head. Was -CPL-Encoded.",
     {"CPL 2-bit": "TypeD 2-bit"}),
    ("Device-Head-TypeD-Pixel", "Device-Head-CPL-Pixel", "TypeD", [("Address", "")],
     [("IND", "indication"), ("RGB", "color")],
     "Type D as three points on a pixel bus. Was -CPL-Pixel.",
     {"CPL-pixel": "TypeD-pixel"}),
    ("Device-Head-SA-RGB", "Device-Head-CL-RGB", "SA", [],
     [("IND", "indication"), ("~{R}", "binary"), ("~{G}", "binary"), ("~{B}", "binary")],
     "GRS SA searchlight as one RGB LED, three legs. Was -CL-RGB.", {}),
    ("Device-Head-SA-Pixel", "Device-Head-CL-Pixel", "SA", [("Address", "")],
     [("IND", "indication"), ("RGB", "color")],
     "SA searchlight as one pixel. Was -CL-Pixel.", {}),
    ("Device-Head-H2-RGB", "Device-Head-CL-RGB", "H2", [],
     [("IND", "indication"), ("~{R}", "binary"), ("~{G}", "binary"), ("~{B}", "binary")],
     "US&S H-2 searchlight as one RGB LED, three legs; same reference row as SA today.", {}),
    ("Device-Head-H2-Pixel", "Device-Head-CL-Pixel", "H2", [("Address", "")],
     [("IND", "indication"), ("RGB", "color")],
     "US&S H-2 searchlight as one pixel; same reference row as SA today.", {}),
    ("Device-Head-Semaphore-UQ", "Device-Head-Semaphore-UQ", "UQ",
     [("stop_deg", ""), ("approach_deg", ""), ("clear_deg", "")],
     [("IND", "indication"), ("ARM", "position")],
     "Mast indication to one upper-quadrant semaphore head's arm position; the angles are this device's settings. Style is fixed: UQ. Three positions, no flash.", {}),
    ("Device-Head-Semaphore-LQ", "Device-Head-Semaphore-LQ", "LQ",
     [("stop_deg", ""), ("approach_deg", ""), ("clear_deg", "")],
     [("IND", "indication"), ("ARM", "position")],
     "Mast indication to one lower-quadrant semaphore head's arm position; the angles are this device's settings. Style is fixed: LQ. Two positions, no flash.", {}),
]

# A pin block that no source target has in the right place: the one-wire RGB pin, taken from this symbol.
RGB_PIN_SOURCE = ("Railroad-Field", "Device-Head-CL-Pixel", "RGB")

# ---------------------------------------------------------------------------------------------

PROPERTY = re.compile(r'^\t\t\(property "([^"]+)" "((?:[^"\\]|\\.)*)"\n(?:\t\t\t[^\n]*\n)*?\t\t\)\n', re.M)
PIN_HEAD = re.compile(r'\(pin (\w+) (\w+)\n\t\t\t\t\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\n\t\t\t\t\(length ([-\d.]+)\)\n\t\t\t\t\(name "((?:[^"\\]|\\.)*)"')
PIN_NUMBER = re.compile(r'\(number "[^"]*"')


def base(pin: str) -> str:
    m = re.match(r"^~\{(.+)\}$", pin)
    return m.group(1) if m else pin


def quote(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


class Library:
    def __init__(self, path: Path):
        self.text = path.read_text()
        self.header = self.text[: self.text.index('\n\t(symbol "') + 1]
        self.symbols = {}
        for s, e in blocks(self.text, "symbol", 1):
            b = self.text[s:e]
            self.symbols[re.match(r'\(symbol "([^"]+)"', b).group(1)] = "\t" + b + "\n"


def properties(block: str) -> list[re.Match]:
    return list(PROPERTY.finditer(block))


def with_value(prop_block: str, value: str) -> str:
    return re.sub(r'^(\t\t\(property "[^"]+" )"(?:[^"\\]|\\.)*"', lambda m: m.group(1) + '"' + quote(value) + '"',
                  prop_block, count=1, flags=re.M)


def renamed(prop_block: str, name: str) -> str:
    return re.sub(r'^\t\t\(property "[^"]+"', '\t\t(property "' + quote(name) + '"', prop_block, count=1, flags=re.M)


def rewrite_properties(block: str, wanted: list[tuple[str, str]]) -> str:
    """Replace the symbol's property list by `wanted` (name, value), in that order, copying each block's
    shape from the source where it has the field, else from a hidden template of the same symbol."""
    props = properties(block)
    have = {p.group(1): p.group(0) for p in props}
    pin_template = next((v for k, v in reversed(have.items()) if k.startswith("Pin.")), None)
    hidden_template = have.get("Name") or have["Footprint"]
    out = []
    for name, value in wanted:
        if name in have:
            out.append(with_value(have[name], value))
        elif name.startswith("Pin.") and pin_template:
            out.append(with_value(renamed(pin_template, name), value))
        else:
            out.append(with_value(renamed(hidden_template, name), value))
    for name, text in have.items():                              # KiCad's own hidden fields stay
        if name.startswith("ki_") and name not in dict(wanted):
            out.append(text)
    return block[: props[0].start()] + "".join(out) + block[props[-1].end():]


def pins(block: str) -> list[tuple[int, int, re.Match]]:
    return [(s, e, PIN_HEAD.match(block, s)) for s, e in blocks(block, "pin", 3)]


def polyline(x1: float, y1: float, x2: float, y2: float) -> str:
    return ("\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy %s %s) (xy %s %s)\n\t\t\t\t)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n"
            "\t\t\t\t\t(type solid)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n\t\t\t)" % (fmt(x1), fmt(y1), fmt(x2), fmt(y2)))


def circle(cx: float, cy: float, red: bool) -> str:
    fill = "\t\t\t\t(fill\n\t\t\t\t\t(type color)\n\t\t\t\t\t(color 255 0 0 1)\n\t\t\t\t)\n" if red else "\t\t\t\t(fill\n\t\t\t\t\t(type none)\n\t\t\t\t)\n"
    return ("\t\t\t(circle\n\t\t\t\t(center %s %s)\n\t\t\t\t(radius 0.508)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n"
            "\t\t\t\t\t(type solid)\n\t\t\t\t)\n%s\t\t\t)" % (fmt(cx), fmt(cy), fill))


def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pin_end(m: re.Match) -> tuple[float, float, float, float]:
    x, y, rot, length = float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6))
    dx, dy = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[int(rot)]
    return x, y, x + dx * length, y + dy * length


def renumber(block: str) -> str:
    n = 0
    out, pos = [], 0
    for s, e in blocks(block, "pin", 3):
        n += 1
        out.append(block[pos:s] + PIN_NUMBER.sub('(number "%d"' % n, block[s:e], count=1))
        pos = e
    return "".join(out) + block[pos:]


def rename(block: str, src: str, dst: str) -> str:
    return block.replace('(symbol "%s"' % quote(src), '(symbol "%s"' % quote(dst)).replace(
        '(symbol "%s_' % quote(src), '(symbol "%s_' % quote(dst))


def line_span(block: str, s: int, e: int) -> tuple[int, int]:
    """The whole lines of a depth-3 node found by blocks(): from its leading tabs through its newline."""
    s0 = block.rindex("\n", 0, s) + 1
    return s0, (e + 1 if block[e] == "\n" else e)


def insert_graphics(block: str, text: str) -> str:
    """Insert `text` (depth-3 graphic lines, no trailing newline) before the last unit's first pin: KiCad writes a
    unit's graphics before its pins."""
    us, ue = list(blocks(block, "symbol", 2))[-1]                 # the drawing unit, "<name>_1_1", is last
    first_pin = next((s for s, _ in blocks(block, "pin", 3) if us < s < ue), None)
    at = block.rindex("\n", 0, first_pin) if first_pin else ue - 4
    assert first_pin or block[ue - 4:ue] == "\n\t\t)", block[ue - 20:ue]
    return block[:at] + "\n" + text + block[at:]


def insert_at_unit_end(block: str, text: str) -> str:
    """Append `text` (depth-3 lines, no trailing newline) to the last unit's body, after its pins."""
    us, ue = list(blocks(block, "symbol", 2))[-1]
    assert block[ue - 4:ue] == "\n\t\t)", block[ue - 20:ue]
    return block[:ue - 4] + "\n" + text + block[ue - 4:]


def make_mast(lib: Library, target, src, style, kind, indications, description, heads) -> str:
    block = rename(lib.symbols[src], src, target)
    edits, lines, glyph_x, glyph_y = [], [], None, None
    for s, e, m in pins(block):
        if m.group(7) == "SIGNAL":
            continue
        x1, y1, x2, y2 = pin_end(m)
        edits.append(line_span(block, s, e) + ("",))
        if float(m.group(6)):
            lines.append(polyline(x1, y1, x2, y2))             # the line the pin drew, so the picture is unchanged
            glyph_x = min(x1, x2) if glyph_x is None else min(glyph_x, x1, x2)   # the glyphs abut the drawn line
            glyph_y = y1
    assert glyph_x is not None, target
    block = replace_spans(block, edits)
    lines += [circle(glyph_x - 0.635 - 1.27 * i, glyph_y, red=(style == "stop_sign")) for i in range(heads)]
    block = renumber(insert_graphics(block, "\n".join(lines)))
    wanted = [("Reference", properties(block)[0].group(2)), ("Value", ""), ("Footprint", ""), ("Datasheet", ""),
              ("Description", description), ("Role", "APPLIANCE"), ("Name", "${Value}"), ("Appliance", "mast"),
              ("Style", style), ("Kind", kind), ("Indications", indications)]
    return rewrite_properties(block, wanted)


def make_device(lib: Library, rgb_pin: str, target, src, style, settings, pin_list, description, relabels) -> str:
    block = rename(lib.symbols[src], src, target)
    wanted_names = [n for n, _ in pin_list]
    have = {m.group(7): (s, e) for s, e, m in pins(block)}
    block = replace_spans(block, [line_span(block, s, e) + ("",) for name, (s, e) in have.items() if name not in wanted_names])
    for name in wanted_names:
        if name not in have:
            assert name == "RGB", (target, name)
            block = insert_at_unit_end(block, rgb_pin)
    block = renumber(block)
    for old, new in relabels.items():
        block = block.replace('(text "%s"' % old, '(text "%s"' % new)
    wanted = [("Reference", properties(block)[0].group(2)), ("Value", ""), ("Footprint", ""), ("Datasheet", ""),
              ("Description", description), ("Role", "DEVICE"), ("Name", "${Value}"), ("Appliance", "head"),
              ("Style", style)] + settings + [("Pin." + base(n), w) for n, w in pin_list]
    return rewrite_properties(block, wanted)


def main() -> int:
    trackplan = Library(SYMBOLS / "Railroad-Trackplan.kicad_sym")
    field = Library(SYMBOLS / "Railroad-Field.kicad_sym")
    rgb_block = field.symbols[RGB_PIN_SOURCE[1]]
    rgb_pin = next("\t\t\t" + rgb_block[s:e] for s, e, m in pins(rgb_block) if m.group(7) == RGB_PIN_SOURCE[2])

    masts = [make_mast(trackplan, *row) for row in TRACKPLAN]
    (SYMBOLS / "Railroad-Trackplan-Signals.kicad_sym").write_text(trackplan.header + "".join(masts) + ")\n")
    devices = [make_device(field, rgb_pin, *row) for row in FIELD]
    (SYMBOLS / "Railroad-Field-Signals.kicad_sym").write_text(field.header + "".join(devices) + ")\n")
    print(f"wrote Railroad-Trackplan-Signals ({len(masts)} symbols) and Railroad-Field-Signals ({len(devices)} symbols)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
