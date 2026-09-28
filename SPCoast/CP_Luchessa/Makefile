SVGTOOL :=$(HOME)/Dropbox/workspace/FieldUnit-Subdivision/tools/render_plant_picture.py
JSONTOOL :=$(HOME)/Dropbox/workspace/FieldUnit-Subdivision/tools/parse_kicad_plant.py
LIB  :=$(HOME)/Dropbox/KiCad/InterlockingPlant/symbols/Railroad.kicad_sym
LAYOUT := "spcoast"
PROJECT  :=$(shell basename $$(PWD))
SCH  :=$(PROJECT).kicad_sch
SVG  :=$(PROJECT).svg
FIELD_JSON :=$(PROJECT)-field.json
PLANT_JSON :=$(PROJECT)-plant.json

all: 
	@echo "Run 'make ${SVG}' or 'make ${FIELD_JSON}' to generate the output files."

svg: $(SVG)
json: $(FIELD_JSON) $(PLANT_JSON)
debug:
	python $(TOOL) \
	--library "$(LIB)" \
	--schematic "$(SCH)" \
	--format text


$(SVG): $(SCH) $(LIB)
	python $(SVGTOOL) \
	--library "$(LIB)" \
	--schematic "$(SCH)" \
	--format board-svg \
	--output "$(SVG)"

$(FIELD_JSON): $(SCH) $(LIB)
	python $(JSONTOOL) \
	--library "$(LIB)" \
	--schematic "$(SCH)" \
	--format fieldunit-json \
  	--plant-name "$(PROJECT)" \
  	--plant-id $(LAYOUT).$(PROJECT) \
	--output "$(FIELD_JSON)"

$(PLANT_JSON): $(SCH) $(LIB)
	python $(JSONTOOL) \
	--library "$(LIB)" \
	--schematic "$(SCH)" \
	--format plant-model-json \
	--output "$(PLANT_JSON)"
