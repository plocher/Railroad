# Railroad symbols: the user's manual

This manual says how to place the symbols of the six hand-maintained libraries in this folder.
A symbol's Description says what the symbol is. This manual says how to use it.
Symbols are grouped by pattern: Role, then Appliance or Kind, then the pin set.
Every symbol appears once, as `Library:Symbol` with its Description as it stands in the file.

## Terms

- **Signal indication.** The meaning of an aspect, as the rulebook states it. Examples: Stop, Restricting, Clear. This manual says "indication".
- **Aspect.** The appearance of a signal: the colours, positions and flashing of all its heads together. A head alone does not show an aspect.
- **Head.** One unit of lamps on a mast. It shows one part of an aspect. **Mast.** The structure that carries one or more heads.
- **Control point.** A named place where a dispatcher or operator controls train movements by controlled absolute signals.
- **Track circuit.** The section of track that one track relay detects, between insulated joints.
- **Code line.** The communication path between the CTC machine and the field units. It carries controls to the field and office indications to the office.
- **Control.** A function sent from the office to the field (`783NWS`). **Office indication.** A function sent from the field to the office (`783NWK`).

## Fields and pins common to every symbol

- **Role.** The class of the symbol. The tools read Role, never the symbol name. A symbol with no Role is a drawing only.
- **Name.** The identity of a named symbol. Its default is `${Value}`. Set Value; Name follows. Value itself is never read.
- **Kind.** The sub-class, where Role alone does not say what the symbol is. Fixed by the symbol, except on a mast.
- **Appliance.** What an APPLIANCE, DEVICE or PANEL symbol is: switch, track_circuit, mast, head, lamp, contact, lever, train_order. Fixed.
- **Style.** The variant inside an Appliance. Fixed by the symbol.
- **CP Name.** The control point the symbol belongs to. Empty means the sheet's interlocking.
- **Pin.<pin>.** The kind of value a function pin carries: binary, level, position, color, indication, message. Fixed.
- **Settings.** Every other field in lower_snake_case, for example `settle_ms`. Set them per placement; empty means the default.
- **Invert.** Names this symbol's pins whose sense is inverted. Fixed.
- A pin named `~{X}` is asserted low. A pin's electrical type is its direction: input, output or bidirectional.
- Membership pins join a net and carry no value: `Column`, `IOBus`, `Processor`, `Transport`, `Codeline`, `MC`, `CHAIN`.
- A device pin that meets a driver pin is an input of the device. Connections are read from the netlist, never from coordinates.

## Trackplan symbols

One interlocking's trackplan is one sheet. Role decides what is on it: TRACK, POLICY, APPLIANCE and the House.

### Track joints, ends and anchors (Role TRACK)
A joint bounds a track circuit; an end closes the drawn track; an anchor states a fact about the point it sits on.
Pins A and B are the two sides of a joint; wire track to each. EoT is the one track pin of an end. To is the track pin of an anchor.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:IRJ` | Insulated Rail Joint |
| `Railroad-Trackplan:IRJ_Diag` | Insulated Rail Joint |
| `Railroad-Trackplan:IRJ-Signal` | Insulated Rail Joint with Signal |
| `Railroad-Trackplan:IRJ-Signals` | Insulated Rail Joint with bidirectional Signals |
| `Railroad-Trackplan:IRJ-END_CTC` | |
| `Railroad-Trackplan:Bumper` | End of Track Bumper/Stop |
| `Railroad-Trackplan:Industry` | Track exists past this point, but is not drawn |
| `Railroad-Trackplan:Milepost` | Milepost: a track anchor carrying the milepost of the point it sits on. |
| `Railroad-Trackplan:NextCP` | Identifies the next control point on this track |
| `Railroad-Trackplan:NextCP Not Modeled` | Documents the logical connection of this track that isn't actually modeled |

- `IRJ` and `IRJ_Diag` (Kind IRJ) differ in glyph only; `IRJ_Diag` is drawn on a diagonal.
- `IRJ-Signal` has pin SIGNAL; `IRJ-Signals` has SIGNAL_A and SIGNAL_B. Wire a mast's SIGNAL pin to one. Set CP Name to the mast's control point.
- `IRJ-END_CTC` has pins CTC and DARK: the controlled side and the side beyond (usage to be confirmed).
- `Bumper` (Kind BUMPER) has no setting. `Industry` (Kind INDUSTRY): set Value to its name.
- `Milepost` has no pin. Set Value to the milepost.
- `NextCP` (Kind NEXT_CP): wire To to the track that leaves the interlocking. Set Value to the next interlocking's name; the Interlocking field follows. `Not Modeled` (Style off_layout) says the next interlocking is not drawn anywhere.

### Operating rules (Role POLICY)
A policy symbol states the rule that governs a track. Kind is the rule number. Direction is fixed: LEFT, RIGHT or BOTH.
Place one per governed track. Wire pin To (Rule 261: Track) to the governed track net.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Rule93-Yard Limits` | Yard Limits: Standard Code Rule 93, GCOR RULE 6.13: a designated section of the main track where trains and engines may operate without protecting against other movements, |
| `Railroad-Trackplan:Rule105-RestrictedSpeed` | Restricted speed: Standard Code Rule 105, GCOR 6.28: Movement on Other Than Main Track. This is the foundational rule governing most industrial tracks. It mandates that trains or engines must move at a speed that allows them to stop within half the range of vision short of a train, engine, car, stop signal, derail, or switch improperly lined. It also requires crew members to look out for track obstructions |
| `Railroad-Trackplan:Rule251-DoT-Left` | Rule 251 (Track Signaled in One Direction): Governs movements on tracks where signals are only configured for  one direction.  Under this rule, signal indications supersede the superiority of trains for movements operating with the current of traffic.  Moving against this traffic direction requires explicit authority (such as a train order or track warrant). |
| `Railroad-Trackplan:Rule251-DoT-Right` | Rule 251 (Track Signaled in One Direction): Governs movements on tracks where signals are only configured for  one direction.  Under this rule, signal indications supersede the superiority of trains for movements operating with the current of traffic.  Moving against this traffic direction requires explicit authority (such as a train order or track warrant). |
| `Railroad-Trackplan:Rule261-DoT-BiDirectional` | Track Signaled in Both Directions:  Governs bi-directional signal territory (often controlled by  Centralized Traffic Control, or CTC).  Under Rule 261, block signal  indications supersede train superiority for both opposing and following movements on the same track, allowing the dispatcher to dynamically change the direction of traffic by clearing signals. |
| `Railroad-Trackplan:Signal Mast Plate-G` | Rule 290 Grade - added to a NUMBER plate.  Allows heavy freight trains to bypass the physical stop required by Rule 291 and pass the red signal moving continuously at restricted speed (to avoid getting stuck on the grade). |
| `Railroad-Trackplan:Signal Mast Plate-R` | Rule 290 Restricting - added to a NUMBER plate.  Explicitly converts a standard automatic block signal's red aspect directly into a Restricting indication |

