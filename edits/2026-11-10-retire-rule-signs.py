"""Remove the retired rule-sign and END CTC symbols from Railroad-Trackplan (ADR 0013 §7.1, decision 3; Subdivision #113).

The GCOR Rule markers (Railroad 0ddd395) replaced them in every SPCoast sheet; the Kinds RULE_251, RULE_261, RULE_93,
RULE_105 and END_CTC are retired from the importer and the rules in the same change, with no bridge. This removes the
five top-level symbol blocks from the library file and nothing else. Sheets keep their own cached copies in
``lib_symbols`` until KiCad rewrites them, so no placement breaks; the archived per-project drawings read the old
``Railroad`` library, not this one.

Run from the Railroad repo with the Subdivision venv:

    uv run --project ~/Dropbox/workspace/FieldUnit-Subdivision python edits/2026-11-10-retire-rule-signs.py [--dry-run]

It refuses to touch the library while KiCad holds its lock (``symbols/~Railroad-Trackplan.kicad_sym.lck``). Before
committing, export a fresh netlist and diff it against one exported before the edit (``tools/contract/netlist_diff.py``)
and run ``tools/contract/lint_symbol_fields.py``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "symbols" / "Railroad-Trackplan.kicad_sym"
RETIRED = ("IRJ-END_CTC", "Rule93-Yard Limits", "Rule105-RestrictedSpeed", "Rule251-DoT-Left", "Rule251-DoT-Right",
           "Rule261-DoT-BiDirectional")


def block(name: str) -> re.Pattern:
    """A top-level symbol block as KiCad 10 writes it: one tab in, closed by the first ``\\n\\t)\\n`` (sub-units close
    deeper)."""
    return re.compile(r'\n\t\(symbol "' + re.escape(name) + r'"\n[\s\S]*?\n\t\)\n')


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    lock = LIB.with_name(f"~{LIB.name}.lck")
    if lock.exists():
        print(f"refusing: KiCad holds {lock}", file=sys.stderr)
        return 2
    text = LIB.read_text(encoding="utf-8")
    for name in RETIRED:
        matches = block(name).findall(text)
        if len(matches) != 1:
            print(f"refusing: {name!r} matched {len(matches)} blocks", file=sys.stderr)
            return 2
        text = block(name).sub("\n", text, count=1)
        print(f"removed symbol {name!r} ({len(matches[0])} characters)")
    if dry:
        print("dry run: nothing written")
        return 0
    LIB.write_text(text, encoding="utf-8")
    print(f"wrote {LIB}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
