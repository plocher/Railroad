#!/usr/bin/env python3
"""Gate for 2026-10-21-explicit-seams.py: the expected seam nets, nothing else changed, nothing new from ERC.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-21-explicit-seams-gate.py \\
        production/explicit-seams-before.net production/explicit-seams-after.net \\
        [--erc-before production/explicit-seams-before.erc.json --erc-after production/explicit-seams-after.erc.json]

Exit 0 only when every check passes (ADR 0007 §2.4):
- every unit's Codeline net is exactly {its Interlocking, its houses, its transport, the transport's encoding};
  Luchessa on Time Coded, every other unit on MQTT;
- every Host net is exactly {the processor, what it hosts}: SPCoastApp hosts five units and the two I/O
  transports; Luchessa and Sargent host themselves; JohnCTC hosts the desk;
- the remote I/O attachments sit alone with their transports; the desk bus is JohnCTC and the panel chips;
- nets that touch no seam symbol are unchanged; parts removed / added are exactly the placeholders / the
  new symbols; fields change only where the ruling says (CP Name, bare CP, node fields, encoding fields);
- ERC: no new (sheet, type) and no count that grew.
The comparison is of two netlists: evidence of the edit, not proof that the documents were otherwise preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.netlist_reader import NetlistReader  # noqa: E402

SEAM_PARTS = ("Processor", "Processor-Virtual", "FieldUnit_Virtual", "Remote-IO-CMRInet", "Remote-IO-JMRI", "OfficeUnit",
              "Interlocking", "MAIN HOUSE") + tuple(f"Codeline-{k}" for k in ("Transport-CMRInet", "Transport-MQTT", "Transport-TimeCode",
                                                                           "Transport-Loconet", "Encoding-AAR", "Encoding-US&S-506"))
REMOVED, ADDED = {"Proc1", "Proc2", "Proc3", "HOST1", "Encoding1"}, {"RIO1", "RIO2", "Proc6", "Proc7"}
LINE = {"/South-cTc/Luchessa/": "Transport2005"}            # every other unit rides MQTT, Transport2006
HOST = {"/South-cTc/Luchessa/": "Proc5", "/South-cTc/Sargent/": "Proc6"}   # every other unit runs on SPCoastApp, Proc7


def seam_node(comp, pin: str) -> bool:
    return comp.part in SEAM_PARTS or pin in ("I2C", "IO_Bus")


def fn(node) -> str:
    """The pin's name: kicad-cli writes pinfunction as <name>_<number>."""
    return node.pinfunction.rsplit("_", 1)[0] if node.pinfunction else node.pin


def nets_of(model):
    out = []
    for net in model.nets:
        nodes = frozenset((n.reference, fn(n)) for n in net.nodes)
        if len(nodes) > 1:
            out.append(nodes)
    return out


def plain_nets(model) -> Counter:
    """Connectivity among nodes that are not seam nodes, as a multiset of pin sets."""
    c = Counter()
    for net in model.nets:
        nodes = frozenset((n.reference, fn(n)) for n in net.nodes if not seam_node(model.components[n.reference], fn(n)))
        if len(nodes) > 1:
            c[nodes] += 1
    return c


def net_containing(nets, ref, pin):
    hits = [n for n in nets if (ref, pin) in n]
    return hits[0] if len(hits) == 1 else None


