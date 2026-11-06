# Track Circuit

`01-track-circuit.kicad_sch`, page 2 of the Examples project. Drafted by `tools/examples/build_examples.py`
(FieldUnit-Subdivision); tidied by hand in KiCad.

## Intent

This page shows one track circuit. On the trackplan, two IRJ-Signal symbols bound the circuit and a Track Circuit symbol names it 1T. In the field, a Device-TrackCircuit-Optical named 1T reports occupancy on CMRInet input bit 1 of node UA1. In the office, a yellow board lamp on desk column 1 shows the indication 1TK through MAX7313 pin A5.

## Facts the compiler derives

| Fact | Value |
| --- | --- |
| Interlocking | Track Circuit (from the sheet title) |
| CP Name | Track Circuit |
| Track circuit | 1T, indication 1TK |
| Field device | Device-TrackCircuit-Optical 1T, ~{OCC} on CMRInet UA1 IN.1 |
| Desk column | 1, CP Name Track Circuit |
| Board lamp | TRACK (yellow), Indication 1TK, MAX7313 0x20 pin A5 |

## Symbols

- `Plant201` Railroad-Trackplan:Interlocking `${TITLE}`
- `HOUSE201` Railroad-Trackplan:House
- `B201` Railroad-Trackplan:IRJ-Signal
- `B202` Railroad-Trackplan:IRJ-Signal
- `TC201` Railroad-Trackplan:Track Circuit `1T`
- `DevTC201` Railroad-Field:Device-TrackCircuit-Optical `1T`
- `CMRI201` Railroad-HardwareIO:Driver-CMRInet-IB
- `RIO201` Railroad-HardwareIO:Driver-CMRInet-Node
- `COL201` Railroad-Office:PanelColumn `1`
- `I2C201` Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc
- `LAMP201` Railroad-Office:ModelLamp-YELLOW `TRACK`

## TODO

- Milepost 0.0 on the House is a placeholder; no Milepost, NextCP or direction-of-traffic policy is drawn.
- no track is drawn beyond either IRJ (their outer pins are open), and both IRJ-Signal SIGNAL pins are open (no masts on this page).
- node UA1 (NodeType C, 1 input and 0 output bytes) is a guess; the pages share the root sheet's one CMRInet line, so each takes its own UA.
- column 1 and I2C address 0x20 are placeholders: the pages share the root sheet's one desk, so each takes its own column and expander.
- lamp row 1 (OS, red) and row 3 are empty on purpose; the switch and signal lever rows are empty.