- The two plates (Kind RULE_290_G, RULE_290_R) have no Direction. Their pin To is wired to the mast they modify (usage to be confirmed).

### Structures (Role STRUCTURE)
A structure declares a named thing that owns or contains others. Kind says which. Set Value to its name.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Interlocking` | |
| `Railroad-Trackplan:House` | The Control Point Maintainer Bungalow (plus optional Maintainer Call) |
| `Railroad-Trackplan:Station` | A Station (Freight and/or Passenger) |
| `Railroad-Office:Railroad` | Attributes for the railroad itself |
| `Railroad-HardwareIO:Processor` | A processor: runs the logic of the units wired to its Processor pin and owns the Drivers on its IO_Bus |

- `Interlocking` (Kind INTERLOCKING): one per trackplan sheet (Luchessa). Wire Codeline to the code line and Processor to the processor that runs the logic.
- `House` (Kind CONTROL_POINT): one per control point. Set CP Name (CP Luchessa) and Milepost. Wire Codeline to the code line and MC to the MaintainerCall.
- `Station` (Kind STATION): set Milepost. No pin. `Railroad` (Kind RAILROAD): one per project; set Era, Railroad, Region, Rulebook. No pin.
- `Processor` (Kind PROCESSOR): one per processor; set Board. Pin Processor is the net its units attach to; pin IOBus is the bus its drivers sit on.

### Switches and derails (Role APPLIANCE, Appliance switch)
A switch appliance is a point in the track, named for the dispatcher. Place one per switch or derail.
Style says what it is: powered, manual, manual_sensed, lock, dual, derail.

- Set Value to the switch name (783). A lock shares its name with its switch. A dependent derail is named `<switch>D` (795D).
- Pins C, N, R are track: C the point end, N the normal leg, R the reverse leg. A derail has C and R only; R is the through pin.
- TC names the switch's OS track circuit; its default is `<Value>T1`. Set it when the circuit has another name. Indication is `<TC>K`, fixed.
- IndicationCeiling is the most favourable indication a route over the switch permits, one value per position (order to be confirmed). Fixed.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Switch_Powered` | |
| `Railroad-Trackplan:Switch_Powered_Diag` | |
| `Railroad-Trackplan:Switch_Powered_Small` | |
| `Railroad-Trackplan:Switch_Powered_NO_TC` | |
| `Railroad-Trackplan:Switch_Lock` | |
| `Railroad-Trackplan:Switch_Dual` | Dual-control switch: a powered switch the crew may also work by hand at the location, under a release from the dispatcher; while released the control is ignored and the switch is out of correspondence (E63). |
| `Railroad-Trackplan:Switch_Manual` | Manual switch, no motor or feedback |
| `Railroad-Trackplan:Switch_Manual_Sensed` | Manual switch, no motor but with N/R feedback |
| `Railroad-Trackplan:Derail` | Protective DERAIL for sidings. Does not imply an additional track circuit. Give it a unique Value for dispatcher control, or use associated mainline switch with a "D" suffix |
| `Railroad-Trackplan:Derail_TC` | Protective DERAIL for sidings WITH an associated Track Circuit. Give it a unique Value for dispatcher control, or use associated mainline switch with a "D" suffix |

