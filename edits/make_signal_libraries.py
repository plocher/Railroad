"""Generate `symbols/Railroad-Field-Signals.kicad_sym`: field masts, head devices and encoders (take 3, 2026-11-04).

The chain is  trackplan Mast --indication--> field Mast device --pin A/B/C--> anonymous Head --head word-->
Encoder --pins / pixels--> Driver.  The field mast device is the binding: Value = the trackplan mast's Name
(246AB), one output per head position, A at the top; the pin set is the head count (Single, Double,
Triple), so it carries no Style, Kind or Indications. A head device has no name of its own: it is a
position on a mast, keyed by the mast pin it is wired to, so it carries no `Name` property. It states
only which model it is (Style); it takes an indication on `IND` and presents a head word on `APP`, both
of pin kind indication. An encoder states only its hardware side: one `APP` input and the output pins or
pixel addresses a driver consumes; the mapping head word -> output is the served head's model table,
reference data read through the wire.

`symbols/Railroad-Trackplan-Signals.kicad_sym` is the owner's, maintained by hand in KiCad; this script
no longer touches it, nor the older libraries it reads graphics from (`Railroad-Field.kicad_sym`).

Every symbol is composed from text templates in the shape KiCad 10 writes: the library header is the
source's; the box, the arrows and the glyphs are the source symbols' own graphic nodes copied verbatim
(Device-Head-CPL's box and lamp glyph, Device-Head-CL-RGB's searchlight, Device-Head-CL-Pixel's pixel,
Device-Head-Semaphore-UQ's arm); the properties are exactly the worklist's set, hidden ones in KiCad's
hidden-property shape. Overbar names (`~{R}`) mark asserted-low binary outputs, as the old symbols'
inputs had.

Run from the Railroad repo with the Subdivision venv:

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python edits/make_signal_libraries.py

Deterministic: a second run writes an identical file. The worklist is
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
from kicad_services.sch_text import blocks  # noqa: E402

SYMBOLS = ROOT / "symbols"
SOURCE = SYMBOLS / "Railroad-Field.kicad_sym"
TARGET = SYMBOLS / "Railroad-Field-Signals.kicad_sym"

# ---------------------------------------------------------------------------------------------
# The worklist.

ANONYMOUS = " Anonymous: a head is a position on its mast, keyed by the mast pin (A, B, C) it is wired to."
HEADS = [
    # (symbol, Style, Description)
    ("Device-Head-TypeD", "TypeD",
     "GRS Type D colour-light head. Presents what its model table lists; the encoder it is wired to makes the lamps." + ANONYMOUS),
    ("Device-Head-SA", "SA", "GRS SA searchlight head." + ANONYMOUS),
    ("Device-Head-H2", "H2", "US&S H-2 searchlight head." + ANONYMOUS),
    ("Device-Head-Semaphore-UQ", "UQ", "Upper-quadrant semaphore head, three positions." + ANONYMOUS),
    ("Device-Head-Semaphore-LQ", "LQ", "Lower-quadrant semaphore head, two positions." + ANONYMOUS),
]

MASTS = [
    # (symbol, head positions)
    ("Device-Mast-Single", 1),
    ("Device-Mast-Double", 2),
    ("Device-Mast-Triple", 3),
]
MAST_DESCRIPTION = ("A mast as one field device, Value = the trackplan mast's Name (246AB). One output per head position, "
                    "A at the top; each hands that head its indication word. Head devices hang on these pins; a head has "
                    "no name of its own.")

# Output pins: (name as drawn, electrical type, Pin.<base> word or None for a bus attachment).
BINARY = "binary"
ENCODERS = [
    # (symbol, Kind, outputs, settings [(field, placement)], glyph source symbol, Description)
    ("Encoder-RYG", "RYG", [("~{R}", "output", BINARY), ("~{Y}", "output", BINARY), ("~{G}", "output", BINARY)], [],
     "Device-Head-CPL", "Three lamp lines for a three-lamp head, to any driver's pins."),
    ("Encoder-RGB", "RGB", [("~{R}", "output", BINARY), ("~{G}", "output", BINARY), ("~{B}", "output", BINARY)], [],
     "Device-Head-CL-RGB", "Three legs of one tricolour LED (a searchlight); the palette mixes yellow."),
    ("Encoder-2bit", "TWO_BIT", [("S0", "output", BINARY), ("S1", "output", BINARY)], [("Code", "below0")],
     "Device-Head-CPL", "Two-bit select for the decoder on the mast; Code names the table. 35 placements on SPCoast today."),
    ("Encoder-Pixel", "PIXEL", [("CHAIN", "passive", None)],
     [("Address.R", "below0"), ("Address.Y", "below1"), ("Address.G", "below2")],
     "Device-Head-CL-Pixel", "Three pixels on a chain, one per lamp colour; no span, nothing positional."),
    ("Encoder-Pixel-RGB", "PIXEL_RGB", [("CHAIN", "passive", None)], [("Address", "below0")],
     "Device-Head-CL-Pixel", "One pixel showing the head's colour."),
    ("Encoder-Servo", "SERVO", [("ARM", "output", "position")],
     [("stop_deg", "hidden"), ("approach_deg", "hidden"), ("clear_deg", "hidden")],
     "Device-Head-Semaphore-UQ", "A blade's angles, moved here from the semaphore head devices."),
]

BOX_SOURCE = "Device-Head-CPL"          # the box every symbol here draws, and the input and output arrows
GLYPH_X = -12.065                       # the box's middle: a glyph sits between the APP name and the output names
COORD = re.compile(r"\((xy|center|start|mid|end|at) ([-\d.]+) ([-\d.]+)")
PIN_LENGTH = 2.54
INPUT_AT = (-24.13, 0.0)                # the input pin, pointing right, as the old head devices
OUTPUT_X = 0.0                          # output pins point left from the box's right edge
OUTPUT_ROWS = {1: [0.0], 2: [1.27, -1.27], 3: [2.54, 0.0, -2.54]}

# Where a setting shows: stacked below the box with its name (an address is filled in per instance and should
# be read on the sheet), or hidden as the old semaphore devices' angles.
PLACEMENTS = {
    "hidden": "\t\t\t(at -11.43 -6.35 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace yes)\n\t\t\t(hide yes)\n"
              "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.635 0.635)\n\t\t\t\t)\n\t\t\t)\n",
}
# ---------------------------------------------------------------------------------------------
# Text shapes (KiCad 10, tab-indented one node per line).


def fmt(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


for _i in range(3):
    PLACEMENTS[f"below{_i}"] = ("\t\t\t(at -21.59 %s 0)\n\t\t\t(show_name yes)\n\t\t\t(do_not_autoplace yes)\n"
                                "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.016 1.016)\n\t\t\t\t)\n"
                                "\t\t\t\t(justify left)\n\t\t\t)\n") % fmt(-4.826 - 1.27 * _i)


def quote(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def base(pin: str) -> str:
    m = re.match(r"^~\{(.+)\}$", pin)
    return m.group(1) if m else pin


def prop(name: str, value: str, body: str) -> str:
    return '\t\t(property "%s" "%s"\n%s\t\t)\n' % (quote(name), quote(value), body)


HIDDEN = ("\t\t\t(at 0 0 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(hide yes)\n"
          "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n")
CONTRACT = ("\t\t\t(at -11.43 5.461 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace yes)\n\t\t\t(hide yes)\n"
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.635 0.635)\n\t\t\t\t)\n\t\t\t)\n")
REFERENCE = ("\t\t\t(at -11.43 4.699 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace yes)\n\t\t\t(hide yes)\n"
             "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.762 0.762)\n\t\t\t\t)\n\t\t\t)\n")
DESCRIPTION = ("\t\t\t(at 0 -5.08 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(hide yes)\n"
               "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n")


def pin_cap(x: float, y: float) -> str:
    """A Pin.* property, placed at its pin's end as the old symbols did."""
    return ("\t\t\t(at %s %s 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace yes)\n\t\t\t(hide yes)\n"
            "\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 0.635 0.635)\n\t\t\t\t)\n\t\t\t)\n") % (fmt(x), fmt(y))


