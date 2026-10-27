#!/usr/bin/env python3
"""Field I/O, 2026-10-21: appliances and local MCP23017 I/O on Watsonville, Corporal, Christopher and Luchessa, in Sargent's forms.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-field-io.py [--dry-run]
    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-field-io.py --check after.net

Owner's instruction (2026-10-21): the actual appliances and local hardware I/O on the remaining interlockings,
following Sargent's forms, MCP23017 digital I/O only (no PWM, servos or pixels). Prepopulate; tidy by hand.

Sargent's forms, read from its sheet and netlist: a device is placed so that its pins land exactly on the expander's
pins, no wires. Per trackplan appliance:
- powered switch, or a lock switch: Device-Switch-OS <n> (M, ~N, ~R, ~OCC on four consecutive pins); a lock switch
  also gets Local-Lock <n> (~WLK, ~WLQK, ~WLQ) and Local-Switch <n> (~NWK, ~RWK, ~RWS, ~NWS), style "powered, lock, dual";
- manually sensed switch: Device-Switch <n> (M, ~N, ~R);
- mast <n><dir><heads>: Mast <n><dir><heads> plus one Cast-Head-CPL-Encoded per head letter (S0, S1), the casts' IND
  pins wired to the mast's IND pin;
- track circuit (not virtual, not another plant's): Device-TrackCircuit-Optical <name> (~OCC);
- maintainer call: Device-Lamp <name> (~LAMP), unless the sheet already has that lamp.
Dependent derails have no device (AGENTS.md). The expander's 16 pins are one 2.54 mm column; devices never straddle
two expanders. Expanders are MCP23017 at 0x20, 0x21, ... per sheet, four units stacked as on Sargent, each with an
IOBus label on its bus pin, in a grid of columns and rows that avoids what the sheet already holds.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(es)
cc, blocks = es.cc, es.blocks
SPCOAST, LIBDIR, HWIO = es.SPCOAST, es.LIBDIR, es.HWIO
FIELD = "Railroad-Field"
SHEETS = {"Watsonville": 15, "Corporal": 11, "Christopher": 9, "Luchessa": 7}       # reference numbering base
MAST_COLUMNS = (50.8, 106.68, 157.48, 208.28)              # a chip that carries masts needs the mast column to its left
PLAIN_COLUMNS = (106.68, 157.48, 208.28, 259.08)           # chips without masts: device column only
ROW_MIN, ROW_MAX, CHIP_PITCH = 10.16, 172.72, 44.45       # rows searched per column; a chip is 40.64 tall
BOTTOM_BAND = 100.33                                       # rows below the trackplans are tried before the top band
TITLE_BLOCK = (175.0, 195.0)                               # bottom-right of a USLetter sheet: nothing placed past it
UNIT_STEP, PIN_STEP = 10.16, 2.54
REGION_MAST = (-45.72, -5.08, 17.78, 40.64)     # around a chip's (x, y): mast column, device column, chip, its four units
REGION_PLAIN = (-24.13, -5.08, 17.78, 40.64)    # device column, chip, its four units
PIN_NUMBERS = {"Device-Switch-OS": 4, "Device-Switch": 3, "Local-Lock": 3, "Local-Switch": 4,
               "Device-TrackCircuit-Optical": 1, "Device-Lamp": 1, "Mast": 1, "Cast-Head-CPL-Encoded": 3}
UNITS = {"Device-Switch-OS": 3, "Device-Switch": 2, "Local-Lock": 2, "Local-Switch": 2}
# (symbol, slots, x offset from the chip column, y offset from the top slot)
FORM = {"Device-Switch-OS": (4, 0, 3.81), "Device-Switch": (3, 0, 2.54), "Local-Lock": (3, -7.62, 2.54),
        "Local-Switch": (4, -7.62, 2.54), "Cast-Head-CPL-Encoded": (2, 0, 1.27),
        "Device-TrackCircuit-Optical": (1, -10.16, 0), "Device-Lamp": (1, 0, 0)}
MAST_DX, CAST_IND_DX = -24.13, -24.13


# ---------------------------------------------------------------- the inventory
def inventory(text: str) -> dict:
    inv = {"switches": set(), "locks": set(), "manual": set(), "masts": set(), "circuits": set(), "calls": set(), "lamps": set()}
    for s, e, lib_id in es.instances(text):
        lib, name = lib_id.split(":")
        p = {k: v for k, (v, _, _) in cc.props_in(text[s:e], 2).items()}
        value = p.get("Value", "")
        if lib == "Railroad-Trackplan":
            if name.startswith("Switch_Powered"):
                inv["switches"].add(value)
            elif name == "Switch_Lock":
                inv["switches"].add(value); inv["locks"].add(value)
            elif name == "Switch_Manual_Sensed":
                inv["manual"].add(value)
            elif name.startswith("Mast_"):
                inv["masts"].add(value)
            elif name.startswith("Track Circuit") and "Virtual" not in name and ":" not in value:
                inv["circuits"].add(value)
            elif name == "MaintainerCall":
                inv["calls"].add(value)
        elif lib == FIELD and name == "Device-Lamp":
            inv["lamps"].add(value)
    return inv


def head_letters(mast: str) -> str:
    m = re.match(r"^\d+[NSEW]([A-Z]+)$", mast)
    assert m, mast
    return m.group(1)


def devices_for(inv: dict) -> list[dict]:
    """Devices in placement order; a mast's casts are one group so they stay on one expander."""
    out = []
    for mast in sorted(inv["masts"]):
        out.append(dict(kind="mast", value=mast, heads=head_letters(mast)))
    for sw in sorted(inv["switches"], key=lambda v: (len(v), v)):
        if sw in inv["locks"]:
            out.append(dict(kind="Local-Lock", value=sw))
            out.append(dict(kind="Local-Switch", value=sw))
        out.append(dict(kind="Device-Switch-OS", value=sw, style="powered, lock, dual" if sw in inv["locks"] else "powered"))
    for sw in sorted(inv["manual"], key=lambda v: (len(v), v)):
        out.append(dict(kind="Device-Switch", value=sw))
    for tc in sorted(inv["circuits"], key=lambda v: (len(v), v)):
        out.append(dict(kind="Device-TrackCircuit-Optical", value=tc))
    for mc in sorted(inv["calls"]):
        if not any(l.startswith(mc) for l in inv["lamps"]):
            out.append(dict(kind="Device-Lamp", value=mc))
    return out


