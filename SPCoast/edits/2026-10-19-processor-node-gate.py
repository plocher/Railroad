#!/usr/bin/env python3
"""Gate for 2026-10-19-processor-node.py: the expected delta, nothing else, and nothing new from ERC.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-19-processor-node-gate.py \\
        production/pre-processor.net production/post-processor.net \\
        [--erc-before production/pre-processor-erc.json --erc-after production/post-processor-erc.json] [--self-test]

Exit 0 only when every check passes (ADR 0007 §2.4): the required changes are present, no other field
changes, connectivity unchanged, no new ERC violation. `--self-test` builds the expected "after" model
from the "before" model in memory, shows the gate passes it, then breaks it three ways and shows the
gate fails each (ADR 0007 C11). The comparison is of two netlists: evidence of the edit, not proof that
the documents were otherwise preserved.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.netlist_reader import NetlistReader  # noqa: E402

HWIO = "Railroad-HardwareIO"
CMRI = {"Driver-CMRI-IB": "IN", "Driver-CMRI-OB": "OUT"}
CMRI_DESC = {
    "Driver-CMRI-IB": "CMRInet digital input. Bit = this bit on the node the sheet's Processor declares (ADR 0005).",
    "Driver-CMRI-OB": "CMRInet digital output. Bit = this bit on the node the sheet's Processor declares (ADR 0005).",
}
TRANSPORTS = ("Codeline-Transport-CMRInet", "Codeline-Transport-MQTT", "Codeline-Transport-Loconet", "Codeline-Transport-TimeCode")
NODE = {"Role": "STRUCTURE", "Kind": "PROCESSOR", "Transport": "CMRInet", "Address": "30", "Board": "cpNode"}
NODE_VALUE, NODE_REF, EXPECTED_DRIVERS = "Caltrain", "Proc1", 34


def nets(model) -> set[frozenset]:
    return {frozenset((n.reference, n.pin) for n in net.nodes) for net in model.nets if len(net.nodes) > 1}


def check(before, after, erc_before=None, erc_after=None) -> list[str]:
    bad: list[str] = []
    if nets(before) != nets(after):
        lost, gained = nets(before) - nets(after), nets(after) - nets(before)
        bad.append(f"connectivity changed: {len(lost)} nets lost, {len(gained)} gained")
    b, a = before.components, after.components
    new = set(a) - set(b)
    if set(b) - set(a):
        bad.append(f"parts removed: {sorted(set(b) - set(a))}")
    if new != {NODE_REF}:
        bad.append(f"parts added: expected only {NODE_REF}, got {sorted(new)}")
    else:
        p = a[NODE_REF]
        if (p.lib, p.part) != (HWIO, "Processor"):
            bad.append(f"{NODE_REF} is {p.lib}:{p.part}, not {HWIO}:Processor")
        if p.value != NODE_VALUE:
            bad.append(f"{NODE_REF} Value {p.value!r}, expected {NODE_VALUE!r}")
        for k, v in NODE.items():
            if p.fields.get(k) != v:
                bad.append(f"{NODE_REF} {k}={p.fields.get(k)!r}, expected {v!r}")
    drivers = [r for r, c in b.items() if c.lib == HWIO and c.part in CMRI]
    if len(drivers) != EXPECTED_DRIVERS:
        bad.append(f"{len(drivers)} CMRI drivers before, expected {EXPECTED_DRIVERS}")
    for r, cb in b.items():
        if r not in a:
            continue
        ca = a[r]
        if (cb.lib, cb.part) != (ca.lib, ca.part):
            bad.append(f"{r}: part changed {cb.lib}:{cb.part} -> {ca.lib}:{ca.part}")
            continue
        fb, fa = dict(cb.fields), dict(ca.fields)
        if cb.lib == HWIO and cb.part in CMRI:
            if fb.get("Address") != "30":
                bad.append(f"{r}: Address before was {fb.get('Address')!r}, the ruling assumed 30")
            for k in ("UA", "Address"):
                if k in fa:
                    bad.append(f"{r}: {k} still present ({fa[k]!r})")
                fb.pop(k, None)
            want = f"{CMRI[cb.part]}.{fb.get('Bit')}"
            if ca.value != want:
                bad.append(f"{r}: Value {ca.value!r}, expected {want!r}")
            if fa.get("Description") != CMRI_DESC[cb.part]:
                bad.append(f"{r}: Description not the new library text")
            fb["Description"] = CMRI_DESC[cb.part]
        elif cb.part in TRANSPORTS:
            if cb.part == "Codeline-Transport-MQTT":
                if "Station" not in fb:
                    bad.append(f"{r}: MQTT transport had no Station before")
                if "Station" in fa:
                    bad.append(f"{r}: Station still present")
                fb.pop("Station", None)
            if fa.get("Host") != "":
                bad.append(f"{r}: Host missing or not empty ({fa.get('Host')!r})")
            fb["Host"] = ""
            if ca.value != cb.value:
                bad.append(f"{r}: Value changed {cb.value!r} -> {ca.value!r}")
        elif ca.value != cb.value:
            bad.append(f"{r}: Value changed {cb.value!r} -> {ca.value!r}")
        diff = {k for k in set(fb) | set(fa) if fb.get(k) != fa.get(k)}
        if diff:
            bad.append(f"{r}: unexpected field changes: {sorted(diff)}")
    if erc_before is not None and erc_after is not None:
        cb_, ca_ = erc_counts(erc_before), erc_counts(erc_after)
        grown = {k: (cb_.get(k, 0), ca_[k]) for k in ca_ if ca_[k] > cb_.get(k, 0)}
        if grown:
            bad.append(f"ERC violations grew: {grown}")
    return bad


def erc_counts(report: dict) -> Counter:
    return Counter((v["type"], v["severity"]) for s in report["sheets"] for v in s["violations"])


def expected_after(before):
    """The after model the ruling promises, built in memory from before."""
    comps = {}
    for r, c in before.components.items():
        f = dict(c.fields)
        v = c.value
        if c.lib == HWIO and c.part in CMRI:
            f.pop("UA", None); f.pop("Address", None)
            f["Description"] = CMRI_DESC[c.part]
            v = f"{CMRI[c.part]}.{f['Bit']}"
        elif c.part in TRANSPORTS:
            f.pop("Station", None)
            f["Host"] = ""
        comps[r] = dataclasses.replace(c, value=v, fields=f)
    sheet = next(c.sheetpath for c in before.components.values() if c.part in CMRI)
    comps[NODE_REF] = dataclasses.replace(next(iter(before.components.values())), reference=NODE_REF, value=NODE_VALUE,
                                          lib=HWIO, part="Processor", fields=dict(NODE), sheetpath=sheet)
    return dataclasses.replace(before, components=comps)


def self_test(before) -> int:
    good = expected_after(before)
    ok = check(before, good)
    print("expected after passes:", not ok, ok or "")
    failures = 0
    # 1. a driver keeps its UA
    broken = expected_after(before)
    r = next(r for r, c in broken.components.items() if c.part in CMRI)
    broken.components[r] = dataclasses.replace(broken.components[r], fields={**broken.components[r].fields, "UA": "30"})
    f1 = check(before, broken); print("UA left on one driver -> fails:", bool(f1), f1[:1]); failures += not f1
    # 2. a net changes
    broken = expected_after(before)
    broken = dataclasses.replace(broken, nets=broken.nets[1:])
    f2 = check(before, broken); print("one net dropped -> fails:", bool(f2), f2[:1]); failures += not f2
    # 3. an unrelated field changes
    broken = expected_after(before)
    r = next(r for r, c in broken.components.items() if c.part not in CMRI and c.part not in TRANSPORTS and c.part != "Processor")
    broken.components[r] = dataclasses.replace(broken.components[r], fields={**broken.components[r].fields, "Role": "X"})
    f3 = check(before, broken); print("unrelated field changed -> fails:", bool(f3), f3[:1]); failures += not f3
    failures += bool(ok)
    print("self-test:", "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path, nargs="?")
    ap.add_argument("--erc-before", type=Path)
    ap.add_argument("--erc-after", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    before = NetlistReader().read(a.before)
    if a.self_test:
        return self_test(before)
    if not a.after:
        ap.error("after netlist required unless --self-test")
    after = NetlistReader().read(a.after)
    eb = json.loads(a.erc_before.read_text()) if a.erc_before else None
    ea = json.loads(a.erc_after.read_text()) if a.erc_after else None
    bad = check(before, after, eb, ea)
    drivers = sum(1 for c in after.components.values() if c.lib == HWIO and c.part in CMRI)
    print(f"after: {len(after.components)} parts, {len(nets(after))} nets; {drivers} CMRI drivers; {NODE_REF} present: {NODE_REF in after.components}")
    for line in bad:
        print("FAIL:", line)
    print("gate:", "PASS" if not bad else f"FAIL ({len(bad)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
