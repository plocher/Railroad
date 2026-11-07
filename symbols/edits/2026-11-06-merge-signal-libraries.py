#!/usr/bin/env python3
"""2026-11-06: fold the -Signals staging libraries into the main libraries.

1. Delete the old signal symbols (zero placements in SPCoast and Tutorial)
   from Railroad-Trackplan and Railroad-Field.
2. Move every top-level (symbol "Name" ...) block, with its unit sub-symbols,
   from Railroad-Trackplan-Signals into Railroad-Trackplan and from
   Railroad-Field-Signals into Railroad-Field. Symbol text is not changed.
   The -Signals files are left in place with no symbols.

Purely textual: a top-level symbol starts at a line "\t(symbol \"" and ends at
the next line that is exactly "\t)". Header and footer lines are kept as is.
Stops without writing if a name would collide.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

DELETE = {
    "Railroad-Trackplan": [
        "Signal Head - CL", "Signal Head - CPL", "Signal Head - Semaphore-UQ",
        "Signal Mast Double CONTROLLED", "Signal Mast Dwarf CONTROLLED",
        "Signal Mast Plate-R", "Signal Mast Single ABSOLUTE",
        "Signal Mast Single CONTROLLED", "Signal Mast Single PERMISSIVE",
    ],
    "Railroad-Field": [
        "Mast", "Device-Head-CL-Pixel", "Device-Head-CL-RGB", "Device-Head-CPL",
        "Device-Head-CPL-Encoded", "Device-Head-CPL-Pixel",
        "Device-Head-Semaphore-LQ", "Device-Head-Semaphore-UQ",
    ],
}
MOVE = {"Railroad-Trackplan-Signals": "Railroad-Trackplan",
        "Railroad-Field-Signals": "Railroad-Field"}


def parse(path):
    lines = path.read_text().splitlines(keepends=True)
    header, blocks, footer = [], [], []
    i, n = 0, len(lines)
    while i < n and not lines[i].startswith('\t(symbol "'):
        header.append(lines[i]); i += 1
    while i < n and lines[i].startswith('\t(symbol "'):
        name = lines[i].split('"')[1]
        j = i
        while lines[j] != "\t)\n":
            j += 1
        blocks.append((name, "".join(lines[i:j + 1])))
        i = j + 1
    footer = lines[i:]
    assert not any(l.startswith('\t(symbol "') for l in footer), path
    return header, blocks, footer


def write(path, header, blocks, footer):
    path.write_text("".join(header) + "".join(b for _, b in blocks) + "".join(footer))


def main():
    libs = {}
    for name in list(DELETE) + list(MOVE):
        libs[name] = parse(HERE / f"{name}.kicad_sym")
    for lib, names in DELETE.items():
        header, blocks, footer = libs[lib]
        have = {b[0] for b in blocks}
        missing = [x for x in names if x not in have]
        if missing:
            sys.exit(f"{lib}: not found, nothing written: {missing}")
        libs[lib] = (header, [b for b in blocks if b[0] not in names], footer)
        print(f"{lib}: deleted {len(names)}")
    for src, dst in MOVE.items():
        sh, sb, sf = libs[src]
        dh, db, df = libs[dst]
        clash = {b[0] for b in sb} & {b[0] for b in db}
        if clash:
            sys.exit(f"{src} -> {dst}: name collision, nothing written: {sorted(clash)}")
        libs[dst] = (dh, db + sb, df)
        libs[src] = (sh, [], sf)
        print(f"{src} -> {dst}: moved {len(sb)}: {[b[0] for b in sb]}")
    for name, (h, b, f) in libs.items():
        write(HERE / f"{name}.kicad_sym", h, b, f)
        print(f"{name}: {len(b)} symbols")


if __name__ == "__main__":
    main()