- `Switch_Powered`, `_Diag` and `_Small` have the same fields; the glyphs differ. `_NO_TC`, `Switch_Manual`, `Switch_Manual_Sensed` and `Derail` have no OS circuit: TC and Indication are empty.
- A manual switch has IndicationCeiling RESTRICTING/RESTRICTING; a derail STOP/RESTRICTING.

### Track circuits (Role APPLIANCE, Appliance track_circuit)
A track circuit marker names the circuit of the track net it sits on. Place one per circuit.
Set Value to the circuit name (1NA). Indication is `<Name>K`, fixed.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Track Circuit` | |
| `Railroad-Trackplan:Track Circuit_RED` | |
| `Railroad-Trackplan:Track Circuit_Yellow` | |
| `Railroad-Trackplan:Track Circuit IR Boundary` | |
| `Railroad-Trackplan:Track Circuit_Virtual` | Virtual track circuit: an indication that aggregates the circuits listed in Members. |

- `Track Circuit`, `_RED` and `_Yellow` have pin TC; wire it to the track net. They differ in drawn colour only.
- `IR Boundary` (Style boundary) has pins A and B, one per side of the boundary (usage to be confirmed).
- `_Virtual` (Style virtual) has no pin. Set Members to a comma-separated list of circuit names. Display shows them.

### Masts drawn with trackplan heads (Role APPLIANCE, Appliance mast and head)
These masts carry their heads as trackplan symbols. Place one mast and one Signal Head per head pin.
Mast: set Value to the mast name (784EAB). Kind is fixed per symbol: CONTROLLED, ABSOLUTE or PERMISSIVE. Wire SIGNAL to an IRJ-Signal or IRJ-Signals SIGNAL pin. Wire each head pin (H, H1, H2) to a Signal Head's pin M.
Head: set Value to the head letter (A). Style is fixed: CL, CPL, LQ, UQ. The head device on the field sheet must have the same Style.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Signal Mast Single CONTROLLED` | |
| `Railroad-Trackplan:Signal Mast Single ABSOLUTE` | |
| `Railroad-Trackplan:Signal Mast Single PERMISSIVE` | |
| `Railroad-Trackplan:Signal Mast Double CONTROLLED` | |
| `Railroad-Trackplan:Signal Mast Dwarf CONTROLLED` | |
| `Railroad-Trackplan:Signal Head - CL` | Color light head: one light source showing one color at a time (searchlight roundel, or one RGB point in the model). Style CL (E65). |
| `Railroad-Trackplan:Signal Head - CPL` | Color-position light head: colored lamps in fixed positions, one lit at a time (three-lamp or multiplexed). Style CPL (E65). |
| `Railroad-Trackplan:Signal Head - Semaphore-LQ` | Lower-quadrant semaphore head, two positions: STOP (horizontal) and CLEAR (arm dropped). The aspect set is an era fact; see FieldUnit's primer section 17. |
| `Railroad-Trackplan:Signal Head - Semaphore-UQ` | Upper-quadrant semaphore head, three positions: STOP (horizontal), APPROACH (45 degrees), CLEAR (vertical). The aspect set is an era fact; see FieldUnit's primer section 17. |

### Masts with derived indications (Role APPLIANCE, Appliance mast, Indications)
These masts carry no head symbols; the head glyphs are picture. The heads are field devices on a field mast device of the same Name.
Place one per signal. Set Value to the mast name. Kind is fixed per symbol. Wire SIGNAL to an IRJ-Signal or IRJ-Signals.
Leave Indications empty: the indications the mast must show are derived. Fill it only with an explicit comma-separated list of indication names; the list replaces the derived set.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan-Signals:Signal Mast Single` | Signal mast with one head. |
| `Railroad-Trackplan-Signals:Signal Mast Single ABSOLUTE` | Absolute block signal mast with one head. |
| `Railroad-Trackplan-Signals:Signal Mast Single PERMISSIVE` | Permissive block signal mast with one head and a number plate. |
| `Railroad-Trackplan-Signals:Signal Mast Double` | Signal mast with two heads. |
| `Railroad-Trackplan-Signals:Signal Mast Triple` | Signal mast with three heads. |
| `Railroad-Trackplan-Signals:Signal Mast Dwarf` | Dwarf signal with one head. |
| `Railroad-Trackplan-Signals:Signal Mast Dwarf-Double` | Dwarf signal with two heads. |
| `Railroad-Trackplan-Signals:Stop` | Fixed stop signal. |

- Style is single, double, triple, dwarf, dwarf2 or stop_sign. Kind is CONTROLLED unless the name says ABSOLUTE or PERMISSIVE.
- `Stop` is ABSOLUTE with Indications fixed to `Stop`.

### Train order signal (Role APPLIANCE, Appliance train_order)
| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:Train Order Mast` | A Train Order signal or Order Board signals to the Engineer that new orders were available at the station |

- Set Value to the signal name and Station to the station it serves. Pin H is its head (usage to be confirmed).

### Non-vital lamps and contacts (Role APPLIANCE, pin MC)
These appliances have one pin, MC. They are the office's view of a non-vital input or output at a control point.

