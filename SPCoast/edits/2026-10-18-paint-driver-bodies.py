#!/usr/bin/env python3
"""Paint every IODRIVER body with the driver look (owner, 2026-10-18).

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python \
        SPCoast/edits/2026-10-18-paint-driver-bodies.py [--dry-run] [--libdir DIR]

Symbol looks by Role: a device is a named box with its proxy glyph, a cast is a plain box with
direction arrows, a driver (chips included) has a thick brown border and KiCad's background fill,
as the owner drew on Driver-I2C-MCP23017 unit A. The body of a unit is its largest rectangle;
units without a rectangle share the symbol's common unit (unit 0). Only the stroke and fill of
that one rectangle change; every other byte is kept. KiCad must not have the libraries open.
lint_symbol_fields.py warns when a driver body lacks the look.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks  # noqa: E402

LIBDIR = Path.home() / "Dropbox/KiCad/Railroad/symbols"
LIBRARIES = ("Railroad-Trackplan", "Railroad-Office", "Railroad-Field", "Railroad-HardwareIO")
STROKE = "(stroke\n\t\t\t\t\t(width 0.3048)\n\t\t\t\t\t(type solid)\n\t\t\t\t\t(color 128 77 0 1)\n\t\t\t\t)"
FILL = "(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)"
RECT = re.compile(r"\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)")


def body_rect(unit: str) -> tuple[int, int] | None:
    """Span of the largest rectangle in a unit block, or None."""
    best = None
    for s, e in blocks(unit, "rectangle", 3):
        x1, y1, x2, y2 = map(float, RECT.search(unit[s:e]).groups())
        area = abs(x2 - x1) * abs(y2 - y1)
        if best is None or area > best[0]:
            best = (area, s, e)
    return None if best is None else (best[1], best[2])


def paint(rect: str) -> str:
    (ss, se), = blocks(rect, "stroke", 4)
    (fs, fe), = blocks(rect, "fill", 4)
    assert ss < fs
    return rect[:ss] + STROKE + rect[se:fs] + FILL + rect[fe:]


def paint_library(text: str, report: list[str], lib: str) -> str:
    edits = []
    for s, e in blocks(text, "symbol", 1):
        sym = text[s:e]
        if not re.search(r'\(property "Role" "IODRIVER"', sym):
            continue
        name = re.match(r'\(symbol "([^"]+)"', sym).group(1)
        for us, ue in blocks(sym, "symbol", 2):
            unit = sym[us:ue]
            span = body_rect(unit)
            if span is None:
                continue
            rs, re_ = span
            old = unit[rs:re_]
            new = paint(old)
            if new != old:
                uname = re.match(r'\(symbol "([^"]+)"', unit).group(1).rsplit("_", 2)[1]
                report.append(f"{lib}:{name} unit {uname}")
                edits.append((s + us + rs, s + us + re_, new))
    out, pos = [], 0
    for s, e, new in sorted(edits):
        out += [text[pos:s], new]
        pos = e
    return "".join(out) + text[pos:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--libdir", type=Path, default=LIBDIR)
    a = ap.parse_args(argv)
    report: list[str] = []
    for lib in LIBRARIES:
        p = a.libdir / f"{lib}.kicad_sym"
        text = p.read_text()
        new = paint_library(text, report, lib)
        if new != text and not a.dry_run:
            p.write_text(new)
    print("\n".join(report))
    print(f"{'would paint' if a.dry_run else 'painted'} {len(report)} driver bodies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