def pin(etype: str, x: float, y: float, rot: int, name: str, number: int) -> str:
    return ("\t\t\t(pin %s line\n\t\t\t\t(at %s %s %d)\n\t\t\t\t(length %s)\n"
            "\t\t\t\t(name \"%s\"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.016 1.016)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n"
            "\t\t\t\t(number \"%d\"\n\t\t\t\t\t(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 0.381 0.381)\n\t\t\t\t\t\t)\n\t\t\t\t\t)\n\t\t\t\t)\n"
            "\t\t\t)\n") % (etype, fmt(x), fmt(y), rot, fmt(PIN_LENGTH), quote(name), number)


def arrow(x: float, y: float) -> str:
    """The maroon direction triangle the old head devices drew at a pin's root, pointing right."""
    return ("\t\t\t(polyline\n\t\t\t\t(pts\n\t\t\t\t\t(xy %s %s) (xy %s %s) (xy %s %s) (xy %s %s)\n\t\t\t\t)\n"
            "\t\t\t\t(stroke\n\t\t\t\t\t(width 0)\n\t\t\t\t\t(type solid)\n\t\t\t\t)\n"
            "\t\t\t\t(fill\n\t\t\t\t\t(type color)\n\t\t\t\t\t(color 132 0 0 1)\n\t\t\t\t)\n\t\t\t)\n"
            ) % (fmt(x), fmt(y), fmt(x - 0.635), fmt(y - 0.635), fmt(x - 0.635), fmt(y + 0.635), fmt(x), fmt(y))