| Symbol | Description |
| --- | --- |
| `Railroad-Trackplan:AUXILIARY` | |
| `Railroad-Trackplan:Contact` | Contact: the generic non-vital input the office may see as <Value>K. Style says who consumes it (lock_request, button, door, ...). Complement of AUXILIARY. |
| `Railroad-Trackplan:MaintainerCall` | |

- `AUXILIARY` (Appliance lamp): set Value to its name. Indication is `<Name>K`, fixed. Wiring of MC (usage to be confirmed).
- `Contact` (Appliance contact): set Value to its name and Style to its consumer. Wiring of MC (usage to be confirmed).
- `MaintainerCall` (Appliance lamp, Style maintainer_call): set Value to the control point's name; Name is `<Value>MC`. Wire MC to the House's MC pin.

## Office symbols

The office sheet holds the CTC machine, its columns and plates, the transports and the encodings that ride them.

### The machine and its columns (Role OFFICE_UNIT, COLUMN)
| Symbol | Description |
| --- | --- |
| `Railroad-Office:OfficeUnit` | The OfficeUnit: the dispatcher's office logic and its desk; one per CTC machine. Its columns are its interlockings (ADR 0009). |
| `Railroad-Office:PanelColumn` | |

- `OfficeUnit`: place one. Set Value to the machine's name. Style is US&S. Wire Processor to the processor that runs the office logic.
- `PanelColumn`: one per desk column. Set Value to the column number; the Column field follows. Set CP Name to the control point the column serves. Wire each plate of the column to one of its eight Column pins.

### Lever plates (Role PANEL, Appliance lever, pin Column)
A plate is a device of the CTC machine in one column. Place one per lever or button on the desk.
Set Value to the name of the field appliance it serves (783). Wire Column to the PanelColumn.
Function pins are binary. An output pin is a lever contact; wire it to a driver input. An input pin is a lamp; wire it to a driver output.
`Control.<pin>` names the control a contact sends; `Indication.<pin>` names the office indication a lamp shows. Both are fixed; an empty one is a deliberate none.
A plate with lamps and contacts has two units: unit 1 contacts, unit 2 lamps. The units are not interchangeable.

| Symbol | Description |
| --- | --- |
| `Railroad-Office:PanelSwitch` | Lever plate for a dispatcher-controlled Switch (or Lock). Value cross-references the plant sheet's Switch appliance by name. NW/RW control+indication vocabulary is mandatory and type-fixed; this symbol declares only the physical realization. |
| `Railroad-Office:PanelSignal` | Lever plate for a dispatcher-controlled Signal. Value cross-references the plant sheet's SignalControl by name. |
| `Railroad-Office:PanelLock` | Lock lever plate. ~{WLS} is the R contact (release control); ~{UNUSED} the N contact, wired but consumed by nothing; ~{WLQK} the red request lamp; ~{WLK} the green locked lamp, lit while WLK is deasserted (Invert=WLK: WLK asserted means released, fail-safe). |
| `Railroad-Office:PanelMCall` | Maintainer Call Lever and Lamp. |
| `Railroad-Office:PanelCode` | Station CODE pushbutton (one-shot). One per multi-column CtcStation, regardless of how many columns it spans. |
| `Railroad-Office:PanelAuxiliary` | Generic 1-bit dispatcher-facing appliance (switch heater, bungalow door, etc).  ControlToken must be declared explicitly. |

- `PanelSwitch` (Style switch): contacts NWS, RWS; lamps NWK, RWK. `PanelSignal` (Style signal): contacts NGS, HS, SGS; lamps NGK, SGK, TEK.
- `PanelLock` (Style lock): contacts WLS, UNUSED; lamps WLQK, WLK. Indication.WLK is `!<Value>WLK`.
- `PanelMCall` (Style maintainer_call): contact MCS; lamp MCK. Set Value to the control point's name; Name is `<Value>MC`.
- `PanelCode` (Style code): contact CODE; Control.CODE is empty. `PanelAuxiliary` (Style non_vital): contact S; Control.S is `<Value>S`.

### Model board lamps (Role PANEL, Appliance lamp, Style board)
A model board lamp sits on the board, in no column, so it has no Column pin. Place one per lamp.
Set Value to the lamp's name. Set Indication to the boolean expression of office indications that lights it. Color is fixed.
Pin ~{LAMP} is a binary input; wire it to a driver output.

| Symbol | Description |
| --- | --- |
| `Railroad-Office:ModelLamp-RED` | One physical model board lamp. |
| `Railroad-Office:ModelLamp-YELLOW` | One physical model board lamp. |
| `Railroad-Office:ModelLamp-GREEN` | One physical model board lamp. |
| `Railroad-Office:ModelLamp-AMBER` | One physical model board lamp. |
| `Railroad-Office:ModelLamp-BLUE` | One physical model board lamp. |

### Transports (Role TRANSPORT)
A transport is a mechanism: a broker, a serial port, a pulse line. Place one per line. Set Value to its name. Kind is fixed.
Wire Processor to the processor that drives the line. Pin Transport is the net the encodings and nodes on this line attach to.