def check(before, after, erc_before=None, erc_after=None) -> list[str]:
    bad: list[str] = []
    b, a = before.components, after.components
    if set(b) - set(a) != REMOVED:
        bad.append(f"parts removed: expected {sorted(REMOVED)}, got {sorted(set(b) - set(a))}")
    if set(a) - set(b) != ADDED:
        bad.append(f"parts added: expected {sorted(ADDED)}, got {sorted(set(a) - set(b))}")
    # --- the seam nets
    nets = nets_of(after)
    by_sheet = defaultdict(lambda: {"units": [], "houses": []})
    for ref, c in a.items():
        if c.part == "Interlocking":
            by_sheet[c.sheetpath]["units"].append(ref)
        elif c.part == "MAIN HOUSE":
            by_sheet[c.sheetpath]["houses"].append(ref)
    encoding_of = {"Transport2005": "Encoding2", "Transport2006": "Encoding2001"}
    for sheet, d in sorted(by_sheet.items()):
        (unit,) = d["units"]
        line = LINE.get(sheet, "Transport2006")
        want = {(unit, "Codeline"), (line, "Transport"), (encoding_of[line], "Transport")} | {(h, "Codeline") for h in d["houses"]}
        for other, od in by_sheet.items():            # every unit on the same line shares the net
            if LINE.get(other, "Transport2006") == line:
                want |= {(od["units"][0], "Codeline")} | {(h, "Codeline") for h in od["houses"]}
        got = net_containing(nets, unit, "Codeline")
        if got != frozenset(want):
            bad.append(f"{sheet} Codeline net: expected {sorted(want)}, got {sorted(got or [])}")
        host = HOST.get(sheet, "Proc7")
        got = net_containing(nets, unit, "Host")
        if got is None or (host, "Host") not in got:
            bad.append(f"{sheet} Host net does not reach {host}: {sorted(got or [])}")
    app = net_containing(nets, "Proc7", "Host")
    want_app = {("Proc7", "Host"), ("Transport2007", "Host"), ("Transport2009", "Host")} | {
        (d["units"][0], "Host") for s, d in by_sheet.items() if HOST.get(s, "Proc7") == "Proc7"}
    if app != frozenset(want_app):
        bad.append(f"SPCoastApp Host net: expected {sorted(want_app)}, got {sorted(app or [])}")
    for proc, unit_sheet in (("Proc5", "/South-cTc/Luchessa/"), ("Proc6", "/South-cTc/Sargent/")):
        want = frozenset({(proc, "Host"), (by_sheet[unit_sheet]["units"][0], "Host")})
        if net_containing(nets, proc, "Host") != want:
            bad.append(f"{proc} Host net: expected {sorted(want)}, got {sorted(net_containing(nets, proc, 'Host') or [])}")
    if net_containing(nets, "Proc4", "Host") != frozenset({("Proc4", "Host"), ("MACHINE2002", "Host")}):
        bad.append(f"desk Host net: {sorted(net_containing(nets, 'Proc4', 'Host') or [])}")
    if net_containing(nets, "MACHINE2002", "Codeline") != frozenset({("MACHINE2002", "Codeline"), ("Transport2005", "Host"), ("Transport2006", "Host")}):
        bad.append(f"machine Codeline net: {sorted(net_containing(nets, 'MACHINE2002', 'Codeline') or [])}")
    for rio, transport in (("RIO1", "Transport2007"), ("RIO2", "Transport2009")):
        want = frozenset({(rio, "Transport"), (transport, "Transport")})
        if net_containing(nets, rio, "Transport") != want:
            bad.append(f"{rio} attachment net: expected {sorted(want)}, got {sorted(net_containing(nets, rio, 'Transport') or [])}")
    bus = net_containing(nets, "Proc4", "IO_Bus")
    chips = {(r, "I2C") for r, c in a.items() if c.part.startswith("Driver-I2C-MAX7313") and c.sheetpath == "/South-cTc/Luchessa/Panel/"}
    if bus != frozenset({("Proc4", "IO_Bus")} | chips):
        bad.append(f"desk bus net: got {sorted(bus or [])}")
    # --- everything else unchanged
    pb, pa = plain_nets(before), plain_nets(after)
    if pb != pa:
        bad.append(f"connectivity away from the seams changed: {sum((pb - pa).values())} nets lost, {sum((pa - pb).values())} gained")
    for ref, cb in b.items():
        if ref not in a:
            continue
        ca = a[ref]
        if (cb.lib, cb.part) != (ca.lib, ca.part):
            bad.append(f"{ref}: part changed {cb.lib}:{cb.part} -> {ca.lib}:{ca.part}")
            continue
        fb, fa = dict(cb.fields), dict(ca.fields)
        if cb.part == "MAIN HOUSE":
            bare = cb.value[3:] if cb.value.startswith("CP ") else cb.value
            if fa.pop("CP Name", None) != bare:
                bad.append(f"{ref}: CP Name is {ca.fields.get('CP Name')!r}, expected {bare!r}")
            if ca.value != cb.value:
                bad.append(f"{ref}: shown Value changed {cb.value!r} -> {ca.value!r}")
        if cb.sheetpath == "/South-cTc/Luchessa/" and fb.get("CP", "").startswith("CP "):
            if fa.get("CP") != fb["CP"][3:]:
                bad.append(f"{ref}: CP {fa.get('CP')!r}, expected {fb['CP'][3:]!r}")
            fb["CP"] = fb["CP"][3:]
        if cb.part == "Processor":
            for k in ("Transport", "Address"):
                if k in fa:
                    bad.append(f"{ref}: {k} still present")
                fb.pop(k, None)
            fb.pop("Description", None); fa.pop("Description", None)
        if cb.part.startswith("Codeline-Encoding") or cb.part == "Codeline-Transport-MQTT":
            for k in ("Station", "Address"):
                if k in fa:
                    bad.append(f"{ref}: {k} still present")
                fb.pop(k, None)
        if cb.value != ca.value and cb.part != "MAIN HOUSE":
            bad.append(f"{ref}: Value changed {cb.value!r} -> {ca.value!r}")
        if fb != fa:
            bad.append(f"{ref}: fields changed: {sorted(set(fb.items()) ^ set(fa.items()))}")
    # --- ERC
    if erc_before is not None and erc_after is not None:
        cb_, ca_ = Counter(), Counter()
        for src, c in ((erc_before, cb_), (erc_after, ca_)):
            for sh in src.get("sheets", []):
                for v in sh.get("violations", []):
                    items = " ".join(i.get("description", "") for i in v.get("items", []))
                    if "Proc6 Pin 2 [IO_Bus" in items:       # Sargent's new processor: its bus pin is unwired, chips attach by sheet
                        continue
                    c[(sh.get("path"), v.get("type"))] += 1
        for k, n in ca_.items():
            if n > cb_.get(k, 0):
                bad.append(f"ERC: {k} went from {cb_.get(k, 0)} to {n}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("before"); ap.add_argument("after")
    ap.add_argument("--erc-before"); ap.add_argument("--erc-after")
    a = ap.parse_args(argv)
    before, after = NetlistReader().read(Path(a.before)), NetlistReader().read(Path(a.after))
    eb = json.loads(Path(a.erc_before).read_text()) if a.erc_before else None
    ea = json.loads(Path(a.erc_after).read_text()) if a.erc_after else None
    bad = check(before, after, eb, ea)
    for line in bad:
        print("FAIL", line)
    if not bad:
        print(f"gate passed: {len(after.components)} parts, {len(nets_of(after))} nets, seam nets as expected, nothing else changed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
