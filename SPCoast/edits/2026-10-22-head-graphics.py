#!/usr/bin/env python3
"""Head graphics, 2026-10-22: the head pictograms lost in the 2026-10-17/18 cast refactor go back into the cast symbols.

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python SPCoast/edits/2026-10-22-head-graphics.py [--dry-run]

Source: Railroad-Field.kicad_sym at commit 3fef4ad (2026-10-13, the six-head set): Device-Head-CPL (three colored
lamps), Device-Head-CL (the colored-segment lens), Device-Head-Semaphore (the arm). Only the pictogram primitives
at the left end of the body are taken (x < -15), shifted 1.27 right to clear the owner's direction arrow; the
semaphore's upper-half pictogram is centred on the one-unit cast body. Targets: Cast-Head-CPL-Encoded and
Cast-Head-CPL <- CPL; Cast-Head-RGB and Cast-Head-Color <- CL; Cast-Head-Semaphore <- Semaphore. The owner fine
tunes by hand. Graphics do not touch connectivity; the gate is that the library and every sheet still export.
KiCad must be closed.
"""
import argparse, importlib.util, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("seams", HERE / "2026-10-21-explicit-seams.py")
es = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(es)
cc = es.cc
FIELD = "Railroad-Field"
SOURCE = {"Cast-Head-CPL-Encoded": ("Device-Head-CPL", False, 1.27, 0.0),
          "Cast-Head-CPL": ("Device-Head-CPL", False, 1.27, 0.0),
          "Cast-Head-RGB": ("Device-Head-CL", False, 1.27, 0.0),
          "Cast-Head-Color": ("Device-Head-CL", False, 1.27, 0.0),
          "Cast-Head-Semaphore": ("Device-Head-Semaphore", True, 1.27, -1.27)}     # the arm's upper-half unit, centred
COORD = re.compile(r"\((xy|center|start|mid|end) ([-\d.]+) ([-\d.]+)\)")


def pictogram(old_lib: str, symbol: str, upper_half: bool, dx: float, dy: float) -> list[str]:
    """The pictogram primitives of every unit of the old symbol: left-end graphics only (x < -15)."""
    s, e = cc.top_symbols(old_lib, 1)[symbol]
    b = old_lib[s:e]
    out = []
    for m in re.finditer(r"\n\t\t\t\((circle|arc|polyline)\n[\s\S]*?\n\t\t\t\)", b):
        prim = m.group(0)
        pts = [(float(x), float(y)) for _, x, y in COORD.findall(prim)]
        if not pts or max(x for x, _ in pts) > -15:
            continue                                  # the right-end indication arrows are not the pictogram
        if upper_half and min(y for _, y in pts) < 0:
            continue                                  # the semaphore's lower-half unit
        prim = COORD.sub(lambda k: f"({k.group(1)} {cc.num(float(k.group(2)) + dx)} {cc.num(float(k.group(3)) + dy)})", prim)
        out.append(prim)
    assert out, symbol
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if list(es.LIBDIR.glob("~*.lck")) or list(es.SPCOAST.glob("~*.lck")):
        print("KiCad holds a lock; close it first", file=sys.stderr); return 2
    old = subprocess.run(["git", "-C", str(es.LIBDIR.parent), "show", f"3fef4ad:symbols/{FIELD}.kicad_sym"],
                         capture_output=True, text=True, check=True).stdout
    path = es.LIBDIR / f"{FIELD}.kicad_sym"; lib = path.read_text()
    for target, (src, upper, dx, dy) in SOURCE.items():
        prims = pictogram(old, src, upper, dx, dy)
        s, e = cc.top_symbols(lib, 1)[target]; b = lib[s:e]
        us = b.index(f'(symbol "{target}_0_1"'); ue = es.end_of(b, us)
        ub = b[us:ue]
        assert "(circle" not in ub and "(arc" not in ub, f"{target} already carries a pictogram"
        new_ub = ub[:-len("\n\t\t)")] + "".join(prims) + "\n\t\t)"
        assert ub.endswith("\n\t\t)")
        lib = cc.splice(lib, [(s + us, s + ue, new_ub)])
        print(f"{target}: {len(prims)} primitives from {src}, shifted ({dx}, {dy})")
    if a.dry_run:
        print("dry run: nothing written"); return 0
    path.write_text(lib)
    print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