| Symbol | Description |
| --- | --- |
| `Railroad-Office:Transport-MQTT` | |
| `Railroad-Office:Transport-CMRInet` | |
| `Railroad-Office:Transport-LocoNet` | Using OPC_PEER 8-byte payload |
| `Railroad-Office:Transport-TimeCode` | US&S DC Long/Short Pulses |

- `MQTT` (Kind MQTT): set Broker. `CMRInet` (Kind CMRI): set Port and Baud. `LocoNet` (Kind LOCONET): set Port. `TimeCode` (Kind TIMECODE): no setting.

### Code line encodings (Role CODELINE_ENCODING)
A code line encoding rides a transport and provides a code line. Place one per code line. Set Value to the code line's name.
Wire Transport to the transport. Pin Codeline is the code line: wire every Interlocking and House on it to it.

| Symbol | Description |
| --- | --- |
| `Railroad-Office:Encoding-AAR` | Advanced Train Control System protocol AAR Specification 250 Message Formats |
| `Railroad-Office:Encoding-US&S-506` | US&S 506 time-coded pulses |
| `Railroad-Office:Encoding-Bits` | Bit (array of bytes) encoding |

- `AAR` (Kind AAR): Topic is the MQTT topic root; `<STRUCTURE:RAILROAD:Name>` in it takes the Railroad symbol's Name.
- `US&S-506` (Kind USS506): Chart (usage to be confirmed). `Bits` (Kind BITS): set ControlBytes and IndicationBytes; Chart (usage to be confirmed).

### I/O encodings (Role IO_ENCODING)
An I/O encoding states what rides a transport. It provides no net. Place one per transport that carries remote I/O. Set Value to its name. Wire Transport to the transport.

| Symbol | Description |
| --- | --- |
| `Railroad-Office:Encoding-JMRI` | JMRI's MQTT objects: an I/O encoding on an MQTT transport; provides an IOBus for JMRI drivers (ADR 0008). |
| `Railroad-Office:Encoding-CMRInet` | CMRInet polling: an I/O encoding on a CMRInet transport. It provides no net; the CMRInet nodes on the line provide the buses their bits sit on (ADR 0009 §3.5). |

- `JMRI` (Kind JMRI): Topic is the JMRI channel root. `CMRInet` (Kind CMRI): Version is the protocol version.

## Field symbols

A field sheet holds the devices of one interlocking: the hardware that acts on and senses its appliances, and the drivers that own the pins.
A device is matched to its trackplan appliance by Name. Set Value to the appliance's name.
Each unit of a device has one capability: one pin kind and one direction. Units are not interchangeable.

### Switch machines and locks (Role DEVICE, Appliance switch)
Place one per powered or sensed switch. Style lists the trackplan switch styles the device serves.
Pin M is the binary demand: asserted means REVERSE; wire it to a driver output. ~{N} and ~{R} are the point contacts; wire them to driver inputs.

| Symbol | Description |
| --- | --- |
| `Railroad-Field:Device-Switch` | Switch machine: M is a binary demand (asserted = REVERSE), ~{N} and ~{R} the point contacts. One device for a stall motor, a PWM motor and a servo: the driver on M's wire decides. |
| `Railroad-Field:Device-Switch-OS` | Switch machine with its OS circuit detector packaged on the same unit: Device-Switch plus ~{OCC}. |
| `Railroad-Field:Device-Switch-ManualSensed` | |
| `Railroad-Field:Device-Lock` | Electric lock mechanism: UNLOCK is the demand, ~{LOCKED} the optional plunger sense. Unwired, the driver simulates the sense (quality SIMULATED) after settle_ms. Shares its Value with the Device-Switch of the same switch. |

- `Device-Switch-OS` adds unit 3, ~{OCC}: the OS circuit's occupancy; wire it to a driver input.
- `Device-Switch-ManualSensed` (Style manual_sensed) has contacts only: ~{N}, ~{R}.
- `Device-Lock` (Style lock, dual): UNLOCK is the demand; ~{LOCKED} the sense. Set settle_ms when the sense is not wired.

### Track circuit detectors (Role DEVICE, Appliance track_circuit)
Place one per detected track circuit. Set Value to the circuit name. Pin ~{OCC} is the binary occupancy; wire it to a driver input.

| Symbol | Description |
| --- | --- |
| `Railroad-Field:Device-TrackCircuit-Current` | |
| `Railroad-Field:Device-TrackCircuit-Optical` | |

- `Optical` has hold_ms (default 1500): how long occupancy holds after the sensor clears.

### Lamps and contacts (Role DEVICE, Appliance lamp, contact)
| Symbol | Description |
| --- | --- |
| `Railroad-Field:Device-Lamp` | Lamp: one binary output, lit or dark. On a level-out pin they gain brightness and fade; on a pixel bus it carries an Address and colour. |
| `Railroad-Field:Device-Contact` | Contact: one binary input, the device of the Contact appliance. |

- `Device-Lamp`: set Value to the lamp's name. Pin ~{LAMP} is a binary input; wire it to a driver output. Set Address only on a pixel bus.
- `Device-Contact`: set Value to the Contact appliance's name. Pin ~{IN} is a binary output; wire it to a driver input.

