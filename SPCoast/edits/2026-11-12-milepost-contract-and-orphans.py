#!/usr/bin/env python3
"""Railroad, 2026-11-12: a library symbol's field set is the contract; declare Milepost on the trackplan, drop orphans.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-milepost-contract-and-orphans.py           # dry run: table of planned changes
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-milepost-contract-and-orphans.py --apply   # write
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-milepost-contract-and-orphans.py --survey  # gate after

The owner (2026-11-12): a library symbol's field set is the contract for what a placed instance may state. The
importer reads `Milepost` on any symbol that states one (Subdivision tools/layout_compiler/seams.py, optional numeric
geographic context), so every symbol it may appear on must declare it; and an instance field its library symbol does
not declare is noise and is removed.

Part A, declare Milepost. In Railroad-Trackplan every top-level symbol whose Role is APPLIANCE, TRACK, POLICY or
STRUCTURE and which has no Milepost property yet gets one: empty text, hidden, in the form of House's existing block,
placed after the symbol's last property (in the parent symbol, not the unit sub-symbols). The same block goes into the
cached copy of each such symbol in every live sheet's lib_symbols (so ERC's lib_symbol_mismatch does not fire).
Placed instances are not touched by Part A: an instance without the field is fine, KiCad adds it on update.
Not touched: DEVICE, IODRIVER, ENCODER, PANEL and the other three libraries.

Part B, remove orphan instance fields. On every placed instance whose lib_id is in one of the four symbols/ libraries,
each `(property "X" ...)` block that the library symbol (as of Part A) does not declare is removed whole, textually.
Reference, Value, Footprint, Datasheet and Description are never orphans.

Edit, text only: a block is inserted after a property or cut with its leading newline and tabs; nothing is
re-serialised. Left alone: .history, Panels, Scratch, lib_ids not under symbols/.
Idempotent: a symbol that already declares Milepost is not touched; an instance with no orphan is not touched.
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
LIBDIR = RAILROAD / "symbols"
PROJECTS = (RAILROAD / "SPCoast", RAILROAD / "Tutorial")
LIBRARIES = ("Railroad-Trackplan", "Railroad-Office", "Railroad-Field", "Railroad-HardwareIO")

TRACKPLAN = "Railroad-Trackplan"
ROLES = {"APPLIANCE", "TRACK", "POLICY", "STRUCTURE"}
FIELD = "Milepost"
TEMPLATE_SYMBOL = "House"
STANDARD = {"Reference", "Value", "Footprint", "Datasheet", "Description"}


# ---------------------------------------------------------------- text helpers
def props_in(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    out, pos = [], 0
    for s, e, new in sorted(edits):
        assert s >= pos, "overlapping edits"
        out += [text[pos:s], new]
        pos = e
    return "".join(out) + text[pos:]


def top_symbols(text: str, depth: int) -> dict[str, tuple[int, int]]:
    out = {}
    for s, e in blocks(text, "symbol", depth):
        m = re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', text[s:e])
        if m:
            out[m.group(1)] = (s, e)
    return out


def instances(text: str):
    for s, e in blocks(text, "symbol", 1):
        m = re.match(r'\(symbol\n\t\t\(lib_id "([^"]+)"', text[s:e])
        if m:
            yield s, e, m.group(1)


def sheets() -> list[Path]:
    out = []
    for proj in PROJECTS:
        out += [p for p in sorted(proj.glob("*.kicad_sch"))]
    return out


def reindent(block: str, from_depth: int, to_depth: int) -> str:
    """A property block as text at one tab depth, rewritten at another (the first line carries no indent)."""
    d = to_depth - from_depth
    lines = block.split("\n")
    if d >= 0:
        return "\n".join([lines[0]] + ["\t" * d + ln for ln in lines[1:]])
    return "\n".join([lines[0]] + [ln[-d:] if ln.startswith("\t" * -d) else ln for ln in lines[1:]])


# ---------------------------------------------------------------- Part A
def milepost_template() -> str:
    """House's Milepost block in the library, at depth 2."""
    t = (LIBDIR / f"{TRACKPLAN}.kicad_sym").read_text()
    s, e = top_symbols(t, 1)[TEMPLATE_SYMBOL]
    _, ps, pe = props_in(t[s:e], 2)[FIELD]
    return t[s + ps:s + pe]


