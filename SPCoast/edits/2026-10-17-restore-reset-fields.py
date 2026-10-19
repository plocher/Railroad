#!/usr/bin/env python3
"""One-off, 2026-10-17: restore per-instance fields that KiCad reset to library defaults.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python \
        SPCoast/edits/2026-10-17-restore-reset-fields.py [--dry-run]

Between the last good netlist export (production/deploy-cases.net, 2026-10-17 before the owner's
final save) and the checkpoint commit 857cae2, a KiCad "update symbols from library" with field
reset put library defaults into per-instance fields on nine sheets: PanelLamp IndicationToken
(-> "S"), PanelColumn Interlocking (-> "Luchessa"), Codeline-Encoding Station (-> "Panel"),
Sargent Exp2 PCA9685-PWM Address/Value (0x27 -> 0x20, colliding with Exp3), and the 34 CMRI bit
numbers on Caltrain (Address -> "1"). The JMRI Value blanks on Gilroy Interchange were intended
and are not restored. TABLE below is the diff of the two netlists, embedded because production/
is not under git. Lesson: never tick "reset fields" / "update field values" in Update Symbols;
the sync script (2026-10-16-sync-library-fields.py) is the safe way to follow the library.

2026-10-18: the reset happened again (same checkbox); this script restored IndicationToken, Interlocking,
Station and Exp2's address. Its GilroyCalTrain CMRI entries were stale (the bit number has moved from
Address to Bit since the 17th) and wrote bit numbers into 32 Addresses; they were put back to 30 and the
entries removed. A restore table is only valid against the damage it was diffed from: dry-run and read it.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Dropbox/workspace/FieldUnit-Subdivision/tools"))
from kicad_services.sch_text import blocks  # noqa: E402

SPCOAST = Path.home() / "Dropbox/KiCad/Railroad/SPCoast"

TABLE = {'Christopher-Panel': {'COL10028': {'Interlocking': 'Christopher'},
                       'COL10029': {'Interlocking': 'Christopher'},
                       'COL10030': {'Interlocking': 'Christopher'},
                       'LMP10081': {'IndicationToken': '1SAT'},
                       'LMP10082': {'IndicationToken': '813T1'},
                       'LMP10083': {'IndicationToken': '2SAT'},
                       'LMP10091': {'IndicationToken': '815T1'},
                       'LMP10092': {'IndicationToken': '815AT1'},
                       'LMP10093': {'IndicationToken': '817T1'},
                       'LMP10101': {'IndicationToken': '1NAT'},
                       'LMP10102': {'IndicationToken': '2NAT'},
                       'MCK10008': {'IndicationToken': 'MC1K'},
                       'MCK10010': {'IndicationToken': 'MC2K'}},
 'Corporal-Panel': {'COL12031': {'Interlocking': 'Corporal'},
                    'COL12032': {'Interlocking': 'Corporal'},
                    'LMP12111': {'IndicationToken': '829T1'},
                    'LMP12112': {'IndicationToken': '831T1'},
                    'LMP12113': {'IndicationToken': '1SAT'},
                    'LMP12121': {'IndicationToken': 'Watsonville:NFLK'},
                    'LMP12122': {'IndicationToken': 'Watsonville:SFLK'},
                    'LMP12123': {'IndicationToken': 'Watsonville:02T'},
                    'MCK12011': {'IndicationToken': 'MC1K'}},
 'GilroyCalTrain-Panel': {'COL4021': {'Interlocking': 'Gilroy Caltrain'},
                          'COL4022': {'Interlocking': 'Gilroy Caltrain'},
                          'LMP4011': {'IndicationToken': '773T1,775T1'},
                          'LMP4012': {'IndicationToken': '1SAT'},
                          'LMP4021': {'IndicationToken': '01T'},
                          'LMP4022': {'IndicationToken': '02T'},
                          'LMP4023': {'IndicationToken': '03T'},
                          'MCK4001': {'IndicationToken': 'MC1K'}},
 'GilroyInterchange-Panel': {'COL6023': {'Interlocking': 'Gilroy Interchange'},
                             'COL6024': {'Interlocking': 'Gilroy Interchange'},
                             'LMP6031': {'IndicationToken': 'Luchessa:NFLK'},
                             'LMP6032': {'IndicationToken': 'Luchessa:SFLK'},
                             'LMP6033': {'IndicationToken': '1SAT'},
                             'LMP6041': {'IndicationToken': '781T1'},
                             'LMP6042': {'IndicationToken': '777T1'},
                             'LMP6043': {'IndicationToken': '02T'},
                             'MCK6003': {'IndicationToken': 'MC1K'},
                             'MCK6004': {'IndicationToken': 'MC2K'}},
 'Luchessa-Panel': {'Encoding8002': {'Station': 'Luchessa'},
                    'Encoding8003': {'Station': 'Gilroy'},
                    'Encoding8004': {'Station': 'Carnadero'},
                    'Encoding8005': {'Station': 'Luchessa'},
                    'Encoding8006': {'Station': 'Luchessa'},
                    'LAMP8005': {'IndicationToken': '783T1'},
                    'LAMP8006': {'IndicationToken': '1NAT'},
                    'LAMP8007': {'IndicationToken': '795T1,01T,799T1'},
                    'LAMP8008': {'IndicationToken': 'MC1K'}},
 'Sargent': {'Exp2': {'Address': '0x27', 'Value': '0x27'}},
 'Sargent-Panel': {'COL1': {'Interlocking': 'Sargent'},
                   'LMP1': {'IndicationToken': 'HBAK'},
                   'LMP2': {'IndicationToken': '835T1'},
                   'LMP3': {'IndicationToken': 'Watsonville:837T1'},
                   'MCK1': {'IndicationToken': 'MC1K'}},
 'Watsonville-Panel': {'COL16034': {'Interlocking': 'Watsonville'},
                       'LMP16141': {'IndicationToken': '0101T'},
                       'LMP16142': {'IndicationToken': '0100T'},
                       'LMP16143': {'IndicationToken': '01T'}}}


def set_value(block: str, s: int, value: str) -> str:
    m = re.match(r'\(property "(?:[^"\\]|\\.)*" "', block[s:])
    vs = s + m.end()
    ve = block.index('"', vs)
    while block[ve - 1] == "\\":
        ve = block.index('"', ve + 1)
    return block[:vs] + value + block[ve:]


def restore_sheet(path: Path, wanted: dict[str, dict[str, str]], dry: bool, report: list[str]) -> int:
    text = path.read_text()
    edits, done = [], 0
    for s, e in blocks(text, "symbol", 1):
        b = text[s:e]
        ref = re.search(r'\n\t\t\(property "Reference" "((?:[^"\\]|\\.)*)"', b)
        if not ref or ref.group(1) not in wanted:
            continue
        nb = b
        for field, value in wanted[ref.group(1)].items():
            props = {re.match(r'\(property "((?:[^"\\]|\\.)*)" "((?:[^"\\]|\\.)*)"', nb[ps:pe]).group(1): (ps, pe)
                     for ps, pe in blocks(nb, "property", 2)}
            if field not in props:
                report.append(f"{path.name} {ref.group(1)}: no field {field} (skipped)")
                continue
            cur = re.match(r'\(property "[^"]*" "((?:[^"\\]|\\.)*)"', nb[props[field][0]:]).group(1)
            if cur != value:
                nb = set_value(nb, props[field][0], value)
                report.append(f"{path.name} {ref.group(1)}: {field} {cur!r} -> {value!r}")
                done += 1
        if nb != b:
            edits.append((s, e, nb))
    if edits and not dry:
        out, pos = [], 0
        for s, e, nb in edits:
            out += [text[pos:s], nb]
            pos = e
        path.write_text("".join(out) + text[pos:])
    missing = set(wanted) - {re.search(r'\n\t\t\(property "Reference" "([^"]*)"', text[s:e]).group(1)
                            for s, e in blocks(text, "symbol", 1) if '(property "Reference"' in text[s:e]}
    for r in sorted(missing):
        report.append(f"{path.name}: reference {r} not found")
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(SPCOAST.glob("~*.lck")):
        print("KiCad holds a lock on the project; close it first", file=sys.stderr)
        return 2
    report: list[str] = []
    total = sum(restore_sheet(SPCOAST / f"{sheet}.kicad_sch", wanted, a.dry_run, report) for sheet, wanted in TABLE.items())
    print("\n".join(report))
    print(f"{'would restore' if a.dry_run else 'restored'} {total} field values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
