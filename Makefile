PYTHON ?= python3
ROOT ?= .
DBLOAD_TXT ?= data/plant-family.dbload.txt
DB_FILE ?= data/Australia.db

.PHONY: all db dbload module module-install clean

all: db

db: $(DB_FILE)

module:
	$(MAKE) -C module

module-install:
	$(MAKE) -C module install

$(DBLOAD_TXT): scripts/build-db-load-file.py $(wildcard data/*/*.txt) $(wildcard data/*/*/*.txt)
	$(PYTHON) scripts/build-db-load-file.py --root $(ROOT) --output $(DBLOAD_TXT)

$(DB_FILE): $(DBLOAD_TXT)
	db_load -T -t btree -f $(DBLOAD_TXT) $(DB_FILE)

dbload: $(DBLOAD_TXT)

clean:
	rm -f $(DB_FILE) $(DBLOAD_TXT)
	$(MAKE) -C module clean
