#!/usr/bin/env python3
"""One-off, 2026-10-13: the six-head set and the field-layout outcome (checkpoint E71 to E73).

Railroad-Field, by text:
- Device-Head-CL-1 -> Device-Head-CL-Pixel (RGB color, Style CL).
- Device-Head-CL_3 -> Device-Head-CL: legs ~{R} ~{G} ~{B} binary (was R Y G); yellow is R plus G.
- Device-Head-Semaphore-UQ-CL -> Device-Head-Semaphore, Style "LQ, UQ": ARM position, LAMP color
  (pixel direct; a white lamp on an expander or PWM pin by the color-to-binary or -level cast).
- Device-Head-Semaphore-UQ-CL_3 -> Device-Head-Semaphore-RGB, Style "LQ, UQ": ARM, ~{R} ~{G} ~{B}
  (the Y leg becomes B; unit order kept so placed units stay valid).
- Device-Head-Semaphore-LQ, -UQ (binary lamp) and Local-Lamp: deleted (E71, E72).
- Local-Switch, Local-Lock: Role DEVICE (PANEL is the machine's column plates only, E72).
- Reference prefixes by device kind (E73): DevHead, DevLamp, DevSW, DevLock, DevTC, DevContact.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks, end_of  # noqa: E402

LIB = Path.home() / "Dropbox/KiCad/Railroad/symbols/Railroad-Field.kicad_sym"


def symbol_blocks(text):
    out, first = {}, None
    for s, e in blocks(text, "symbol", 1):
        first = s if first is None else first
        out[re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', text[s:e]).group(1)] = text[s:e]
    return text[: first - 2], out


def set_prop(b, name, value):
    m = re.search(r'\n\t\t\(property "%s" "' % re.escape(name), b)
    if m:
        s = m.end(); e = b.index('"', s)
        while b[e - 1] == "\\":
            e = b.index('"', e + 1)
        return b[:s] + value + b[e:]
    t = re.search(r'\n\t\t\(property "Role" ', b); ts = t.start() + 3; te = end_of(b, ts)
    tmpl = re.sub(r'^\(property "Role" "[^"]*"', '(property "%s" "%s"' % (name, value), b[ts:te], count=1)
    return b[:te] + "\n\t\t" + tmpl + b[te:]


def del_prop(b, name):
    m = re.search(r'\n\t\t\(property "%s" ' % re.escape(name), b)
    if not m:
        return b
    s = m.start() + 3; e = end_of(b, s)
    return b[:s - 3] + b[e:]


def rename_prop(b, old, new):
    return b.replace('(property "%s" "' % old, '(property "%s" "' % new, 1)


def rename_symbol(b, old, new):
    return b.replace('(symbol "%s"' % old, '(symbol "%s"' % new).replace('(symbol "%s_' % old, '(symbol "%s_' % new)


def rename_pin(b, old, new):
    assert b.count('(name "%s"' % old) == 1, (old, b.count('(name "%s"' % old))
    return b.replace('(name "%s"' % old, '(name "%s"' % new, 1)


PREFIX = {"Device-Head": "DevHead", "Device-Lamp": "DevLamp", "Device-Switch": "DevSW", "Device-Lock": "DevLock",
          "Device-TrackCircuit": "DevTC", "Device-Contact": "DevContact"}

header, syms = symbol_blocks(LIB.read_text())
out = {}
for name, b in syms.items():
    if name in ("Device-Head-Semaphore-LQ", "Device-Head-Semaphore-UQ", "Local-Lamp"):
        continue
    if name == "Device-Head-CL-1":
        name = "Device-Head-CL-Pixel"; b = rename_symbol(b, "Device-Head-CL-1", name)
        b = set_prop(b, "Description", "Color light head on a pixel chain: one RGB point, one color at a time; Address is its slot (E71).")
    elif name == "Device-Head-CL_3":
        name = "Device-Head-CL"; b = rename_symbol(b, "Device-Head-CL_3", name)
        b = rename_pin(b, "~{Y}", "~{G}@"); b = rename_pin(b, "~{G}", "~{B}"); b = rename_pin(b, "~{G}@", "~{G}")
        b = rename_prop(b, "Pin.G", "Pin.B@"); b = rename_prop(b, "Pin.Y", "Pin.G"); b = rename_prop(b, "Pin.B@", "Pin.B")
        b = set_prop(b, "Description", "Color light head as one RGB LED, three legs: red is R, yellow is R plus G, green is G, lunar is all three. On an expander or, with brightness per leg, on PWM (E71).")
    elif name == "Device-Head-Semaphore-UQ-CL":
        name = "Device-Head-Semaphore"; b = rename_symbol(b, "Device-Head-Semaphore-UQ-CL", name)
        b = set_prop(b, "Style", "LQ, UQ")
        b = set_prop(b, "Description", "Semaphore head, lower or upper quadrant by the plant head's Style; arm angles are settings. LAMP is a color point: a pixel directly; a white lamp behind the roundel on an expander or PWM pin by the color-to-binary or color-to-level cast (E71).")
    elif name == "Device-Head-Semaphore-UQ-CL_3":
        name = "Device-Head-Semaphore-RGB"; b = rename_symbol(b, "Device-Head-Semaphore-UQ-CL_3", name)
        b = set_prop(b, "Style", "LQ, UQ")
        b = rename_pin(b, "~{Y}", "~{B}")
        b = del_prop(b, "Pin.LAMP"); b = del_prop(b, "Pin.Y")
        for leg in ("R", "G", "B"):
            b = set_prop(b, f"Pin.{leg}", "binary")
        b = set_prop(b, "Description", "Semaphore head with an RGB LED behind the roundel-less lens: ARM position; legs R, G, B as the color light head (E71).")
    elif name in ("Local-Switch", "Local-Lock"):
        b = set_prop(b, "Role", "DEVICE")
    for prefix, ref in PREFIX.items():
        if name.startswith(prefix):
            b = set_prop(b, "Reference", ref)
    out[name] = b
LIB.write_text(header + "".join("\n\t" + out[n] for n in sorted(out)) + "\n)\n")
print(f"Railroad-Field: {len(syms)} -> {len(out)} symbols")
