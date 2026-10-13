#!/usr/bin/env python3
"""One-off, 2026-10-12: move every SPCoast sheet from the InterlockingPlant libraries to the four
Railroad libraries (checkpoint step 6, the mechanical half).

    python3 SPCoast/edits/2026-10-12-migrate-libraries.py [--dry-run] [--heads CL|CPL]

Per sheet, by text edits that keep untouched bytes:
- every instance's lib_id is remapped by MAP (nickname and, where the recipe renamed it, symbol);
- the embedded lib_symbols definition is replaced by the library's current block;
- instance properties are synced to the library symbol: missing fields added (hidden, with the
  library's value), empty fields filled from the library, Description refreshed, `Indications`
  renamed `IndicationCeiling`, retired fields removed (Kind, ControlToken, Vital, NormalIs, Chain,
  Index, and any field not on the new symbol whose value is empty); a non-empty field the new
  symbol does not declare is kept and reported;
- an instance of a symbol that is now multi-unit is completed: its pin list is pruned to unit 1
  and one copy per further unit is added at the same position with a fresh uuid, so the units
  mesh into the old picture and the old wires land on the old pin positions. The netlist gate
  (tools/contract/netlist_diff.py against production/pre-migration.net) reports what did not.
Retired symbols (AUXILIARY_TRAFFIC) and unknown lib_ids are left alone and reported.
KiCad must be closed (no ~*.lck in SPCoast/).
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks, end_of, library_symbols  # noqa: E402

RAILROAD = Path.home() / "Dropbox/KiCad/Railroad"
SPCOAST = RAILROAD / "SPCoast"
LIBDIR = RAILROAD / "symbols"
LIBRARIES = ("Railroad-Trackplan", "Railroad-Office", "Railroad-Field", "Railroad-HardwareIO")
STANDARD = {"Reference", "Value", "Footprint", "Datasheet"}
RETIRED = {"Kind", "ControlToken", "Vital", "NormalIs", "Chain", "Index"}
RENAMED = {"Indications": "IndicationCeiling"}

PLANT_EXCEPTIONS = {"Switch_Powered_Derail": "Railroad-Trackplan:Derail",
                    "Virtual Indication": "Railroad-Trackplan:Track Circuit_Virtual",
                    "AUXILIARY_TRAFFIC": None}
FIELD = {"Device-Detector-Optical": "Railroad-Field:Device-TrackCircuit-Optical",
         "Device-Head-3LED-Mux2": "Railroad-Field:Device-Head-CPL-Encoder",
         "Device-Head-3LED-PWM": "Railroad-Field:Device-Head-CPL",
         "Device-Head-Semaphore-Servo": "Railroad-Field:Device-Head-Semaphore-UQ",
         "Device-Lamp-Bit": "Railroad-Field:Device-Lamp",
         "Device-Lamp-NeoPixel": "Railroad-Field:Device-Lamp",
         "Device-Switch-Sense": "Railroad-Field:Device-Switch-ManualSensed",
         "Device-Switch-StallMotor-Sensed-OS": "Railroad-Field:Device-Switch-OS",
         "Driver-I2C-MCP23017": "Railroad-HardwareIO:Driver-I2C-MCP23017",
         "Driver-I2C-PCA9685": "Railroad-HardwareIO:Driver-I2C-PCA9685-PWM",
         "Local-Lock": "Railroad-Field:Local-Lock",
         "Local-Switch": "Railroad-Field:Local-Switch"}
OFFICE_EXCEPTIONS = {"Driver-I2C-MAX7313": "Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc"}


def target(lib_id: str, heads: str) -> str | None | str:
    lib, _, name = lib_id.partition(":")
    if lib == "Railroad":
        if name == "Signal Head - CL":
            return f"Railroad-Trackplan:Signal Head - {heads}"
        return PLANT_EXCEPTIONS.get(name, f"Railroad-Trackplan:{name}")
    if lib == "RailroadPanel":
        return OFFICE_EXCEPTIONS.get(name, f"Railroad-Office:{name}")
    if lib == "RailroadField":
        return FIELD.get(name, "?")
    return "?"


def symbol_blocks(text: str) -> dict[str, str]:
    out = {}
    for s, e in blocks(text, "symbol", 1):
        out[re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', text[s:e]).group(1)] = text[s:e]
    return out


def props_of(block: str, depth: int) -> dict[str, tuple[str, int, int]]:
    """{name: (value, start, end)} of the property blocks at the given tab depth."""
    out = {}
    for s, e in blocks(block, "property", depth):
        m = re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', block[s:e])
        out[m.group(1)] = (m.group(2), s, e)
    return out


def set_value(block: str, s: int, value: str) -> str:
    m = re.match(r'\(property "(?:[^"\\]|\\.)*" "', block[s:])
    vs = s + m.end(); ve = block.index('"', vs)
    while block[ve - 1] == "\\":
        ve = block.index('"', ve + 1)
    return block[:vs] + value + block[ve:]


def new_property(name: str, value: str, at: str) -> str:
    return (f'\n\t\t(property "{name}" "{value}"\n\t\t\t(at {at} 0)\n\t\t\t(hide yes)\n\t\t\t(show_name no)'
            f'\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)')


class Migration:
    def __init__(self, heads: str):
        self.heads = heads
        self.lib_blocks: dict[str, str] = {}
        self.lib_syms: dict[str, dict] = {}
        for lib in LIBRARIES:
            text = (LIBDIR / f"{lib}.kicad_sym").read_text()
            for name, b in symbol_blocks(text).items():
                self.lib_blocks[f"{lib}:{name}"] = b
            for name, s in library_symbols(text).items():
                self.lib_syms[f"{lib}:{name}"] = s
        self.report: list[str] = []
        self.counts: Counter = Counter()

    def unit_pins(self, lib_id: str) -> dict[int, set[str]]:
        s = self.lib_syms[lib_id]
        number = defaultdict(list)
        for n, num, _ in s["pins"]:
            number[n].append(num)
        out = {}
        for u, names in s["units"].items():
            if names:
                out[u] = {num for n in names for num in number[n]}
        return out

    def sync_properties(self, b: str, lib_id: str, ref: str, sheet: str) -> str:
        lib = props_of(self.lib_blocks[lib_id], 2)
        at = re.search(r"\n\t\t\(at ([-\d.]+ [-\d.]+)", b).group(1)
        edits = []
        inst = props_of(b, 2)
        renames = dict(RENAMED)
        lower = {k.lower(): k for k in lib}
        for name in inst:
            if name not in lib and name.lower() in lower and lower[name.lower()] != name:
                renames[name] = lower[name.lower()]          # Hold_ms -> hold_ms: the setting kept its value
        if "Index" in inst and inst["Index"][0] and "Address" in lib and inst.get("Address", ("",))[0] == "":
            renames["Index"] = "Address"                     # a pixel's chain slot is its Address (E30)
        for old, new in renames.items():
            if old in inst and new not in inst:
                v, s, e = inst[old]
                b = b[:s] + b[s:e].replace(f'(property "{old}" ', f'(property "{new}" ', 1) + b[e:]
                inst = props_of(b, 2)
            elif old in inst and new in inst and inst[new][0] == "" and inst[old][0]:
                b = set_value(b, inst[new][1], inst[old][0])
                inst = props_of(b, 2)
        for name, (v, s, e) in sorted(inst.items(), key=lambda kv: -kv[1][1]):
            if name in STANDARD or name == "Description":
                continue
            if name not in lib:
                if name in RETIRED or v == "":
                    b = b[:s - 3] + b[e:]
                    if v and name not in RETIRED:
                        pass
                    if v:
                        self.report.append(f"{sheet} {ref}: dropped {name}={v!r} ({lib_id})")
                else:
                    self.report.append(f"{sheet} {ref}: kept {name}={v!r}, not on {lib_id}")
        inst = props_of(b, 2)
        for name, (lv, _, _) in lib.items():
            if name in STANDARD:
                continue
            if name in inst:
                iv, s, e = inst[name]
                if name == "Description" or (iv == "" and lv != ""):
                    b = set_value(b, s, lv)
                    inst = props_of(b, 2)
            else:
                last = max(e for _, _, e in inst.values())
                b = b[:last] + new_property(name, lv, at) + b[last:]
                inst = props_of(b, 2)
        return b

    def complete_units(self, b: str, lib_id: str, ref: str, sheet: str, present: set[int]) -> str:
        """Add the units of a now multi-unit symbol that the sheet does not place yet (a chip drawn
        as four units already has them; a plate drawn as one symbol has only unit 1)."""
        units = {u: p for u, p in self.unit_pins(lib_id).items() if u not in present or u == 1}
        if len(units) < 2:
            return b
        if not re.search(r"\n\t\t\(unit 1\)", b):
            return b
        def prune(block: str, keep: set[str], fresh: bool) -> str:
            spans = []
            for s, e in blocks(block, "pin", 2):
                num = re.match(r'\(pin "([^"]*)"', block[s:e]).group(1)
                if num not in keep:
                    spans.append((s - 3, e, ""))
                elif fresh:
                    spans.append((s, e, re.sub(r'\(uuid "[^"]*"\)', f'(uuid "{uuid.uuid4()}")', block[s:e])))
            for s, e, new in sorted(spans, reverse=True):
                block = block[:s] + new + block[e:]
            return block
        ordered = sorted(units)
        first = prune(b, units[ordered[0]], False)
        copies = []
        for u in ordered[1:]:
            c = prune(b, units[u], True)
            c = re.sub(r"\n\t\t\(unit 1\)", f"\n\t\t(unit {u})", c, count=1)
            c = re.sub(r"\n\t\t\t\t\t\(unit 1\)", f"\n\t\t\t\t\t(unit {u})", c)
            c = re.sub(r'\n\t\t\(uuid "[^"]*"\)', f'\n\t\t(uuid "{uuid.uuid4()}")', c, count=1)
            copies.append(c)
        self.counts["units added"] += len(copies)
        self.report.append(f"{sheet} {ref}: units {', '.join(str(u) for u in ordered[1:])} added at the same place ({lib_id})")
        return first + "".join("\n\t" + c for c in copies)

    def migrate_sheet(self, path: Path, dry: bool) -> None:
        sheet = path.stem
        t = path.read_text()
        # 1. embedded library definitions
        ls, le = next(blocks(t, "lib_symbols", 1))
        section = t[ls:le]
        edits, seen = [], set()
        for s, e in blocks(section, "symbol", 2):
            old = re.match(r'\(symbol "((?:[^"\\]|\\.)*)"', section[s:e]).group(1)
            new = target(old, self.heads)
            if new in (None, "?"):
                continue
            if new in seen:
                edits.append((s - 3, e, ""))
                continue
            seen.add(new)
            lib_block = self.lib_blocks[new]
            name = new.partition(":")[2]
            body = lib_block.replace(f'(symbol "{name}"', f'(symbol "{new}"', 1).replace("\n", "\n\t")
            edits.append((s, e, body))
        for s, e, new in sorted(edits, reverse=True):
            section = section[:s] + new + section[e:]
        t = t[:ls] + section + t[le:]
        # 2. instances
        placed: dict[str, set[int]] = defaultdict(set)
        for s, e in blocks(t, "symbol", 1):
            b = t[s:e]
            ref = re.search(r'\(property "Reference" "([^"]*)"', b).group(1)
            placed[ref].add(int(re.search(r"\n\t\t\(unit (\d+)\)", b).group(1)))
        out, pos = [], 0
        for s, e in blocks(t, "symbol", 1):
            b = t[s:e]
            m = re.search(r'\n\t\t\(lib_id "((?:[^"\\]|\\.)*)"\)', b)
            old = m.group(1)
            ref = re.search(r'\(property "Reference" "([^"]*)"', b).group(1)
            new = target(old, self.heads)
            if new is None:
                self.report.append(f"{sheet} {ref}: {old} is retired; delete by hand")
                self.counts["retired, left"] += 1
                continue
            if new == "?" or new not in self.lib_blocks:
                self.report.append(f"{sheet} {ref}: {old} has no target ({new}); left")
                self.counts["unmapped, left"] += 1
                continue
            nb = b[:m.start(1)] + new + b[m.end(1):]
            nb = self.sync_properties(nb, new, ref, sheet)
            nb = self.complete_units(nb, new, ref, sheet, placed[ref])
            self.counts[f"{old} -> {new}"] += 1
            out.append((s, e, nb))
        for s, e, nb in sorted(out, reverse=True):
            t = t[:s] + nb + t[e:]
        if not dry:
            path.write_text(t)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--heads", default="CPL", choices=("CL", "CPL"), help="Style for every plant head drawn as Signal Head - CL")
    a = ap.parse_args(argv)
    if any(SPCOAST.glob("~*.lck")) and not a.dry_run:
        print("KiCad has the project open (lock files present); close it first", file=sys.stderr)
        return 1
    m = Migration(a.heads)
    for lib_id in list(FIELD.values()) + list(OFFICE_EXCEPTIONS.values()) + [v for v in PLANT_EXCEPTIONS.values() if v]:
        assert lib_id in m.lib_blocks, lib_id
    for path in sorted(SPCOAST.glob("*.kicad_sch")):
        m.migrate_sheet(path, a.dry_run)
    print("== instances")
    for k, v in sorted(m.counts.items()):
        print(f"{v:4}  {k}")
    print("== notes")
    for line in m.report:
        print("  " + line)
    print("(dry run, nothing written)" if a.dry_run else "written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
