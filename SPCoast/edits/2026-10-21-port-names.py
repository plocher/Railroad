#!/usr/bin/env python3
"""Port names, 2026-10-21: two hierarchical names that did not match across a sheet boundary.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-port-names.py

- South-cTc: the Luchessa sheet box's pin `OfficeBusIO` becomes `OfficeIOBus`, the name every other unit uses
  and the label Luchessa's sheet carries.
- Gilroy Interchange: the hierarchical label `JMRI_MQTT` on the JMRI attachment becomes `IOBus`, the port name
  the parent wires (to the JMRI_MQTT transport).
Gate: the netlist after must show Luchessa's three MAX7313s on the desk bus with Proc4 and RIO2 on the
JMRI_MQTT transport; nothing else changes. KiCad must be closed.
"""
import re, sys
from pathlib import Path

SPCOAST = Path.home() / "Dropbox/KiCad/Railroad/SPCoast"
if list(SPCOAST.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
root = SPCOAST / "South-cTc.kicad_sch"
t = root.read_text()
assert t.count('(pin "OfficeBusIO" ') == 1, t.count('(pin "OfficeBusIO" ')
root.write_text(t.replace('(pin "OfficeBusIO" ', '(pin "OfficeIOBus" ', 1))
gi = SPCOAST / "GilroyInterchange.kicad_sch"
t = gi.read_text()
assert t.count('(hierarchical_label "JMRI_MQTT"') == 1
gi.write_text(t.replace('(hierarchical_label "JMRI_MQTT"', '(hierarchical_label "IOBus"', 1))
print("renamed: South-cTc Luchessa pin OfficeBusIO -> OfficeIOBus; GilroyInterchange label JMRI_MQTT -> IOBus")