def slots_of(dev: dict) -> int:
    return 2 * len(dev["heads"]) if dev["kind"] == "mast" else FORM[dev["kind"]][0]


# ---------------------------------------------------------------- placement
def points_of(text: str) -> list[tuple[float, float]]:
    """Every coordinate the sheet already uses, plus the corners of its sheet boxes."""
    pts = []
    for head in ("symbol", "wire", "label", "text", "global_label", "hierarchical_label", "junction", "no_connect", "bus"):
        for s, e in blocks(text, head, 1):
            b = text[s:e]
            if head == "symbol":
                m = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)", b)
                pts.append((float(m.group(1)), float(m.group(2))))
            else:
                pts += [(float(a), float(b_)) for a, b_ in re.findall(r"\((?:at|xy) ([-\d.]+) ([-\d.]+)", b)]
    for s, e in blocks(text, "sheet", 1):
        b = text[s:e]
        x, y = map(float, re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)\)", b).groups())
        w, h = map(float, re.search(r"\n\t\t\(size ([-\d.]+) ([-\d.]+)\)", b).groups())
        pts += [(x, y), (x + w, y), (x, y + h), (x + w, y + h), (x + w / 2, y + h / 2)]
    return pts


def rect(x, y, region):
    x1, y1, x2, y2 = region
    return (x + x1 - 1.27, y + y1 - 1.27, x + x2 + 1.27, y + y2 + 1.27)


def free(pts, taken, x, y, region) -> bool:
    ax1, ay1, ax2, ay2 = rect(x, y, region)
    if any(ax1 <= px <= ax2 and ay1 <= py <= ay2 for px, py in pts):
        return False
    return not any(ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2 for bx1, by1, bx2, by2 in taken)