def target_symbols(libtext: str) -> list[str]:
    """Every top-level Trackplan symbol whose Role is one of ROLES, in file order."""
    out = []
    for name, (s, e) in top_symbols(libtext, 1).items():
        p = props_in(libtext[s:e], 2)
        if "Role" in p and p["Role"][0] in ROLES:
            out.append(name)
    return out


def plan_declare(block: str, depth: int, template: str) -> str | None:
    """Insert the Milepost block after the last property of a symbol definition. None when already declared."""
    p = props_in(block, depth)
    if FIELD in p:
        return None
    last_end = max(e for _, _, e in p.values())
    ins = "\n" + "\t" * depth + reindent(template, 2, depth)
    return block[:last_end] + ins + block[last_end:]


# ---------------------------------------------------------------- Part B
def declared_fields(after_part_a: set[str]) -> dict[str, set[str]]:
    """{lib_id: field names the library symbol declares}, with Milepost counted on the Part A targets."""
    out = {}
    for lib in LIBRARIES:
        t = (LIBDIR / f"{lib}.kicad_sym").read_text()
        for name, (s, e) in top_symbols(t, 1).items():
            names = set(props_in(t[s:e], 2))
            if lib == TRACKPLAN and name in after_part_a:
                names.add(FIELD)
            out[f"{lib}:{name}"] = names
    return out


def plan_orphans(block: str, declared: set[str]) -> tuple[str | None, list[str]]:
    """Cut every undeclared property block (with its leading newline and tabs) from a placed instance."""
    cuts = []
    gone = []
    for name, (_, s, e) in props_in(block, 2).items():
        if name in STANDARD or name in declared:
            continue
        assert block[s - 3:s] == "\n\t\t", f"unexpected layout before {name!r}"
        cuts.append((s - 3, e, ""))
        gone.append(name)
    if not cuts:
        return None, []
    return splice(block, cuts), gone


# ---------------------------------------------------------------- run
def lock_gate() -> None:
    locks = [p for p in RAILROAD.rglob("~*.lck") if "/Panels/" not in str(p) and "/.claude/" not in str(p)]
    if locks:
        sys.exit("KiCad holds a lock; close it first: " + ", ".join(str(p) for p in locks))


