#!/usr/bin/env python3
"""Watsonville yard, 2026-10-22: the 24 yard track circuits onto the two expanders the owner added (0x25, 0x26).

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-watsonville-yard.py [--dry-run]

Same form as 2026-10-21-field-io.py: a Device-TrackCircuit-Optical per circuit, its ~OCC pin on the expander's
pin, filling the expanders' free pins in order; the pins left over are no-connected. KiCad must be closed.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fio", HERE / "2026-10-21-field-io.py")
fio = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fio)
es, cc, blocks = fio.es, fio.cc, fio.blocks
SHEET = fio.SPCOAST / "Watsonville.kicad_sch"
TARGET_ADDRESSES = ("0x25", "0x26")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(fio.SPCOAST.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    text = SHEET.read_text()
    field_lib = (fio.LIBDIR / f"{fio.FIELD}.kicad_sym").read_text()
    inv = fio.inventory(text)
    missing = sorted(inv["circuits"] - {v for v in circuits_drawn(text)}, key=lambda v: (len(v), v))
    chips = []
    for s, e, lib_id in es.instances(text):
        if lib_id.endswith("Driver-I2C-MCP23017") and "\n\t\t(unit 1)" in text[s:e]:
            p = cc.props_in(text[s:e], 2)
            if p["Address"][0] in TARGET_ADDRESSES:
                x, y, rot = es.inst_at(text[s:e])
                assert rot == 0
                chips.append((p["Address"][0], x, y))
    chips.sort()
    assert [c[0] for c in chips] == list(TARGET_ADDRESSES), chips
    pins = [(round(x, 3), round(y + fio.PIN_STEP * i, 3)) for _, x, y in chips for i in range(16)]
    # the pins must be free: nothing but the expanders' own units may sit on them (a unit's anchor is its first pin)
    others = []
    for s, e, lib_id in es.instances(text):
        if not lib_id.endswith("Driver-I2C-MCP23017"):
            x, y, _ = es.inst_at(text[s:e]); others.append((round(x, 3), round(y, 3)))
    busy = [p for p in pins if p in others]
    assert not busy, f"expander pins already carry something: {busy}"
    assert len(missing) <= len(pins), (len(missing), len(pins))
    refs = fio.Refs(text, fio.SHEETS["Watsonville"])
    path = es.sheet_path(text)
    new, ncs = [], []
    for tc, (px, py) in zip(missing, pins):
        _, b = fio.place_device("Device-TrackCircuit-Optical", tc, round(px + fio.FORM["Device-TrackCircuit-Optical"][1], 3), py,
                                refs, path, field_lib)
        new += b
    for px, py in pins[len(missing):]:
        ncs.append(fio.no_connect(px, py))
    last = max(e for _, e, _ in es.instances(text))
    text = text[:last] + "\n" + "\n".join(new) + text[last:]
    text = es.insert_before_first(text, "wire", ncs)
    print(f"Watsonville: {len(missing)} track circuits placed on {TARGET_ADDRESSES}: {missing}; {len(ncs)} pins no-connected")
    if a.dry_run:
        print("dry run: nothing written"); return 0
    SHEET.write_text(text)
    print(f"wrote {SHEET.name}")
    return 0


def circuits_drawn(text: str):
    for s, e, lib_id in es.instances(text):
        if lib_id.endswith("Device-TrackCircuit-Optical"):
            yield cc.props_in(text[s:e], 2)["Value"][0]


if __name__ == "__main__":
    sys.exit(main())