def allocate(text: str, chips: list[list[dict]]) -> list[tuple[float, float] | None]:
    """A position per chip, in order; None when the sheet has no room left. Mast chips take the mast column."""
    pts, taken, out = points_of(text), [], []
    for chip in chips:
        has_mast = any(d["kind"] == "mast" for d in chip)
        region = REGION_MAST if has_mast else REGION_PLAIN
        columns = MAST_COLUMNS if has_mast else PLAIN_COLUMNS
        spot = None
        rows = [round(ROW_MIN + PIN_STEP * i, 3) for i in range(int((ROW_MAX - ROW_MIN) / PIN_STEP) + 1)]
        for y in [r for r in rows if r >= BOTTOM_BAND] + [r for r in rows if r < BOTTOM_BAND]:   # below the trackplan first
            for col in columns:
                if col + region[2] > TITLE_BLOCK[0] and y + region[3] > TITLE_BLOCK[1]:
                    continue
                if free(pts, taken, col, y, region):
                    spot = (col, y)
                    break
            if spot:
                break
        if spot:
            taken.append(rect(*spot, region))
        out.append(spot)
    return out


# ---------------------------------------------------------------- symbol text
def lib_defaults(lib_text: str, name: str) -> tuple[list[tuple[str, str]], str]:
    s, e = cc.top_symbols(lib_text, 1)[name]
    p = cc.props_in(lib_text[s:e], 2)
    desc = p.get("Description", ("", 0, 0))[0]
    extra = [(k, v) for k, (v, _, _) in p.items() if k not in ("Reference", "Value", "Footprint", "Datasheet", "Description")]
    return extra, desc


def unit_instance(lib_id: str, ref: str, value: str, x: float, y: float, unit: int, path: str,
                  props: list[tuple[str, str]], desc: str, pin_count: int, value_at: tuple[float, float]) -> str:
    at = f"{cc.num(x)} {cc.num(y)} 0"
    body = [es.sheet_prop("Reference", ref, at, autoplace=False),
            es.sheet_prop("Value", value, f"{cc.num(value_at[0])} {cc.num(value_at[1])} 0", hide=False),
            es.sheet_prop("Footprint", "", at), es.sheet_prop("Datasheet", "", at), es.sheet_prop("Description", desc, at)]
    body += [es.sheet_prop(k, v, at) for k, v in props]
    pins = "".join(f'\n\t\t(pin "{i}"\n\t\t\t(uuid "{cc.uid()}")\n\t\t)' for i in range(1, pin_count + 1))
    return (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at})\n\t\t(unit {unit})\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
            f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{cc.uid()}")\n'
            + "\n".join(body) + pins +
            f'\n\t\t(instances\n\t\t\t(project "SPCoast"\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{ref}")\n'
            f'\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)')


class Refs:
    def __init__(self, text: str, base: int):
        self.next = {}
        for prefix, n in re.findall(r'\(property "Reference" "([A-Za-z_]+)(\d+)"', text):
            self.next[prefix] = max(self.next.get(prefix, 0), int(n) + 1)
        self.base = base

    def take(self, prefix: str) -> str:
        n = max(self.next.get(prefix, 0), self.base * 1000 + (900 if prefix == "SW" else 1))
        self.next[prefix] = n + 1
        return f"{prefix}{n}"


REF_PREFIX = {"Device-Switch-OS": "DevSW", "Device-Switch": "DevSW", "Local-Lock": "LK", "Local-Switch": "SW",
              "Device-TrackCircuit-Optical": "DevTC", "Device-Lamp": "DevLamp", "Mast": "DevMast", "Cast-Head-CPL-Encoded": "Cast"}


def place_device(kind: str, value: str, x: float, y: float, refs: Refs, path: str, field_lib: str,
                 overrides: dict | None = None) -> tuple[str, list[str]]:
    extra, desc = lib_defaults(field_lib, kind)
    if overrides:
        extra = [(k, overrides.get(k, v)) for k, v in extra]
    ref = refs.take(REF_PREFIX[kind])
    cx = x - 1.9 if kind == "Device-TrackCircuit-Optical" else x - 12.065
    blocks_ = [unit_instance(f"{FIELD}:{kind}", ref, value, x, y, u, path, extra, desc, PIN_NUMBERS[kind], (cx, y))
               for u in range(1, UNITS.get(kind, 1) + 1)]
    return ref, blocks_


