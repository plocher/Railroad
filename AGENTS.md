# AGENTS.md

Guidance for agentic coders working in the KiCad `Railroad` repo.

## What this repo is

KiCad 10 projects that serve as the **design source of truth** for SPCoast
railroad signalling, not as PCBs. They are schematics that tools parse into data.

```
SPCoast/
  Luchessa/      interlocking plant drawing (Railroad symbols) → plant JSON, board SVG
  South-cTc/     dispatcher desk (RailroadPanel symbols) → desk I/O binding (tooling TBD)
```

- **Plant projects** (`<Interlocking>`, e.g. `Luchessa`) draw one interlocking's track topology: switches, derails, track circuits, masts and heads, MAIN HOUSEs, rule markers. Pins are passive; wires form the topology.
- **Desk projects** draw the cTc machine: columns, levers, lamps, code buttons and the I/O expander bit each one lands on. Pins are typed in/out. Connections are made by pins touching; there are no wires.
- **Naming: interlocking vs controlled point.** An interlocking (`Luchessa`) contains one or more controlled points, each a MAIN HOUSE whose Value is `CP <Name>` (`CP Luchessa`, `CP Gilroy`, `CP Carnadero`). One desk column is one CP. The interlocking and one of its CPs may share a base name; keep the `CP ` prefix on CPs and never on interlockings. Names are case-preserved when produced; consumers compare them case-insensitively.
- Desk and plant are linked **only by name**: a panel appliance's Value must equal the plant appliance's Value.
- **Value is the name; Reference is not.** KiCad re-annotates References freely (`SW784` may hold switch `783`). Tools must never derive or check names from References.

## External dependencies (outside this repo)

- Symbol libraries: `~/Dropbox/KiCad/InterlockingPlant/symbols/{Railroad,RailroadPanel}.kicad_sym`. They are registered in the global KiCad 10 `sym-lib-table` and are not in git. They are evolving and expected to move into FieldUnit-Subdivision. **Do not copy them into this repo.** `.bak` files next to them are manual snapshots.
- Tools: `~/Dropbox/workspace/FieldUnit-Subdivision/tools/`. Its AGENTS.md documents the symbol and field conventions the compiler enforces.
- Firmware consumer: `~/Dropbox/Arduino/libraries/FieldUnit/examples/spcoast_ctc`.

## Generating outputs

Each project has a two-line `Makefile` that sets `KIND` (`plant` or `desk`) and
includes the shared rules in `SPCoast/kicad.mk`. That file is experimental and
is expected to move into FieldUnit-Subdivision `tools/`. Put new rules there,
not in project Makefiles.

```zsh
make            # list targets for this project
make netlist    # <X>.net via kicad-cli; rebuilt only when <X>.kicad_sch is newer
make json       # plant: <X>-field.json (FieldUnit projection) + <X>-plant.json (portable model)
make svg        # plant: <X>.svg board picture
make all        # plant: json + svg
make debug      # plant: text inventory from the plant compiler
```

- Regenerate after every schematic edit; make dependencies handle ordering.
- `.net` files are gitignored build products. JSON and SVG are committed so they can be reviewed.
- The authoritative station JSON lives in FieldUnit-Subdivision `profiles/spcoast_south/cps/generated/`, not here. Never hand-edit generated JSON.
- Overridable variables: `KICAD_CLI` (default: KiCad.app bundle, then PATH), `SUBDIVISION`, `SYMBOLS`, `PYTHON`, `PLANT_NAME`, `PLANT_ID`.
- `kicad-cli` prints harmless Homebrew Fontconfig warnings to stderr.
- Desk projects produce only the netlist so far; desk derivation is being designed.

## Desk (South-cTc) conventions

- `CtcMachine`: one per desk (`Columns`, `Type`).
- `PanelColumn`: Value is the desk column number; `Interlocking` names the station.
- `PanelColumn-MAX7313`: an I/O expander instance. Its Value is that expander's address or index on its bus (`BusKind`). Pin N is bit N-1; pin direction (in/out) is part of the symbol.
- The schematic is the source for which expander, bit and polarity each panel appliance uses. Do not derive an expander from a column number or from any other convention. Today the column ↔ expander link is implied only by placement. Making it explicit is open work.
- Tokens:
  - `…S` is a control (lever to field): NWS, RWS, NGS, HS, SGS, CODE, ControlToken e.g. `MC1S`.
  - `…K` is an indication (field to lamp): NWK, RWK, NGK, SGK, TEK.
- `PanelLamp-*`: `IndicationToken` is the comma-separated list of indications OR'd onto the lamp (e.g. `795T1,2NAA,799T1`, `MC1K`). Value is only a descriptive label (OS, TRACK, MC, ...) and nothing reads it.
- Unused expander bits carry no-connect markers.

## Known debt, not conventions

Existing code sometimes takes shortcuts, e.g. `spcoast_ctc` addresses expanders as `base + (col-1)` with fixed bit constants. Those shortcuts are defects to remove, not rules for the schematics to follow. When the schematic and such code disagree, raise it; do not bend the schematic to fit the code.

## Safety rules for agents

- **KiCad is often open.** If `~<name>.kicad_sch.lck` / `~<name>.kicad_pro.lck` exist, do not write the `.kicad_sch`/`.kicad_pro`; ask the user to edit in KiCad. Reading is fine. Prefer the `.net`, and regenerate it if it is older than the schematic.
- Read connectivity from the netlist or ERC, never from coordinates.
- Commit only source: `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `Makefile`, `kicad.mk`, and deliberate generated artifacts. `.gitignore` excludes backups, `*.bak-*`, `~*.lck`, `*.kicad_prl`, `*.history/`, `*.net`, `*.pdf` and `*.zip`. Use `git ls-files -i -c --exclude-standard` to catch anything that slips in.
- Use Conventional Commits (`feat(kicad):`, `chore:`), matching the sibling repos.

## Roadmap (South-cTc)

- Extend from Luchessa (columns 5–7) to all 14 columns and 7 stations.
- Make the column ↔ expander binding explicit.
- Add the Subdivision tool (and `KIND := desk` rules in `kicad.mk`) that turns the desk (and plant) schematics into a generated, compiled and uploaded desk sketch.