### Local plates (Role DEVICE, Appliance lever)
A local plate is a lever or key at the location, not in the CTC machine, so it has no Column pin.
Set Value to the switch's name. Output pins are contacts; wire them to driver inputs. Input pins are lamps; wire them to driver outputs.

| Symbol | Description |
| --- | --- |
| `Railroad-Field:Local-Switch` | Lever plate for a dispatcher-controlled Switch (or Lock). Value cross-references the plant sheet's Switch appliance by name. NW/RW control+indication vocabulary is mandatory and type-fixed; this symbol declares only the physical realization. |
| `Railroad-Field:Local-Lock` | Fascia lock plate. ~{WLQ} is the crew's key (request); ~{WLQK} the red request lamp; ~{WLK} the green locked lamp, lit while WLK is deasserted (Invert=WLK). |

- `Local-Switch` (Style switch): contacts NWS, RWS; lamps NWK, RWK. `Local-Lock` (Style lock): contact WLQ; lamps WLQK, WLK; Invert is WLK.

### Whole-mast device (Role DEVICE, Appliance mast, pin IND)
A whole-mast device hands the mast's indication to a driver that takes a whole mast, or to head devices of the older shape.
Place one per mast of the trackplan-heads group. Set Value to the mast's name (836NAB).
Pin IND is an indication output. Wire it to a Driver-JMRI-SignalMast IND, or to the IND of each head device of the older shape.

| Symbol | Description |
| --- | --- |
| `Railroad-Field:Mast` | A mast as one device: IND is the mast's indication (the rule name), for drivers that take a whole mast, e.g. Driver-JMRI-SignalMast. Value = the trackplan mast's Value (836NAB, 774SAB): one Mast per trackplan mast, each protecting its own route; the head casts hang on IND. |

### Head devices of the older shape (Role DEVICE, Appliance head, hardware pins)
A head device of this shape makes its own lamps or arm. Place one per head of a mast of the trackplan-heads group.
Set Value to the mast name plus the head letter (784A). The last letter of Name is the head letter. Style is fixed and must match the trackplan head's Style.
Pin IND is the indication input; wire it to the whole-mast device's IND. Every other pin is a hardware input of one kind; wire each to a driver output.

| Symbol | Description |
| --- | --- |
| `Railroad-Field:Device-Head-CPL` | Mast indication to one CPL head's lamps, one wire each: R, Y, G. Head is the head letter, one the mast's name lists: Head B on mast 774NAB. The aspect is derived, not drawn. |
| `Railroad-Field:Device-Head-CPL-Encoded` | Mast indication to one CPL head's two-bit select code; the decoder on the head is field hardware. Head is the head letter. |
| `Railroad-Field:Device-Head-CPL-Pixel` | Mast indication to one CPL head's lamps, one wire each: R, Y, G. Head is the head letter, one the mast's name lists: Head B on mast 774NAB. The aspect is derived, not drawn. |
| `Railroad-Field:Device-Head-CL-RGB` | Mast indication to one head's aspect on one RGB LED, three legs. Head is the head letter; Style names the head style the rulebook's table is read for (CL, CPL, LQ, UQ). |
| `Railroad-Field:Device-Head-CL-Pixel` | Mast indication to one head's aspect as one color point, for a pixel or a lamp behind a roundel (E71). Head is the head letter; Style is fixed: CL. |
| `Railroad-Field:Device-Head-Semaphore-UQ` | Mast indication to one upper-quadrant semaphore head's arm position; the angles are this device's settings. Head is the head letter; Style is fixed: UQ. |
| `Railroad-Field:Device-Head-Semaphore-LQ` | Mast indication to one lower-quadrant semaphore head's arm position; the angles are this device's settings. Head is the head letter; Style is fixed: LQ. |

- `CPL`: binary ~{R}, ~{Y}, ~{G}. `CPL-Encoded`: binary S0, S1, the select code. `CPL-Pixel`: color ~{R}, ~{Y}, ~{G}, one pixel each.
- `CL-RGB`: binary ~{R}, ~{G}, ~{B}. `CL-Pixel`: color RGB, one pixel; set Address to its index on the chain.
- `Semaphore-UQ`, `-LQ`: position ARM; set stop_deg, approach_deg, clear_deg.
- The Head field is tolerated, not required. The head letter is read from Name.

### Field mast devices (Role DEVICE, Appliance mast, pins A, B, C)
A field mast device binds a mast of the derived-indications group to its heads. Place one per such mast.
Set Value to the trackplan mast's name (246AB). It has no Style, Kind or Indications: the pin set states the head count.
Pins A, B, C are indication outputs, one per head position, top down. Wire each to one anonymous head's IND.

| Symbol | Description |
| --- | --- |
| `Railroad-Field-Signals:Device-Mast-Single` | Field mast with one head position. |
| `Railroad-Field-Signals:Device-Mast-Double` | Field mast with two head positions. |
| `Railroad-Field-Signals:Device-Mast-Triple` | Field mast with three head positions. |
| `Railroad-Field-Signals:Device-Mast-Dwarf` | Field dwarf mast with one head position. |
| `Railroad-Field-Signals:Device-Mast-Dwarf-Double` | Field dwarf mast with two head positions. |

