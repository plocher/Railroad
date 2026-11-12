#!/usr/bin/env python3
"""Railroad, 2026-11-12: Value is the literal; the key field derives from it as ${Value}, never the reverse.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-value-is-the-literal.py           # dry run: table of planned changes
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-value-is-the-literal.py --apply   # write
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-11-12-value-is-the-literal.py --survey  # gate after

The owner (2026-11-12): on every library symbol and placed instance, Value is the user-editable literal and the
key-bearing field is the macro `${Value}`. KiCad's "Update Symbols from Library" with field reset overwrites every
field except Reference and Value from the library, so a literal kept in any other field is lost, and a macro in
Value becomes circular once the library field says `${Value}`.

Symbols and their key field:
  Railroad-HardwareIO  Driver-I2C-MAX7311, -MAX7313, -MAX7313-SPCoastcTc, -PCA9685-PWM, -PCA9685-Servo, -MCP23017: Address
                       Driver-CMRInet-IB, -OB: Bit;  Driver-CMRInet-Node: Address
  Railroad-Trackplan   House: CP Name

Edit, text only on the `(property "X" "..."` lines, never a re-serialisation:
  library symbol:  Value "" ; key "${Value}"
  cached copy:     the same, in every sheet's lib_symbols (so ERC's lib_symbol_mismatch does not fire)
  placed instance: Value <- the literal in the key field; key <- "${Value}".  A Value of the form IN.${Bit},
                   OUT.${Bit}, UA${Address}, CP ${CP Name} loses its prefix: the model key does not change.
                   Every unit block of a multi-unit symbol carries its own properties and is changed.
Left alone: ${TITLE} (Interlocking, Processor), ${Style}/${Kind} (anonymous heads, Encoder-RYG), Scratch sheets,
.history, Panels, lib_ids not under symbols/.
Idempotent: an instance whose key is already "${Value}" and whose Value holds no macro is not touched.
A conflict (literal Value differing from a literal key, a macro that names another field) is reported and skipped.
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

TARGETS = {  # lib_id: key field
    "Railroad-HardwareIO:Driver-I2C-MAX7311": "Address",
    "Railroad-HardwareIO:Driver-I2C-MAX7313": "Address",
    "Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc": "Address",
    "Railroad-HardwareIO:Driver-I2C-PCA9685-PWM": "Address",
    "Railroad-HardwareIO:Driver-I2C-PCA9685-Servo": "Address",
    "Railroad-HardwareIO:Driver-I2C-MCP23017": "Address",
    "Railroad-HardwareIO:Driver-CMRInet-IB": "Bit",
    "Railroad-HardwareIO:Driver-CMRInet-OB": "Bit",
    "Railroad-HardwareIO:Driver-CMRInet-Node": "Address",
    "Railroad-Trackplan:House": "CP Name",
}
MACRO = re.compile(r"\$\{([^}]*)\}")


# ---------------------------------------------------------------- text helpers
def props_in(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def find_prop(props: dict, name: str):
    """KiCad resolves ${field} case-insensitively; so do we. Returns (actual name, (value, s, e)) or None."""
    for k, v in props.items():
        if k.lower() == name.lower():
            return k, v
    return None


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


# ---------------------------------------------------------------- the two edits
def plan_definition(block: str, depth: int, key: str) -> tuple[str, list[str]] | None:
    """A library symbol or a cached copy: Value "" and key "${Value}". None when already so."""
    p = props_in(block, depth)
    notes = []
    val = p["Value"][0]
    hit = find_prop(p, key)
    if hit is None:
        return None, [f"no {key} field"]
    kname, (kval, _, _) = hit
    if val == "" and kval == "${Value}":
        return None, []
    new = block
    if val != "":
        new = set_prop(new, "Value", "", depth); notes.append(f"Value {val!r} -> ''")
    if kval != "${Value}":
        new = set_prop(new, kname, "${Value}", depth); notes.append(f"{kname} {kval!r} -> '${{Value}}'")
    return new, notes


def plan_instance(block: str, key: str) -> tuple[str | None, str, str, str, str, str]:
    """A placed unit block. Returns (new block or None, value before, value after, key before, key after, note)."""
    p = props_in(block, 2)
    val = p["Value"][0]
    hit = find_prop(p, key)
    if hit is None:
        return None, val, val, "", "", f"SKIP: no {key} field on the instance"
    kname, (kval, _, _) = hit
    macros = MACRO.findall(val)
    if not macros and kval == "${Value}":
        return None, val, val, kval, kval, ""           # already in the target form
    if macros:
        others = [m for m in macros if m.lower() != key.lower()]
        if others:
            return None, val, val, kval, kval, f"SKIP: Value names other fields {others}"
        if MACRO.search(kval):
            return None, val, val, kval, kval, f"SKIP: {kname} is itself a macro {kval!r}"
        literal = kval
        prefix = MACRO.sub("", val)
        note = f"prefix {prefix!r} lost" if prefix else ""
        if literal == "":
            note = (note + "; " if note else "") + f"{kname} was empty: Value becomes ''"
    else:
        # literal Value and literal key: they must agree for the key to stay the same
        if kval == val:
            literal = val; note = f"{kname} == Value already"
        elif kval == "":
            return None, val, val, kval, kval, f"SKIP: {kname} empty but Value literal {val!r}; key would change"
        else:
            return None, val, val, kval, kval, f"SKIP: conflict {kname} {kval!r} != Value {val!r}"
    new = set_prop(block, "Value", literal, 2)
    new = set_prop(new, kname, "${Value}", 2)
    return new, val, literal, kval, "${Value}", note


def run(apply: bool) -> int:
    if list(RAILROAD.rglob("~*.lck")):
        locks = [p for p in RAILROAD.rglob("~*.lck") if "/Panels/" not in str(p) and "/.claude/" not in str(p)]
        if locks:
            sys.exit("KiCad holds a lock; close it first: " + ", ".join(str(p) for p in locks))
    rows: list[tuple] = []
    skips: list[tuple] = []
    totals = Counter()
    writes: dict[Path, str] = {}

    # 1. the library symbols
    by_lib: dict[str, list[str]] = {}
    for lib_id, key in TARGETS.items():
        lib, name = lib_id.split(":")
        by_lib.setdefault(lib, []).append(name)
    lib_text: dict[str, str] = {}
    for lib, names in by_lib.items():
        path = LIBDIR / f"{lib}.kicad_sym"; t = path.read_text()
        tops = top_symbols(t, 1); edits = []
        for name in names:
            if name not in tops:
                skips.append((path.name, name, "", "symbol not in library")); continue
            s, e = tops[name]
            new, notes = plan_definition(t[s:e], 2, TARGETS[f"{lib}:{name}"])
            if new is None:
                if notes:
                    skips.append((path.name, name, "", notes[0]))
                continue
            edits.append((s, e, new)); rows.append(("library", path.name, name, "", "; ".join(notes))); totals["library"] += 1
        if edits:
            t = splice(t, edits); writes[path] = t
        lib_text[lib] = t

    # 2. the sheets: cached copies, then instances
    for p in sheets():
        sch = p.read_text(); edits = []
        (ls, le), = blocks(sch, "lib_symbols", 1)
        for cname, (s, e) in top_symbols(sch[ls:le], 2).items():
            if cname not in TARGETS:
                continue
            new, notes = plan_definition(sch[ls + s:ls + e], 3, TARGETS[cname])
            if new is None:
                continue
            edits.append((ls + s, ls + e, new)); rows.append(("cache", p.name, cname, "", "; ".join(notes))); totals["cache"] += 1
        for s, e, lib_id in instances(sch):
            if lib_id not in TARGETS:
                continue
            b = sch[s:e]
            pr = props_in(b, 2)
            ref = pr.get("Reference", ("?",))[0]
            unit = re.search(r"\n\t\t\(unit (\d+)\)", b)
            who = f"{ref}" + (f" u{unit.group(1)}" if unit else "")
            new, v0, v1, k0, k1, note = plan_instance(b, TARGETS[lib_id])
            if new is None:
                if note:
                    skips.append((p.name, who, lib_id, note))
                continue
            edits.append((s, e, new))
            rows.append(("instance", p.name, who, lib_id.split(":")[1], f"Value {v0!r} -> {v1!r}; {TARGETS[lib_id]} {k0!r} -> {k1!r}" + (f"  ({note})" if note else "")))
            totals["instance"] += 1
            if note.startswith("prefix"):
                totals["prefix lost"] += 1
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
    """Every target: library Value "" and key "${Value}"; each cached copy the same; no instance has a macro in
    Value and every instance key is exactly "${Value}"."""
    fails = []; counts = Counter()
    for lib_id, key in TARGETS.items():
        lib, name = lib_id.split(":")
        t = (LIBDIR / f"{lib}.kicad_sym").read_text()
        s, e = top_symbols(t, 1)[name]; p = props_in(t[s:e], 2)
        kv = find_prop(p, key)
        if p["Value"][0] != "" or kv is None or kv[1][0] != "${Value}":
            fails.append(f"library {lib_id}: Value {p['Value'][0]!r}, {key} {kv and kv[1][0]!r}")
        counts["library"] += 1
    for sh in sheets():
        sch = sh.read_text()
        (ls, le), = blocks(sch, "lib_symbols", 1)
        for cname, (s, e) in top_symbols(sch[ls:le], 2).items():
            if cname in TARGETS:
                p = props_in(sch[ls + s:ls + e], 3); kv = find_prop(p, TARGETS[cname])
                if p["Value"][0] != "" or kv is None or kv[1][0] != "${Value}":
                    fails.append(f"cache {sh.name} {cname}: Value {p['Value'][0]!r}, {TARGETS[cname]} {kv and kv[1][0]!r}")
                counts["cache"] += 1
        for s, e, lib_id in instances(sch):
            if lib_id not in TARGETS:
                continue
            p = props_in(sch[s:e], 2); val = p["Value"][0]; kv = find_prop(p, TARGETS[lib_id])
            ref = p.get("Reference", ("?",))[0]
            if MACRO.search(val):
                fails.append(f"instance {sh.name} {ref} {lib_id}: macro in Value {val!r}")
            if kv is None or kv[1][0] != "${Value}":
                fails.append(f"instance {sh.name} {ref} {lib_id}: {TARGETS[lib_id]} is {kv and kv[1][0]!r}")
            counts["instance"] += 1; counts[f"instance {lib_id.split(':')[1]}"] += 1
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
