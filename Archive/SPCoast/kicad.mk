# Shared make rules for SPCoast KiCad projects.
#
# Experimental home: expected to move into FieldUnit-Subdivision/tools once the
# plant and desk flows settle. A project Makefile sets KIND and includes this:
#
#   KIND := plant        # or: desk
#   include ../kicad.mk
#
# Override any ?= variable on the command line or in the environment.

PROJECT     ?= $(notdir $(CURDIR))
SUBDIVISION ?= $(HOME)/Dropbox/workspace/FieldUnit-Subdivision
SYMBOLS     ?= $(HOME)/Dropbox/KiCad/InterlockingPlant/symbols
PYTHON      ?= python3
KICAD_CLI   ?= $(firstword $(wildcard /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli) kicad-cli)
export KICAD_CLI

SCH := $(PROJECT).kicad_sch
NET := $(PROJECT).net

.PHONY: help netlist clean

help:
	@echo "$(PROJECT) ($(KIND)) targets:"
	@echo "  netlist   regenerate $(NET) from $(SCH) via kicad-cli"
	@$(if $(filter plant,$(KIND)),echo "  json      $(PROJECT)-field.json + $(PROJECT)-plant.json"; echo "  svg       $(PROJECT).svg board picture"; echo "  debug     plant graph inventory (text)"; echo "  all       json + svg")
	@echo "  clean     remove generated netlist"

netlist: $(NET)

# Netlist is regenerated whenever the schematic is newer.
$(NET): $(SCH)
	"$(KICAD_CLI)" sch export netlist --output "$@" "$<"

clean:
	rm -f "$(NET)"

# ---------------------------------------------------------------- plant
ifeq ($(KIND),plant)

LIB        ?= $(SYMBOLS)/Railroad.kicad_sym
PLANT_NAME ?= $(PROJECT)
PLANT_ID   ?= spcoast.$(PROJECT)
PLANT_TOOL := $(SUBDIVISION)/tools/parse_kicad_plant.py
SVG_TOOL   := $(SUBDIVISION)/tools/render_plant_picture.py

SVG        := $(PROJECT).svg
FIELD_JSON := $(PROJECT)-field.json
PLANT_JSON := $(PROJECT)-plant.json

PLANT_ARGS = --library "$(LIB)" --schematic "$(SCH)" --netlist "$(NET)" \
             --plant-name "$(PLANT_NAME)" --plant-id "$(PLANT_ID)"

.PHONY: all json svg debug

all: json svg
json: $(FIELD_JSON) $(PLANT_JSON)
svg: $(SVG)

debug: $(NET)
	$(PYTHON) "$(PLANT_TOOL)" $(PLANT_ARGS) --format text

$(FIELD_JSON): $(NET) $(SCH) $(LIB)
	$(PYTHON) "$(PLANT_TOOL)" $(PLANT_ARGS) --format fieldunit-json --output "$@"

$(PLANT_JSON): $(NET) $(SCH) $(LIB)
	$(PYTHON) "$(PLANT_TOOL)" $(PLANT_ARGS) --format plant-model-json --output "$@"

# board-svg needs schematic placements; the tool accepts only one source.
$(SVG): $(SCH) $(LIB)
	$(PYTHON) "$(SVG_TOOL)" --library "$(LIB)" --schematic "$(SCH)" --format board-svg --output "$@"

endif

# ----------------------------------------------------------------- desk
ifeq ($(KIND),desk)

LIB ?= $(SYMBOLS)/RailroadPanel.kicad_sym

# Desk derivation (panel binding → sketch) is not designed yet; only the
# netlist is produced for now.

endif