### Anonymous heads (Role DEVICE, Appliance head, pins IND and APP)
An anonymous head is one head of a given model at one position on a field mast. Place one per head position.
It has no Name. The mast pin its IND is wired to identifies it: the mast's Name plus the letter A, B or C. Value shows Style and is never read.
Style is the manufacturer model, fixed by the symbol. The symbol has no setting.
Pin IND is the indication input; wire it to one pin of the field mast device. Pin APP is the indication output, the head word; wire it to the APP of one or more encoders.

| Symbol | Description |
| --- | --- |
| `Railroad-Field-Signals:Device-Head-TypeD` | GRS Type D colour-light signal head. |
| `Railroad-Field-Signals:Device-Head-SA` | GRS SA searchlight signal head. |
| `Railroad-Field-Signals:Device-Head-H2` | US&S H-2 searchlight signal head. |
| `Railroad-Field-Signals:Device-Head-Semaphore-UQ` | Upper-quadrant semaphore signal head with three positions. |
| `Railroad-Field-Signals:Device-Head-Semaphore-LQ` | Lower-quadrant semaphore signal head with two positions. |

### Encoders (Role ENCODER)
An encoder turns a head word into hardware: lamps, a select code, pixels or a servo arm. Place one per head, or two when a semaphore has a lamp behind its blade.
It has no Name and no Appliance. The head it serves identifies it. Value shows Kind and is never read. Kind is fixed and names the hardware.
Pin APP is the one indication input; wire it to the head's APP. Every hardware-side pin is an input of kind binary or position; wire each to a driver output.
CHAIN is an attachment to a pixel chain; wire it to a Driver-GPIO-Pixel D.

| Symbol | Description |
| --- | --- |
| `Railroad-Field-Signals:Encoder-RYG` | Encoder for a signal head with red, yellow and green lamps. |
| `Railroad-Field-Signals:Encoder-RGB` | Encoder for a signal head with one tricolour LED. |
| `Railroad-Field-Signals:Encoder-3MUX2A` | Encoder for a 3MUX2A decoder. |
| `Railroad-Field-Signals:Encoder-Lamp` | Encoder for one lamp. |
| `Railroad-Field-Signals:Encoder-Pixel-RYG` | Encoder for three pixels on one chain, one pixel for each lamp colour. |
| `Railroad-Field-Signals:Encoder-Pixel-RGB` | Encoder for one pixel on a chain. |
| `Railroad-Field-Signals:Encoder-Servo` | Encoder for a semaphore blade on a servo. |

- `RYG` (Kind RYG): binary ~{R}, ~{Y}, ~{G}. `RGB` (Kind RGB): binary ~{R}, ~{G}, ~{B}. `3MUX2A` (Kind 3MUX2A): binary S0, S1, the select code.
- `Lamp` (Kind LAMP): binary ~{LAMP}, lit for every head word except DARK.
- `Pixel-RYG` (Kind PIXEL_RYG): CHAIN; set Address.R, Address.Y, Address.G to each lamp's pixel index. `Pixel-RGB` (Kind PIXEL_RGB): CHAIN; set Address to the pixel index.
- `Servo` (Kind SERVO): position ARM; set stop_deg, approach_deg, clear_deg.

## Hardware I/O symbols

A driver owns pins. It sits on an IOBus and hands its pins to devices, encoders and plates. IC names the chip or the encoding. `Pin.<pin>` states each pin's kind.
Wire IOBus to the Processor's IOBus, or to a CMRInet node's IOBus. The devices on a driver's pins run on that processor.

### I2C chips (Role IODRIVER, pins A1 to B8)
Place one per chip. Set Address to the chip's I2C address. The sixteen pins are in four units of four; the symbol fixes their kind.

