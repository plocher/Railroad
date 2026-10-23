#!/usr/bin/env python3
"""Fit and finish, 2026-10-23: head-device definitions refreshed; local-bus IOBus labels made local.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-23-fit-finish.py

- Every sheet's cached Device-Head-* definitions are refreshed from Railroad-Field (the owner renamed Cast-Head-* to
  Device-Head-* with fixed, hidden styles); any stale Cast-Head-* cache entry is dropped.
- A unit sheet whose box on South-cTc no longer has an IOBus pin (the owner removed them where the bus is local) has its
  IOBus hierarchical labels turned into local labels: the bus stays tied to its processor and expanders, and ERC stops
  reporting a sheet-pin mismatch.
Gate: connectivity, parts and fields identical. KiCad must be closed.
"""
import importlib.util, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc, blocks = es.cc, es.blocks
FIELD = "Railroad-Field"
if list(es.SPCOAST.glob("~*.lck")) or list(es.LIBDIR.glob("~*.lck")):
    sys.exit("KiCad holds a lock; close it first")
field = (es.LIBDIR / f"{FIELD}.kicad_sym").read_text()
heads = [n for n in cc.top_symbols(field, 1) if n.startswith("Device-Head")]
root = (es.SPCOAST / "South-cTc.kicad_sch").read_text()
boxes = {}
for s, e in blocks(root, "sheet", 1):
    b = root[s:e]
    boxes[re.search(r'\(property "Sheetfile" "([^"]+)"', b).group(1)] = set(re.findall(r'\n\t\t\(pin "([^"]+)" ', b))
for p in sorted(es.SPCOAST.glob("*.kicad_sch")):
    t = p.read_text(); changed = []
    add = {f"{FIELD}:{h}": cc.cached(FIELD, field, h) for h in heads if f'(lib_id "{FIELD}:{h}")' in t}
    ls = t.index("(lib_symbols"); cache = t[ls:es.end_of(t, ls)]
    stale = tuple(n for n in cc.top_symbols(cache, 2) if n.startswith(f"{FIELD}:Cast-Head"))
    if add or stale:
        t = es.update_cache(t, add, drop=stale); changed.append(f"{len(add)} head definitions refreshed, {len(stale)} stale Cast-Head entries dropped")
    if p.name in boxes and "IOBus" not in boxes[p.name] and '(hierarchical_label "IOBus"' in t:
        n = 0
        for s, e in sorted(list(blocks(t, "hierarchical_label", 1)), reverse=True):
            b = t[s:e]
            if b.startswith('(hierarchical_label "IOBus"'):
                b = re.sub(r"\n\t\t\(shape \w+\)", "", b.replace('(hierarchical_label "IOBus"', '(label "IOBus"', 1), count=1)
                t = cc.splice(t, [(s, e, b)]); n += 1
        changed.append(f"{n} IOBus labels made local (no IOBus pin on the sheet's box)")
    if changed:
        p.write_text(t); print(f"{p.name}: " + "; ".join(changed))
