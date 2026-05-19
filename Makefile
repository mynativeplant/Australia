PYTHON ?= python3
ROOT ?= .
DB_DIR ?= db
DBLOAD_TXT ?= $(DB_DIR)/plant-family.dbload.txt
DB_FILE ?= $(DB_DIR)/Australia.db

.PHONY: all db dbload module module-install clean

all: db

db: $(DB_FILE)

module:
	$(MAKE) -C module

module-install:
	$(MAKE) -C module install

dbload:
	$(PYTHON) scripts/build-db-load-file.py --root $(ROOT) --output $(DBLOAD_TXT)

$(DB_FILE): dbload
	mkdir -p $(DB_DIR)
	db_load -T -t btree -f $(DBLOAD_TXT) $(DB_FILE)

clean:
	rm -f $(DB_FILE) $(DBLOAD_TXT)
	$(MAKE) -C module clean