def label(text: str) -> str:
    """The box's label, in the Field library's shape: KIND ${VALUE} top left inside the box."""
    return ("\t\t\t(text \"%s\"\n\t\t\t\t(at -20.955 2.667 0)\n\t\t\t\t(effects\n\t\t\t\t\t(font\n\t\t\t\t\t\t(size 1.016 1.016)\n"
            "\t\t\t\t\t)\n\t\t\t\t\t(justify left)\n\t\t\t\t)\n\t\t\t)\n") % quote(text)


# ---------------------------------------------------------------------------------------------
# Reading the source library: its header and each symbol's graphic nodes.


class Library:
    def __init__(self, path: Path):
        self.text = path.read_text()
        self.header = self.text[: self.text.index('\n\t(symbol "') + 1]
        self.symbols: dict[str, str] = {}
        for s, e in blocks(self.text, "symbol", 1):
            b = self.text[s:e]
            self.symbols[re.match(r'\(symbol "([^"]+)"', b).group(1)] = b

    def graphics(self, symbol: str, unit: str) -> list[tuple[str, str]]:
        """[(node head, node text with its line's tabs and newline)] of a unit's non-pin nodes."""
        b = self.symbols[symbol]
        out = []
        for us, ue in blocks(b, "symbol", 2):
            u = b[us:ue]
            if not re.match(r'\(symbol "%s_%s"' % (re.escape(symbol), unit), u):
                continue
            for head in ("rectangle", "polyline", "circle", "arc", "text"):
                for s, e in blocks(u, head, 3):
                    s0 = u.rindex("\n", 0, s) + 1
                    out.append((head, u[s0:e] + "\n", s0))
        return [(h, t) for h, t, _ in sorted(out, key=lambda x: x[2])]


def box(lib: Library) -> str:
    rects = [t for h, t in lib.graphics(BOX_SOURCE, "0_1") if h == "rectangle"]
    assert len(rects) == 1
    return rects[0]


def glyph(lib: Library, symbol: str) -> str:
    """Everything the source draws in its picture unit except the box, moved so its centre is at GLYPH_X."""
    text = "".join(t for h, t in lib.graphics(symbol, "0_1") if h != "rectangle")
    xs = [float(m.group(2)) for m in COORD.finditer(text)]
    dx = GLYPH_X - (min(xs) + max(xs)) / 2
    return COORD.sub(lambda m: "(%s %s %s" % (m.group(1), fmt(float(m.group(2)) + dx), m.group(3)), text)


# ---------------------------------------------------------------------------------------------


