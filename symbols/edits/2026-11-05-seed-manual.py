"""One-time seed of symbols/manual.html from README.symbols.md (2026-11-05): the draft's prose as marked fragments.

    python3 symbols/edits/2026-11-05-seed-manual.py symbols/README.symbols.md symbols/manual.html

The draft's symbol tables are dropped: tools/contract/symbol_manual.py (FieldUnit-Subdivision) generates them.
"""
import html, re, sys
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2])
T, TS, O, F, FS, H = ("Railroad-Trackplan", "Railroad-Trackplan-Signals", "Railroad-Office", "Railroad-Field", "Railroad-Field-Signals", "Railroad-HardwareIO")
GROUPS = [  # (heading prefix, id, library, match) in the draft's order
    ("Track joints", "track", T, {"library": T, "Role": "TRACK"}),
    ("Operating rules", "policy", T, {"library": T, "Role": "POLICY"}),
    ("Structures", "structures", T, {"tab": T, "Role": "STRUCTURE"}),
    ("Switches and derails", "switches", T, {"library": T, "Appliance": "switch"}),
    ("Track circuits", "track-circuits", T, {"library": T, "Appliance": "track_circuit"}),
    ("Masts drawn with", "masts-with-heads", T, {"library": T, "Appliance": ["mast", "head"]}),
    ("Masts with derived", "masts", TS, {"library": TS, "Appliance": "mast"}),
    ("Train order", "train-order", T, {"library": T, "Appliance": "train_order"}),
    ("Non-vital lamps", "lamps-contacts", T, {"library": T, "Appliance": ["lamp", "contact"]}),
    ("The machine", "machine", O, {"library": O, "Role": ["OFFICE_UNIT", "COLUMN"]}),
    ("Lever plates", "levers", O, {"library": O, "Role": "PANEL", "Appliance": "lever"}),
    ("Model board lamps", "board-lamps", O, {"library": O, "Role": "PANEL", "Appliance": "lamp"}),
    ("Transports", "transports", O, {"library": O, "Role": "TRANSPORT"}),
    ("Code line encodings", "codeline-encodings", O, {"library": O, "Role": "CODELINE_ENCODING"}),
    ("I/O encodings", "io-encodings", O, {"library": O, "Role": "IO_ENCODING"}),
    ("Switch machines", "switch-devices", F, {"library": F, "Role": "DEVICE", "Appliance": "switch"}),
    ("Track circuit detectors", "track-circuit-devices", F, {"library": F, "Role": "DEVICE", "Appliance": "track_circuit"}),
    ("Lamps and contacts", "lamp-contact-devices", F, {"library": F, "Role": "DEVICE", "Appliance": ["lamp", "contact"]}),
    ("Local plates", "local-plates", F, {"library": F, "Role": "DEVICE", "Appliance": "lever"}),
    ("Whole-mast device", "whole-mast", F, {"library": F, "Role": "DEVICE", "Appliance": "mast"}),
    ("Head devices of the older", "old-heads", F, {"library": F, "Role": "DEVICE", "Appliance": "head"}),
    ("Field mast devices", "field-masts", FS, {"library": FS, "Role": "DEVICE", "Appliance": "mast"}),
    ("Anonymous heads", "heads", FS, {"library": FS, "Role": "DEVICE", "Appliance": "head"}),
    ("Encoders", "encoders", FS, {"library": FS, "Role": "ENCODER"}),
    ("I2C chips", "i2c", H, {"library": H, "Role": "IODRIVER", "pin": "A1"}),
    ("Processor pins", "gpio", H, {"library": H, "Role": "IODRIVER", "IC": "GPIO"}),
    ("CMRInet node", "cmri", H, {"library": H, "Role": "IODRIVER", "IC": "CMRI"}),
    ("JMRI objects", "jmri", H, {"library": H, "Role": "IODRIVER", "IC": "MQTT-JMRI"}),
    ("Settings on a net", "settings", H, {"library": H, "Role": "SETTING"}),
]
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
def to_html(lines):
    out, para, items = [], [], []
    def flush():
        if para: out.append("<p>" + "\n".join(inline(x) for x in para) + "</p>"); para.clear()
        if items: out.append("<ul>\n" + "\n".join(f"<li>{inline(x)}</li>" for x in items) + "\n</ul>"); items.clear()
    for ln in lines:
        if ln.startswith("|"): continue
        if not ln.strip(): flush()
        elif ln.startswith("- "):
            if para: flush()
            items.append(ln[2:])
        elif ln.startswith("#"):
            flush(); out.append(f"<h2>{inline(ln.lstrip('# '))}</h2>")
        else:
            if items: flush()
            para.append(ln)
    flush()
    return "\n".join(out) + "\n"
sections, cur = [("", [])], None
for ln in src.read_text().splitlines():
    if ln.startswith("### "): sections.append((ln[4:], []))
    elif ln.startswith("## ") and sections[-1][0]: sections.append(("", [ln]))   # a library section's opening lines
    else: sections[-1][1].append(ln)
intro = [ln for h, body in sections if not h for ln in body + [""]]
HEAD = """<!-- The hand-written text of the Railroad symbols manual.

Each fragment is HTML between an opening marker and its END marker. A GROUP marker holds the group's
title and the selector that says which symbols belong to it; `a or b` is either value. The page order is
the order of this file. Text outside the markers is not read.

Generate the page (FieldUnit-Subdivision):  uv run python tools/contract/symbol_manual.py
The page is symbols/production/manual/index.html. To keep prose edited in the page:
                                            uv run python tools/contract/symbol_manual.py --harvest
-->

"""
def sel(v): return v if isinstance(v, str) else " or ".join(v)
parts = ["<!-- ABOUT -->\n" + to_html([ln for ln in intro if not ln.startswith("# ")]) + "<!-- END ABOUT -->"]
for prefix, gid, lib, match in GROUPS:
    (heading, body), = [s for s in sections if s[0].startswith(prefix)]
    title = re.sub(r"\s*\(.*\)$", "", heading)
    parts.append(f"<!-- GROUP: {title} | " + ", ".join(f"{k}={sel(v)}" for k, v in match.items()) + " -->\n" + to_html(body) + "<!-- END GROUP -->")
out.write_text(HEAD + "\n\n".join(parts) + "\n")
