#!/usr/bin/env python3
"""Gilroy Interchange hosts itself, 2026-10-22: its Host port on South-cTc leaves the SPCoastApp host line.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-interchange-host.py

The Interchange sheet wires its Interlocking's Host to its own processor (Gilroy, with the pixel heads on its bus);
the root sheet still dropped the sheet's Host port onto the SPCoastApp line, so the unit had two hosts. The drop
becomes a no-connect, as Sargent's and the other self-hosted units' ports are. KiCad must be closed.
"""
import importlib.util, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("lu", HERE / "2026-10-21-local-units.py")
lu = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(lu)
es = lu.es
ROOT = es.SPCOAST / "South-cTc.kicad_sch"
PIN, LINE = (63.5, 111.76), 81.28
if list(es.SPCOAST.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
t = ROOT.read_text()
t = es.drop_wire(t, (PIN[0], LINE, PIN[0], PIN[1]))
t = es.drop_wire(t, (34.29, LINE, PIN[0], LINE))       # the host-line segment that only reached this drop; Caltrain's feed stays
t = es.insert_before_first(t, "wire", [lu.no_connect(*PIN)])
ROOT.write_text(t)
print("South-cTc: Gilroy Interchange's Host port: drop to the SPCoastApp line removed, no-connect placed")