def run(apply: bool) -> int:
    lock_gate()
    rows: list[tuple] = []
    skips: list[tuple] = []
    totals = Counter()
    writes: dict[Path, str] = {}
    template = milepost_template()

    # A1. the library
    libpath = LIBDIR / f"{TRACKPLAN}.kicad_sym"
    libtext = libpath.read_text()
    targets = target_symbols(libtext)
    tops = top_symbols(libtext, 1)
    edits = []
    for name in targets:
        s, e = tops[name]
        new = plan_declare(libtext[s:e], 2, template)
        if new is None:
            skips.append((libpath.name, name, "", f"{FIELD} already declared"))
            continue
        edits.append((s, e, new)); rows.append(("library", libpath.name, name, "", f"+ {FIELD}")); totals["library"] += 1
    if edits:
        writes[libpath] = splice(libtext, edits)
    target_set = set(targets)
    declared = declared_fields(target_set)

    # A2 and B. the sheets: cached copies, then instances
    for p in sheets():
        sch = p.read_text(); edits = []
        (ls, le), = blocks(sch, "lib_symbols", 1)
        for cname, (s, e) in top_symbols(sch[ls:le], 2).items():
            lib, _, name = cname.partition(":")
            if lib != TRACKPLAN or name not in target_set:
                continue
            new = plan_declare(sch[ls + s:ls + e], 3, template)
            if new is None:
                continue
            edits.append((ls + s, ls + e, new)); rows.append(("cache", p.name, cname, "", f"+ {FIELD}")); totals["cache"] += 1
        for s, e, lib_id in instances(sch):
            if lib_id not in declared:
                if lib_id.split(":")[0] in LIBRARIES:
                    skips.append((p.name, "", lib_id, "lib_id not in its library"))
                continue
            b = sch[s:e]
            new, gone = plan_orphans(b, declared[lib_id])
            if new is None:
                continue
            pr = props_in(b, 2)
            ref = pr.get("Reference", ("?",))[0]
            unit = re.search(r"\n\t\t\(unit (\d+)\)", b)
            who = f"{ref}" + (f" u{unit.group(1)}" if unit else "")
            edits.append((s, e, new))
            rows.append(("orphan", p.name, who, lib_id.split(":")[1], "- " + ", ".join(gone)))
            totals["orphan blocks"] += len(gone); totals[f"orphan blocks {p.name}"] += len(gone)
        if edits:
            writes[p] = splice(sch, edits)

    # report
    print(f"{'APPLY' if apply else 'DRY RUN'}: planned changes")
    w = max((len(r[1]) for r in rows), default=10)
    for kind, where, who, sym, what in rows:
        print(f"  {kind:8s} {where:{w}s} {who:14s} {sym:28s} {what}")
    print("totals: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + f"; files {len(writes)}")
    if skips:
        print("skipped / not applicable:")
        for where, who, sym, why in skips:
            print(f"  {where} {who} {sym}: {why}")
    if apply:
        for path, text in writes.items():
            path.write_text(text)
        print(f"wrote {len(writes)} files")
    return 0


# ---------------------------------------------------------------- gate
def survey() -> int:
    """Every Role-qualified Trackplan symbol declares Milepost hidden, in the library and in every cached copy;
    no placed instance of a symbols/ library states a field its library symbol does not declare."""
    fails = []; counts = Counter()
    libtext = (LIBDIR / f"{TRACKPLAN}.kicad_sym").read_text()
    targets = set(target_symbols(libtext))
    tops = top_symbols(libtext, 1)
    for name in sorted(targets):
        s, e = tops[name]; p = props_in(libtext[s:e], 2)
        if FIELD not in p:
            fails.append(f"library {TRACKPLAN}:{name}: no {FIELD}")
        elif "(hide yes)" not in libtext[s + p[FIELD][1]:s + p[FIELD][2]]:
            fails.append(f"library {TRACKPLAN}:{name}: {FIELD} not hidden")
        counts["library"] += 1
    declared = declared_fields(set())  # the library as it is on disk, no allowance
    for sh in sheets():
        sch = sh.read_text()
        (ls, le), = blocks(sch, "lib_symbols", 1)
        for cname, (s, e) in top_symbols(sch[ls:le], 2).items():
            lib, _, name = cname.partition(":")
            if lib != TRACKPLAN or name not in targets:
                continue
            p = props_in(sch[ls + s:ls + e], 3)
            if FIELD not in p:
                fails.append(f"cache {sh.name} {cname}: no {FIELD}")
            elif "(hide yes)" not in sch[ls + s + p[FIELD][1]:ls + s + p[FIELD][2]]:
                fails.append(f"cache {sh.name} {cname}: {FIELD} not hidden")
            counts["cache"] += 1
        for s, e, lib_id in instances(sch):
            if lib_id not in declared:
                continue
            p = props_in(sch[s:e], 2)
            ref = p.get("Reference", ("?",))[0]
            for name in p:
                if name not in STANDARD and name not in declared[lib_id]:
                    fails.append(f"instance {sh.name} {ref} {lib_id}: orphan field {name!r}")
            counts["instance"] += 1
    print("survey: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for f in fails:
        print("FAIL", f)
    print("gate", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    ap.add_argument("--survey", action="store_true", help="gate: check the target form everywhere")
    a = ap.parse_args(argv)
    if a.survey:
        return survey()
    return run(a.apply)


if __name__ == "__main__":
    sys.exit(main())
