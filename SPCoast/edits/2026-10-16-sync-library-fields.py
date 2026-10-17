#!/usr/bin/env python3
"""One-off, 2026-10-16: make every placed instance agree with its library symbol on the fields the
library owns (Role, Appliance, Style, IC, Kind, Pin.*).

    python3 SPCoast/edits/2026-10-16-sync-library-fields.py [--dry-run] [--project DIR] [--libdir DIR]

Why: KiCad copies a symbol's fields at placement and never follows the library afterwards. The
2026-10-12 migration filled empty instance fields from the library but kept a non-empty value, so
the head instances placed before the libraries were corrected still say Role COMPONENT and Style
CPL while `Railroad-Trackplan` says APPLIANCE and CL/CPL/LQ/UQ. The front-end rule agreed on
2026-10-16: library-owned fields come from the library by lib_id, and an instance that disagrees
is a diagnostic. This script clears the backlog by text edits that keep every untouched byte.

Rules: a library-owned field whose library value is non-empty is set to the library value; a
library-owned field the instance lacks is added, hidden; a library-owned field on the instance
that the library symbol does not declare is reported, not removed. No other field is touched.
KiCad must be closed (no ~*.lck in the project).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks  # noqa: E402

RAILROAD = Path.home() / "Dropbox/KiCad/Railroad"
SPCOAST = RAILROAD / "SPCoast"
LIBDIR = RAILROAD / "symbols"
LIBRARIES = ("Railroad-Trackplan", "Railroad-Office", "Railroad-Field", "Railroad-HardwareIO")
OWNED = ("Role", "Appliance", "Style", "IC", "Kind")


def owned(name: str) -> bool:
    return name in OWNED or name.startswith("Pin.")


def props_of(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def set_value(block: str, s: int, value: str) -> str:
    m = re.match(r'\(property "(?:[^"\\]|\\.)*" "', block[s:])
    vs = s + m.end()
    ve = block.index('"', vs)
    while block[ve - 1] == "\\":
        ve = block.index('"', ve + 1)
    return block[:vs] + value + block[ve:]


def new_property(name: str, value: str, at: str) -> str:
    return (f'\n\t\t(property "{name}" "{value}"\n\t\t\t(at {at} 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)'
            f'\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)')


def library_fields(libdir: Path) -> dict[str, dict[str, str]]:
    """{lib_id: {owned field: value}} from the four libraries."""
    out = {}
    for lib in LIBRARIES:
        text = (libdir / f"{lib}.kicad_sym").read_text()
        for s, e in blocks(text, "symbol", 1):
            b = text[s:e]
            name = re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', b).group(1)
            out[f"{lib}:{name}"] = {k: v for k, (v, _, _) in props_of(b, 2).items() if owned(k)}
    return out


def sync_sheet(path: Path, libs: dict[str, dict[str, str]], dry: bool, report: list[str]) -> int:
    text = path.read_text()
    edits = []
    changed = 0
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        lib_id = re.search(r'\n\t\t\(lib_id "((?:[^"\\]|\\.)*)"', b)
        if not lib_id or lib_id.group(1) not in libs:
            continue
        lib = libs[lib_id.group(1)]
        inst = props_of(b, 2)
        ref = inst.get("Reference", ("?",))[0]
        at = re.search(r"\n\t\t\(at ([-\d.]+ [-\d.]+)", b).group(1)
        nb = b
        for name, (iv, _, _) in inst.items():
            if owned(name) and name not in lib:
                report.append(f"{path.name} {ref}: {name}={iv!r} not declared by {lib_id.group(1)} (kept)")
        for name, lv in lib.items():
            if lv == "":
                continue
            cur = props_of(nb, 2)
            if name in cur:
                iv, ps, _ = cur[name]
                if iv != lv:
                    report.append(f"{path.name} {ref}: {name} {iv!r} -> {lv!r} ({lib_id.group(1)})")
                    nb = set_value(nb, ps, lv)
            else:
                report.append(f"{path.name} {ref}: {name} added = {lv!r} ({lib_id.group(1)})")
                last = max(pe for _, _, pe in cur.values())
                nb = nb[:last] + new_property(name, lv, at) + nb[last:]
        if nb != b:
            edits.append((s, e, nb))
            changed += 1
    if edits and not dry:
        out, pos = [], 0
        for s, e, nb in edits:
            out += [text[pos:s], nb]
            pos = e
        path.write_text("".join(out) + text[pos:])
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--project", type=Path, default=SPCOAST)
    ap.add_argument("--libdir", type=Path, default=LIBDIR)
    a = ap.parse_args(argv)
    if list(a.project.glob("~*.lck")):
        print("KiCad holds a lock on the project; close it first", file=sys.stderr)
        return 2
    libs = library_fields(a.libdir)
    report: list[str] = []
    total = 0
    for sheet in sorted(a.project.glob("*.kicad_sch")):
        total += sync_sheet(sheet, libs, a.dry_run, report)
    print("\n".join(report))
    print(f"{'would change' if a.dry_run else 'changed'} {total} instances in {a.project}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
