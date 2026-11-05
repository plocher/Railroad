# Powered Switch

`02-powered-switch.kicad_sch`, page 3 of the Examples project. Drafted by `tools/examples/build_examples.py`
(FieldUnit-Subdivision); tidied by hand in KiCad.

## Intent

This page shows one powered switch. On the trackplan, Switch_Powered 1 sits between an IRJ-Signal on each main-track side and an IRJ on the reverse leg; its TC field names the OS circuit 1T1. In the field, a Device-Switch-OS named 1 takes its motor bit from CMRInet output bit 1 and reports N, R and OCC on input bits 1, 2 and 3 of node UA2. In the office, lever 1 on desk column 2 sends NWS and RWS and shows NWK and RWK through MAX7313 pins A8, A7, A1 and A2; a red OS lamp shows 1T1K through pin A4.

## Facts the compiler derives

| Fact | Value |
| --- | --- |
| Interlocking | Powered Switch (from the sheet title) |
| CP Name | Powered Switch |
| Switch | 1, powered; OS circuit 1T1 (TC field ${VALUE}T1); indication 1T1K |
| Field device | Device-Switch-OS 1: M on CMRInet UA2 OUT.1; ~{N} IN.1, ~{R} IN.2, ~{OCC} IN.3 |
| Desk column | 2, CP Name Powered Switch |
| Lever | PanelSwitch 1 (MAX7313 0x21): controls 1NWS (A8), 1RWS (A7); indications 1NWK (A1), 1RWK (A2) |
| Board lamp | OS (red), Indication 1T1K, MAX7313 0x21 pin A4 |

## Symbols

- `Plant301` Railroad-Trackplan:Interlocking `${TITLE}`
- `HOUSE301` Railroad-Trackplan:House
- `SW301` Railroad-Trackplan:Switch_Powered `1`
- `B301` Railroad-Trackplan:IRJ-Signal
- `B302` Railroad-Trackplan:IRJ-Signal
- `B303` Railroad-Trackplan:IRJ
- `DevSW301` Railroad-Field:Device-Switch-OS `1`
- `CMRI301` Railroad-HardwareIO:Driver-CMRInet-OB
- `CMRI302` Railroad-HardwareIO:Driver-CMRInet-IB
- `CMRI303` Railroad-HardwareIO:Driver-CMRInet-IB
- `CMRI304` Railroad-HardwareIO:Driver-CMRInet-IB
- `RIO301` Railroad-HardwareIO:Driver-CMRInet-Node
- `COL301` Railroad-Office:PanelColumn `2`
- `I2C301` Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc
- `SW302` Railroad-Office:PanelSwitch `1`
- `LAMP301` Railroad-Office:ModelLamp-RED `OS`

## TODO

- Milepost 0.0 on the House is a placeholder; no Milepost, NextCP or direction-of-traffic policy is drawn.
- no track is drawn beyond the IRJs (their outer pins are open); both IRJ-Signal SIGNAL pins are open (no masts on this page); the plain IRJ on the reverse leg copies Gilroy Caltrain 771.
- node UA2 (NodeType C, 1 input and 1 output bytes) is a guess; the pages share the root sheet's one CMRInet line, so each takes its own UA.
- column 2 and I2C address 0x21 are placeholders: the pages share the root sheet's one desk, so each takes its own column and expander.
- lamp rows 2 and 3 and the signal lever row are empty on purpose.