def symbol(name: str, reference: str, contract: list[tuple[str, str]], settings: list[tuple[str, str]],
           pin_caps: list[tuple[str, str, float, float]], description: str, picture: str, body: str) -> str:
    """One top-level symbol: KiCad's flags, the properties in its order, the picture unit, the pin unit."""
    props = [prop("Reference", reference, REFERENCE), prop("Value", "", HIDDEN), prop("Footprint", "", HIDDEN),
             prop("Datasheet", "", HIDDEN), prop("Description", description, DESCRIPTION)]
    props += [prop(k, v, HIDDEN if k == "Name" else CONTRACT) for k, v in contract]
    props += [prop(k, "", PLACEMENTS[place]) for k, place in settings]
    props += [prop("Pin." + k, v, pin_cap(x, y)) for k, v, x, y in pin_caps]
    return ('\t(symbol "%s"\n\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)\n\t\t(pin_names\n\t\t\t(offset 0.889)\n\t\t)\n'
            "\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n"
            "\t\t(duplicate_pin_numbers_are_jumpers no)\n" % quote(name)
            + "".join(props)
            + '\t\t(symbol "%s_0_1"\n%s\t\t)\n' % (quote(name), picture)
            + '\t\t(symbol "%s_1_1"\n%s\t\t)\n' % (quote(name), body)
            + "\t\t(embedded_fonts no)\n\t)\n")


def make_head(lib: Library, name: str, style: str, description: str) -> str:
    ix, iy = INPUT_AT
    ox, oy = OUTPUT_X, OUTPUT_ROWS[1][0]
    body = arrow(ix + PIN_LENGTH + 0.889, iy) + arrow(ox - PIN_LENGTH - 0.254, oy) + label(style)   # no name: anonymous
    body += pin("input", ix, iy, 0, "IND", 1) + pin("output", ox, oy, 180, "APP", 2)
    contract = [("Role", "DEVICE"), ("Appliance", "head"), ("Style", style)]                        # no Name property
    caps = [("IND", "indication", ix - 4.318, iy), ("APP", "indication", ox + 5.588, oy)]
    return symbol(name, "Cast", contract, [], caps, description, box(lib), body)


def make_mast(lib: Library, name: str, heads: int) -> str:
    """A field mast device: one indication output per head position, A at the top, in the Railroad-Field:Mast look."""
    rows = OUTPUT_ROWS[heads]
    letters = "ABC"[:heads]
    body = "".join(arrow(OUTPUT_X - PIN_LENGTH - 0.254, y) for y in rows) + label("MAST ${VALUE}")
    body += "".join(pin("output", OUTPUT_X, y, 180, letter, i + 1) for i, (letter, y) in enumerate(zip(letters, rows)))
    contract = [("Role", "DEVICE"), ("Name", "${Value}"), ("Appliance", "mast")]
    caps = [(letter, "indication", OUTPUT_X + 5.588, y) for letter, y in zip(letters, rows)]
    return symbol(name, "DevMast", contract, [], caps, MAST_DESCRIPTION, box(lib), body)


def make_encoder(lib: Library, name: str, kind: str, outputs, settings, glyph_source: str, description: str) -> str:
    ix, iy = INPUT_AT
    rows = OUTPUT_ROWS[len(outputs)]
    body = arrow(ix + PIN_LENGTH + 0.889, iy)
    body += "".join(arrow(OUTPUT_X - PIN_LENGTH - 0.254, y) for (_, etype, _), y in zip(outputs, rows) if etype == "output")
    body += label(f"{kind} ${{VALUE}}")
    body += pin("input", ix, iy, 0, "APP", 1)
    body += "".join(pin(etype, OUTPUT_X, y, 180, pname, i + 2) for i, ((pname, etype, _), y) in enumerate(zip(outputs, rows)))
    contract = [("Role", "ENCODER"), ("Name", "${Value}"), ("Kind", kind)]
    caps = [("APP", "indication", ix - 4.318, iy)]
    caps += [(base(pname), word, OUTPUT_X + 5.588, y) for (pname, _, word), y in zip(outputs, rows) if word]
    return symbol(name, "ENC", contract, settings, caps, description, box(lib) + glyph(lib, glyph_source), body)


def main() -> int:
    lib = Library(SOURCE)
    if list(SYMBOLS.glob("~*.lck")):
        print("a symbol library is open in KiCad (~*.lck present); close it first", file=sys.stderr)
        return 1
    out = ([make_mast(lib, *row) for row in MASTS] + [make_head(lib, *row) for row in HEADS]
           + [make_encoder(lib, *row) for row in ENCODERS])
    out.sort(key=lambda s: re.match(r'\t\(symbol "([^"]+)"', s).group(1))    # KiCad writes symbols by name
    TARGET.write_text(lib.header + "".join(out) + ")\n")
    print(f"wrote {TARGET.name} ({len(MASTS)} field masts, {len(HEADS)} head devices, {len(ENCODERS)} encoders)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
