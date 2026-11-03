"""Add the Kind property to mast placements that carry none (ADR 0013 §5).

The library's mast symbols are named "Signal Mast <Style> <Kind>" and state the fixed Kind since Railroad 1695d48,
but a placement made before that keeps its own field list, and KiCad's "update symbol fields" with "don't change
existing attribute values" adds no field. This sweep copies the Kind from the library symbol's name into each mast
placement that has no Kind property, as a hidden property at the symbol's own position, formatted as KiCad 10 writes
it. Nothing else in the file changes.

Run from the Railroad repo with the Subdivision venv (2026-11-03):

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python edits/add_mast_kind.py [--dry-run]

It refuses to touch a sheet while KiCad holds its lock (``~<name>.lck``) and reports every edit it makes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEETS = sorted((ROOT / "SPCoast").glob("*.kicad_sch"))
MAST = re.compile(r'\n\t\(symbol\n\t\t\(lib_id "Railroad-Trackplan:Signal Mast (\w+) (CONTROLLED|ABSOLUTE|PERMISSIVE)"\)[\s\S]*?\n\t\)\n')
AT = re.compile(r'\n\t\t\(at ([\d.-]+ [\d.-]+ [\d.-]+)\)')
PROPERTY = re.compile(r'^\t\t\(property "([^"]+)" "([^"]*)"\n(?:\t\t\t[^\n]*\n)*?\t\t\)\n', re.M)
# ^ anchored per line: a pattern that began with "\n" consumed the newline the next property starts on and matched
# only every other property, so the first run (2026-11-03) saw no Kind anywhere and added a duplicate to 26 masts;
# those were removed by hand the same hour. Dry-run first, and check the edit count against the compile's mast.kind.


def kind_block(at: str, kind: str) -> str:
    return ('\t\t(property "Kind" "%s"\n\t\t\t(at %s)\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n') % (kind, at)


def locked(sheet: Path) -> bool:
    return any(sheet.parent.glob(f"~{sheet.stem}.*lck")) or any(sheet.parent.glob("~*.kicad_pro.lck"))


def sweep(dry_run: bool) -> int:
    edits = 0
    for sheet in SHEETS:
        if locked(sheet):
            print(f"skip {sheet.name}: KiCad holds a lock")
            continue
        text = sheet.read_text()
        out = []
        pos = 0
        for m in MAST.finditer(text):
            block, style, kind = m.group(0), m.group(1), m.group(2)
            props = {p.group(1): p for p in PROPERTY.finditer(block)}
            value = props["Value"].group(2) if "Value" in props else "?"
            if "Kind" in props:
                continue
            last = max(props.values(), key=lambda p: p.end())          # append after the last property
            at = AT.search(block).group(1)
            new = block[:last.end()] + kind_block(at, kind) + block[last.end():]
            out.append(text[pos:m.start()] + new)
            pos = m.end()
            edits += 1
            print(f"{sheet.name}: {value} (Signal Mast {style} {kind}) gets Kind={kind} at {at}")
        if pos and not dry_run:
            out.append(text[pos:])
            sheet.write_text("".join(out))
    print(f"{edits} edit(s){' (dry run)' if dry_run else ''}")
    return edits


if __name__ == "__main__":
    sweep("--dry-run" in sys.argv[1:])
