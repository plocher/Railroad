#!/usr/bin/env python3
"""Railroad, 2026-11-13: renumber the Corporal interlocking's switches and desk levers by minus two.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-13-corporal-renumber.py           # dry run: table of planned changes
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-13-corporal-renumber.py --apply   # write

The owner (2026-11-13): at Corporal the lock and the switch take the lever numbers below their signals, so the
desk reads lock 827 / signal 828 in column 11 and switch 829 / signal 830 in column 12. The signals and the track
circuits keep their names.

Name map, applied once per placed unit block. The key is (lib_id, Reference, field, old text): the Reference is an
annotation artifact that does not change, and it is what tells the two Device-Switch-OS and the two PanelSignal
symbols apart once 831 has become 829 and 832 has become 830 (Value alone would chain 829 -> 827 on a second run).
  SPCoast/Corporal.kicad_sch
    Railroad-Trackplan:Switch_Lock      SW11829     Value 829  -> 827
    Railroad-Trackplan:Derail           SW11900     Value 829D -> 827D
    Railroad-Trackplan:Switch_Powered   SW11831     Value 831  -> 829
    Railroad-Field:Device-Switch-OS     DevSW11001  Value 829  -> 827   (3 units)
    Railroad-Field:Device-Switch-OS     DevSW11002  Value 831  -> 829   (3 units)
    Railroad-Field:Local-Lock           LK11001     Value 829  -> 827   (2 units)
    Railroad-Field:Local-Switch         SW11902     Value 829  -> 827   (2 units)
  SPCoast/Corporal-Panel.kicad_sch
    Railroad-Office:PanelLock           LKL12011    Value 829  -> 827   (2 units)
    Railroad-Office:PanelSignal         SGL12011    Value 830  -> 828   (2 units)
    Railroad-Office:PanelSignal         SGL12012    Value 832  -> 830   (2 units)
    Railroad-Office:PanelSwitch         SWL12012    Value 831  -> 829   (2 units)
    Railroad-Office:ModelLamp-YELLOW    LMP12111    Indication 829T1K -> 827T1K   (the literal OS lamp token)
    Railroad-Office:ModelLamp-RED       LMP12112    Indication 831T1K -> 829T1K
Every other field on these symbols is a macro (${Value}, ${Value}NWS, ${VALUE}T1, ...) and follows the Value.

Edit, text only on the `(property "X" "..."` lines, never a re-serialisation. Every unit block of a multi-unit
symbol carries its own properties and is changed.
Left alone: the masts 828NA, 828SA, 830NAB, 830SAB, 832NA, 832SA and the track circuits 832T, 833T, 834T;
References (SW11829, SW11831 are annotation artifacts); every other sheet, the libraries, .history, Scratch
sheets, Panels. A symbol on the two sheets whose Value or literal field carries one of the numbers but is not in
the map is reported and not changed.
Idempotent: once applied, no block matches an old key and the dry run plans nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks  # noqa: E402

RAILROAD = Path.home() / "Dropbox/KiCad/Railroad"
SHEETS = (RAILROAD / "SPCoast/Corporal.kicad_sch", RAILROAD / "SPCoast/Corporal-Panel.kicad_sch")

# (lib_id, Reference, field, old) -> new.  The lookup uses the old text, so a block already renamed matches nothing,
# and the Reference keeps 831 -> 829 from being followed by 829 -> 827 on the same symbol.
MAP: dict[tuple[str, str, str, str], str] = {
    ("Railroad-Trackplan:Switch_Lock", "SW11829", "Value", "829"): "827",
    ("Railroad-Trackplan:Derail", "SW11900", "Value", "829D"): "827D",
    ("Railroad-Trackplan:Switch_Powered", "SW11831", "Value", "831"): "829",
    ("Railroad-Field:Device-Switch-OS", "DevSW11001", "Value", "829"): "827",
    ("Railroad-Field:Device-Switch-OS", "DevSW11002", "Value", "831"): "829",
    ("Railroad-Field:Local-Lock", "LK11001", "Value", "829"): "827",
    ("Railroad-Field:Local-Switch", "SW11902", "Value", "829"): "827",
    ("Railroad-Office:PanelLock", "LKL12011", "Value", "829"): "827",
    ("Railroad-Office:PanelSignal", "SGL12011", "Value", "830"): "828",
    ("Railroad-Office:PanelSignal", "SGL12012", "Value", "832"): "830",
    ("Railroad-Office:PanelSwitch", "SWL12012", "Value", "831"): "829",
    ("Railroad-Office:ModelLamp-YELLOW", "LMP12111", "Indication", "829T1K"): "827T1K",
    ("Railroad-Office:ModelLamp-RED", "LMP12112", "Indication", "831T1K"): "829T1K",
}
# Any literal that carries one of the numbers; a block with one that is not in MAP is reported, not changed.
WATCH = re.compile(r"^(829|829D|831|830|832)(T1K?|K|D)?$")
EXCLUDED = re.compile(r"^(828[NS]A|830[NS]AB|832[NS]A|83[234]T)$")  # masts and track circuits: by design
RENAMED = {(lib_id, ref, field, new) for (lib_id, ref, field, _), new in MAP.items()}  # a renamed block is not a stranger


# ---------------------------------------------------------------- text helpers (as 2026-11-12-value-is-the-literal.py)
def props_in(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def set_prop(block: str, name: str, value: str, depth: int) -> str:
    """Replace only the value text of one `(property "name" "..."` line; nothing else moves."""
    _, s, e = props_in(block, depth)[name]
    m = re.match(r'\(property "(?:[^"\\]|\\.)*" "', block[s:])
    vs = s + m.end()
    ve = block.index('"', vs)
    while block[ve - 1] == "\\":
        ve = block.index('"', ve + 1)
    return block[:vs] + value.replace("\\", "\\\\").replace('"', '\\"') + block[ve:]


def splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    out, pos = [], 0
    for s, e, new in sorted(edits):
        assert s >= pos, "overlapping edits"
        out += [text[pos:s], new]
        pos = e
    return "".join(out) + text[pos:]


def instances(text: str):
    for s, e in blocks(text, "symbol", 1):
        m = re.match(r'\(symbol\n\t\t\(lib_id "([^"]+)"', text[s:e])
        if m:
            yield s, e, m.group(1)


# ---------------------------------------------------------------- the edit
def run(apply: bool) -> int:
    locks = [p for p in RAILROAD.rglob("~*.lck") if "/Panels/" not in str(p) and "/.claude/" not in str(p)]
    if locks:
        sys.exit("KiCad holds a lock; close it first: " + ", ".join(str(p) for p in locks))
    rows: list[tuple] = []
    unmapped: list[tuple] = []
    totals: Counter = Counter()
    writes: dict[Path, str] = {}

    for sheet in SHEETS:
        sch = sheet.read_text()
        edits = []
        for s, e, lib_id in instances(sch):
            b = sch[s:e]
            pr = props_in(b, 2)
            ref = pr.get("Reference", ("?",))[0]
            unit = re.search(r"\n\t\t\(unit (\d+)\)", b)
            who = ref + (f" u{unit.group(1)}" if unit else "")
            hit = [(f, v) for f, (v, _, _) in pr.items() if (lib_id, ref, f, v) in MAP]
            if len(hit) > 1:
                sys.exit(f"{sheet.name} {who} {lib_id}: two mapped fields on one block {hit}")
            if hit:
                field, old = hit[0]
                new = MAP[(lib_id, ref, field, old)]
                edits.append((s, e, set_prop(b, field, new, 2)))
                rows.append((sheet.name, lib_id.split(":")[1], who, field, old, new))
                totals[(sheet.name, lib_id.split(":")[1], field, old, new)] += 1
            for f, (v, _, _) in pr.items():
                if WATCH.match(v) and (lib_id, ref, f, v) not in MAP and (lib_id, ref, f, v) not in RENAMED and not EXCLUDED.match(v):
                    unmapped.append((sheet.name, who, lib_id, f, v))
        if edits:
            writes[sheet] = splice(sch, edits)

    print(f"{'APPLY' if apply else 'DRY RUN'}: planned changes")
    for sheet, sym, who, field, old, new in rows:
        print(f"  {sheet:24s} {sym:22s} {who:14s} {field:10s} {old!r:10s} -> {new!r}")
    print("totals (blocks):")
    for (sheet, sym, field, old, new), n in sorted(totals.items()):
        print(f"  {sheet:24s} {sym:22s} {field:10s} {old!r:10s} -> {new!r:10s} x{n}")
    print(f"blocks {len(rows)}; files {len(writes)}")
    if unmapped:
        print("NOT CHANGED: literals carrying one of the numbers that are not in the map (masts and 83xT excluded by design):")
        for sheet, who, lib_id, f, v in unmapped:
            print(f"  {sheet} {who} {lib_id} {f}={v!r}")
    if apply:
        for path, text in writes.items():
            path.write_text(text)
        print(f"wrote {len(writes)} files")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    a = ap.parse_args(argv)
    return run(a.apply)


if __name__ == "__main__":
    sys.exit(main())