| Symbol | Description |
| --- | --- |
| `Railroad-HardwareIO:Driver-I2C-MAX7311` | 16 bit I2C digital IO Expander (I2C addresses 0x10 to 0x4F 100kΩ Pullups Open-Drain Interrupt Output |
| `Railroad-HardwareIO:Driver-I2C-MAX7313` | 16 bit I2C digital IO Expander (I2C addresses 0x10 to 0x4F |
| `Railroad-HardwareIO:Driver-I2C-MAX7313-SPCoastcTc` | One physical IO expander instance bound to a PanelColumn. Address is 0x10 to 0x4F |
| `Railroad-HardwareIO:Driver-I2C-MCP23017` | 16 bit I2C digital IO Expander  Address is 0x20 to 0x27 |
| `Railroad-HardwareIO:Driver-I2C-PCA9685-PWM` | PCA9685 as a lamp driver: sixteen level-out pins at one frequency_hz. A servo on it is refused. |
| `Railroad-HardwareIO:Driver-I2C-PCA9685-Servo` | PCA9685 as a servo driver: sixteen position-out pins at 50 Hz, pulse min_us to max_us. A lamp on it is refused. |

- `MAX7311`, `MAX7313`, `MCP23017`: binary, bidirectional pins; the device that lands on a pin sets its direction.
- `MAX7313-SPCoastcTc`: one unit with each pin's direction fixed to the desk column's wiring. Wire the column's plates to it.
- `PCA9685-PWM` (IC PCA9685): level outputs; set frequency_hz; wire lamps to it. `PCA9685-Servo`: position outputs; set min_us and max_us; wire ARM pins to it.

### Processor pins (Role IODRIVER, IC GPIO)
Place one per processor pin in use. Set Address to the board core's pin name. Pin D is the one function pin.

| Symbol | Description |
| --- | --- |
| `Railroad-HardwareIO:Driver-GPIO-Digital` | Processor pin used as a digital input or output, by what lands on it. Address = the board core's pin name |
| `Railroad-HardwareIO:Driver-GPIO-Pixel` | Processor pin driving a pixel chain: a bus, one colour-out slot per Address. Address = the board core's pin name. |

- `Digital`: D is binary, bidirectional. `Pixel`: D is color, the chain; wire pixel encoders' CHAIN pins and older heads' pixel pins to it.

### CMRInet node and bits (Role IODRIVER, IC CMRI)
A node is a driver on a CMRInet line that provides the IOBus its bits sit on. A bit is one input or output of that node.
Place one node per CMRInet node and one bit symbol per bit in use.

| Symbol | Description |
| --- | --- |
| `Railroad-HardwareIO:Driver-CMRInet-Node` | A CMRInet node: a driver on the CMRInet line, addressed by its UA, providing the IOBus its bits sit on; declares NodeType (C, M, N) and its IB/OB byte arrays, checked against the bits in use (ADR 0009 §3.5). |
| `Railroad-HardwareIO:Driver-CMRInet-IB` | CMRInet digital input: one bit of the IB array of the CMRInet node whose IOBus it sits on. Bit = the bit number; Node = the node's UA, only when a sheet holds two nodes (ADR 0009). |
| `Railroad-HardwareIO:Driver-CMRInet-OB` | CMRInet digital output: one bit of the OB array of the CMRInet node whose IOBus it sits on. Bit = the bit number; Node = the node's UA, only when a sheet holds two nodes (ADR 0009). |

- `Node` (Kind NODE): set Address to the UA, NodeType to C, M or N, InputBytes and OutputBytes. Wire Transport to the CMRInet transport. Pin IOBus is the bus for its bits. The Transport field (usage to be confirmed).
- `IB` (Kind IB): D is a binary input to the node; wire a device output to it. `OB` (Kind OB): D is a binary output; wire a device input to it. Set Bit; set Node only when the sheet holds two nodes.

### JMRI objects over MQTT (Role IODRIVER, IC MQTT-JMRI)
A JMRI driver is one JMRI object on an MQTT transport. Kind is the object class. Place one per object.
Address is the JMRI object name. Leave it empty to name the object after the device the driver serves.

| Symbol | Description |
| --- | --- |
| `Railroad-HardwareIO:Driver-JMRI-Turnout` | JMRI MQTT turnout command (CLOSED/THROWN). Address = the JMRI turnout name; empty = the switch this driver serves. |
| `Railroad-HardwareIO:Driver-JMRI-Turnout-Feedback` | JMRI MQTT turnout feedback (CLOSED/THROWN/INCONSISTENT/UNKNOWN) as N and R. Address as Driver-JMRI-Turnout. |
| `Railroad-HardwareIO:Driver-JMRI-Sensor` | JMRI MQTT sensor published by the FieldUnit (ACTIVE/INACTIVE). Address = the JMRI sensor name; empty = the circuit this driver serves. |
| `Railroad-HardwareIO:Driver-JMRI-Sensor-Feedback` | JMRI MQTT sensor read by the FieldUnit (ACTIVE/INACTIVE). Address as Driver-JMRI-Sensor. |
| `Railroad-HardwareIO:Driver-JMRI-Light` | JMRI MQTT light driven by the FieldUnit: ON (OFF/ON) and INTENSITY (a level, for a variable light). No Address: the JMRI object is named by the lamp this driver serves (ADR 0005 R11); Address overrides it. |
| `Railroad-HardwareIO:Driver-JMRI-SignalMast` | JMRI MQTT signal mast: sends the mast's indication as JMRI's aspect name, with Lit and Held from the FieldUnit. Address = the JMRI mast name; empty = the mast this driver serves. |

- `Turnout` (Kind TURNOUT): M, binary output; wire a Device-Switch M to it. `Turnout-Feedback`: ~{N}, ~{R}, binary inputs; wire the switch's contacts to them.
- `Sensor` (Kind SENSOR): S, binary output, the FieldUnit publishes; wire a detector's ~{OCC} to it. `Sensor-Feedback`: S, binary input, the FieldUnit reads.
- `Light` (Kind LIGHT): ON, binary; INTENSITY, level. `SignalMast` (Kind SIGNALMAST): IND, indication input; wire a whole-mast device's IND to it.

### Settings on a net (Role SETTING)
| Symbol | Description |
| --- | --- |
| `Railroad-HardwareIO:Setting` | Setting: attaches settings to a net; everything on the net inherits them. Value is a short displayed name, Description the reason, every other field one setting. |

- Place one on a net to give every symbol on the net the same settings. Set Value to a short name. Add one field per setting, in lower_snake_case. Wire its one pin, net, to the net.
