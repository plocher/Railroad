# Single Mast

`03-single-mast.kicad_sch`, page 4 of the Examples project. Drafted by `tools/examples/build_examples.py`
(FieldUnit-Subdivision); tidied by hand in KiCad.

## Intent

This page shows one controlled signal mast with one head. On the trackplan, Signal Mast Single 2 stands on an IRJ-Signal. In the field, Device-Mast-Single 2 drives a Device-Head-TypeD on its pin A; the head's APP feeds an Encoder-RYG whose G, Y and R inputs are CMRInet output bits 1, 2 and 3 of node UA3. In the office, signal lever 2 on desk column 3 sends NGS, HS and SGS and shows NGK, SGK and TEK through MAX7313 pins B2, B3, B4, B6, B7 and B8.

## Facts the compiler derives

| Fact | Value |
| --- | --- |
| Interlocking | Single Mast (from the sheet title) |
| CP Name | Single Mast |
| Mast | 2, single, CONTROLLED; Indications empty (demand derived) |
| Field mast | Device-Mast-Single 2; head position A -> Device-Head-TypeD (anonymous) -> Encoder-RYG |
| Head bits | ~{G} CMRInet UA3 OUT.1, ~{Y} OUT.2, ~{R} OUT.3 |
| Desk column | 3, CP Name Single Mast |
| Lever | PanelSignal 2 (MAX7313 0x22): controls 2NGS (B2), 2HS (B3), 2SGS (B4); indications 2NGK (B6), 2SGK (B7), 2TEK (B8) |

## Symbols

- `Plant401` Railroad-Trackplan:Interlocking `${TITLE}`
- `HOUSE401` Railroad-Trackplan:House
- `B401` Railroad-Trackplan:IRJ-Signal
- `S401` Railroad-Trackplan-Signals:Signal Mast Single `2`
- `DevMast401` Railroad-Field-Signals:Device-Mast-Single `2`
- `Head401` Railroad-Field-Signals:Device-Head-TypeD
- `ENC401` Railroad-Field-Signals:Encoder-RYG
- `CMRI401` Railroad-HardwareIO:Driver-CMRInet-OB
- `CMRI402` Railroad-HardwareIO:Driver-CMRInet-OB
- `CMRI403` Railroad-HardwareIO:Driver-CMRInet-OB
- `RIO401` Railroad-HardwareIO:Driver-CMRInet-Node
- `COL401` Railroad-Office:PanelColumn `3`
- `I2C401` Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc
- `SIG401` Railroad-Office:PanelSignal `2`

## TODO

- Milepost 0.0 on the House is a placeholder; no Milepost, NextCP or direction-of-traffic policy is drawn.
- no track is drawn on either side of the IRJ (its A and B pins are open); no track circuit, switch or opposing mast is drawn. The name 2 follows the talk, not the mast grammar (number, direction, head letters).
- node UA3 (NodeType C, 0 input and 1 output bytes) is a guess; the pages share the root sheet's one CMRInet line, so each takes its own UA.
- the head carries no Head letter and no Name on purpose (anonymous head on pin A, settled 2026-11-04); the compiler still reports both as missing.
- column 3 and I2C address 0x22 are placeholders: the pages share the root sheet's one desk, so each takes its own column and expander.
- the board lamp rows and the switch lever row are empty on purpose; the lever plate's own NGK/SGK/TEK lamps are its pins.