def place_chip(x: float, y: float, address: str, refs: Refs, path: str, hwio_lib: str) -> tuple[str, list[str], str]:
    extra, desc = lib_defaults(hwio_lib, "Driver-I2C-MCP23017")
    extra = [(k, address if k == "Address" else v) for k, v in extra]
    ref = refs.take("Exp")
    units = [unit_instance(f"{HWIO}:Driver-I2C-MCP23017", ref, "${ADDRESS}", x, y + UNIT_STEP * u, u + 1, path, extra, desc, 17,
                           (x + 8.89, y + UNIT_STEP * u - 1.27)) for u in range(4)]
    label = es.hier_label("IOBus", round(x + 17.78, 3), round(y + 7.62, 3), 0)
    return ref, units, label


# ---------------------------------------------------------------- the sheet edit
def edit_sheet(name: str, text: str, field_lib: str, hwio_lib: str, report: list[str]) -> str:
    inv = inventory(text)
    devs = devices_for(inv)
    total = sum(slots_of(d) for d in devs)
    # pack devices onto chips: a device never straddles two chips
    chips: list[list[dict]] = [[]]
    used = 0
    for d in devs:
        n = slots_of(d)
        if used + n > 16:
            chips.append([]); used = 0
        chips[-1].append(d); used += n
    positions = allocate(text, chips)
    skipped = [d for chip, pos in zip(chips, positions) if pos is None for d in chip]
    placed = [(chip, pos) for chip, pos in zip(chips, positions) if pos is not None]
    refs = Refs(text, SHEETS[name])
    path = es.sheet_path(text)
    new_symbols, wires, junctions, labels = [], [], [], []
    for k, (chip, (cx, cy)) in enumerate(placed):
        ref, units, label = place_chip(cx, cy, f"0x{0x20 + k:02X}", refs, path, hwio_lib)
        new_symbols += units; labels.append(label)
        slot = 0
        for d in chip:
            top = round(cy + PIN_STEP * slot, 3)
            if d["kind"] == "mast":
                ind_ys = []
                for head in d["heads"]:
                    hy = round(top + 1.27, 3)
                    _, b = place_device("Cast-Head-CPL-Encoded", "", cx, hy, refs, path, field_lib, {"Head": head})
                    new_symbols += b; ind_ys.append(hy); top = round(top + 2 * PIN_STEP, 3); slot += 2
                mx, my = round(cx + MAST_DX, 3), round((ind_ys[0] + ind_ys[-1]) / 2, 3)
                _, b = place_device("Mast", d["value"], mx, my, refs, path, field_lib)
                new_symbols += b
                if len(ind_ys) > 1:
                    wires.append(es.wire(mx, ind_ys[0], mx, ind_ys[-1]))
                    junctions.append(junction(mx, my))
                continue
            n, dx, dy = FORM[d["kind"]]
            overrides = {"Style": d["style"]} if "style" in d else None
            _, b = place_device(d["kind"], d["value"], round(cx + dx, 3), round(top + dy, 3), refs, path, field_lib, overrides)
            new_symbols += b; slot += n
    # no-connect flags on the expander pins no device uses, as Sargent carries them
    ncs = []
    for chip, (cx, cy) in placed:
        used = sum(slots_of(d) for d in chip)
        for i in range(used, 16):
            ncs.append(es.no_connect(cx, round(cy + PIN_STEP * i, 3)) if hasattr(es, "no_connect") else no_connect(cx, round(cy + PIN_STEP * i, 3)))
    text = es.insert_before_first(text, "wire", ncs)
    # file the new symbols after the last placed symbol, labels/wires/junctions in their sections
    last = max(e for _, e, _ in es.instances(text))
    text = text[:last] + "\n" + "\n".join(new_symbols) + text[last:]
    text = es.insert_before_first(text, "wire", junctions)
    text = es.insert_before_first(text, "global_label", wires)
    text = es.insert_before_first(text, "symbol", labels)
    add = {f"{FIELD}:{k}": cc.cached(FIELD, field_lib, k) for k in PIN_NUMBERS}
    add[f"{HWIO}:Driver-I2C-MCP23017"] = cc.cached(HWIO, hwio_lib, "Driver-I2C-MCP23017")
    text = es.update_cache(text, add)
    kinds = {}
    for d in devs:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    report.append(f"{name}: {len(devs)} appliances ({kinds}), {total} pins on {len(chips)} MCP23017; placed {len(placed)} at {[p for _, p in placed]}")
    if skipped:
        report.append(f"{name}: NO ROOM for {len(skipped)} devices ({sum(slots_of(d) for d in skipped)} pins): "
                      + ", ".join(f"{d['kind']} {d['value']}" for d in skipped))
    return text


def no_connect(x: float, y: float) -> str:
    return f'\t(no_connect\n\t\t(at {cc.num(x)} {cc.num(y)})\n\t\t(uuid "{cc.uid()}")\n\t)'


def junction(x: float, y: float) -> str:
    return f'\t(junction\n\t\t(at {cc.num(x)} {cc.num(y)})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "{cc.uid()}")\n\t)'


# ---------------------------------------------------------------- check
def check(after_path: str) -> list[str]:
    sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
    from kicad_services.netlist_reader import NetlistReader
    m = NetlistReader().read(Path(after_path)); c = m.components
    def fn(n): return n.pinfunction.rsplit("_", 1)[0] if n.pinfunction else n.pin
    bad = []
    for sheet in SHEETS:
        sp = f"/South-cTc/{sheet}/"
        devs = {r for r, comp in c.items() if comp.sheetpath == sp and comp.lib == FIELD}
        exps = {r for r, comp in c.items() if comp.sheetpath == sp and comp.part == "Driver-I2C-MCP23017"}
        procs = {r for r, comp in c.items() if comp.sheetpath == sp and comp.part == "Processor"}
        if not devs or not exps:
            bad.append(f"{sheet}: no devices or no expanders"); continue
        seen_pins = {}
        for net in m.nets:
            nodes = [(n.reference, fn(n)) for n in net.nodes]
            dev_nodes = [(r, p) for r, p in nodes if r in devs and p != "IND"]
            exp_nodes = [(r, p) for r, p in nodes if r in exps and p != "I2C"]
            if any(c[r].part.startswith("Driver-GPIO") for r, _ in nodes):
                continue                                    # a pre-existing device on a GPIO driver
            if dev_nodes and len(exp_nodes) != 1:
                bad.append(f"{sheet}: {dev_nodes} on {len(exp_nodes)} expander pins")
            for r, p in exp_nodes:
                seen_pins.setdefault((r, p), 0); seen_pins[(r, p)] += len(dev_nodes)
            if any(r in exps and p == "I2C" for r, p in nodes):
                if not any(r in procs and p == "IO_Bus" for r, p in nodes):
                    bad.append(f"{sheet}: expander bus pin not on the processor's bus")
        dangling = [r for r in devs if not any(r == n.reference for net in m.nets for n in net.nodes if len(net.nodes) > 1)]
        if dangling:
            bad.append(f"{sheet}: devices with no connected pin: {sorted(dangling)[:6]}")
        if any(v > 1 for v in seen_pins.values()):
            bad.append(f"{sheet}: an expander pin carries two devices")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", metavar="AFTER")
    a = ap.parse_args(argv)
    if a.check:
        bad = check(a.check)
        print("\n".join("FAIL " + b for b in bad) or "check passed: every device pin on exactly one expander pin, every expander on its processor's bus")
        return 1 if bad else 0
    if list(SPCOAST.glob("~*.lck")) or list(LIBDIR.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    field_lib = (LIBDIR / f"{FIELD}.kicad_sym").read_text()
    hwio_lib = (LIBDIR / f"{HWIO}.kicad_sym").read_text()
    report, out = [], {}
    for name in SHEETS:
        p = SPCOAST / f"{name}.kicad_sch"
        out[p] = edit_sheet(name, p.read_text(), field_lib, hwio_lib, report)
    print("\n".join(report))
    if a.dry_run:
        print("dry run: nothing written"); return 0
    for p, t in out.items():
        p.write_text(t)
    print("wrote " + ", ".join(p.name for p in out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
