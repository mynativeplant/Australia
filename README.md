# Australian Native Plant Repository

This project aims to create an open-source Git repository of Australian native plants that includes species, hybrids, and cultivars. The goal is to provide a shared plant list that others can reuse when building applications, without each project needing to discover, curate, and maintain its own separate database.

Existing plant lists usually focus on botany or gardening. This repository is intended to be broader than that and to support other real-world uses as well, including cut flowers and any other plant-related domain that benefits from a shared, machine-readable source of truth.

This project is not intended to replace botanical science, challenge existing authorities, or step on anyone else’s toes. It is a practical data and tooling project that aims to organize plant information in a reusable open format.

## Plant Syntax

This project introduces a new syntax for describing plants that is designed to be more machine friendly. The syntax definition is maintained in [`SYNTAX.md`](SYNTAX.md).

That syntax is intended to support:

- species
- hybrids
- cultivars
- common names
- parent-child relationships between hybrid and cultivar records

For example, a valid plant line might look like this:

```text
Banksia.spinulosa(Birthday Candles){Hairpin Banksia}
```

## Parsers

This project will include parsers for the syntax in both Python and C.

## Repository Layout

Australian plants are stored in `data/`, grouped first by family and then by genus. Each family has its own directory, for example `data/Proteaceae/`, and each genus has its own text file named `{GENUS}.txt` inside the family directory, for example `data/Proteaceae/Banksia.txt` and `data/Proteaceae/Grevillea.txt`.

Generated database artifacts live in `db/`. The `make dbload` target writes `db/plant-family.dbload.txt`, and the `make db` target builds the Berkeley DB file at `db/Australia.db`.

For a weekly deployment refresh on another machine, use `scripts/refresh-australia-db.sh`. It updates a dedicated git clone from `https://github.com/mynativeplant/Australia.git`, builds the load file and Berkeley DB directly, and writes the finished `Australia.db` into the clone's `db/` directory. The target host needs `git`, `python3`, `db_load`, and `install` available.

The helper script `scripts/init-family-layout.py` recreates the family directory tree and can also create missing genus files from `native-plant-catalog.txt` inside the matching family directory. Existing genus files are left untouched.

Each `{GENUS}.txt` file may contain comments. A comment is any record whose first byte is `#`, or any blank record. All other records must contain a parsable plant record.

## Data Model

The plant repository is designed to keep species, hybrids, and cultivars together in one consistent structure. The plant listing endpoint should return details such as:

- common name
- cultivar name
- parent plants for hybrids
- child relationships when the plant is a parent of another hybrid or cultivar

## Web Interface

In addition to the parser, this project is planned to include an Apache module called `mod_mynativeplant`. The module will return JSON lists in response to queries such as `list-families`, `list-genera`, `list-plants`, and `search`.

The module source and build entrypoint live in [`module/`](module/). Use `make module` from the repository root to build it, and `make module-install` to install it via `apxs` when Apache development tooling is available. The module reads the primary Berkeley DB directly, does not rely on a separate secondary index file, and returns pretty-printed JSON.

The `list-families` handler returns a JSON object with `creator` and `run_time` metadata, a `github_path` pointing at [`data/`](data/), plus a `families` array of family name strings built from the primary database.

The `list-genera` handler accepts a `family` query parameter and returns the genera associated with that family as an array of genus name strings. The top-level object carries the family name, a `github_path` pointing at the family directory in [`data/`](data/), plus `creator` and `run_time` metadata.

The `list-plants` handler accepts a required `family` query parameter and an optional `genera` query parameter. When `genera` is present, it returns a top-level `genus` string plus a `plants` array containing parser output objects for the matching records. The top-level object also includes a `github_path` pointing at the genus file in [`data/`](data/). When `genera` is omitted, the handler returns all matching family records across genera, points `github_path` at the family directory, and omits the top-level `genus` field. After building the array, the handler walks it again and adds child links to any matching parent records. In the same second pass, species records gain a `cultivars` array when cultivar forms of the species are present. If any records fail to parse, the handler adds an `errors` array to the top-level response before `github_path`, listing the skipped record keys.

The `search` handler accepts a required `string` query parameter and scans the full database without narrowing to a family or genus first. It returns the top 10 fuzzy matches in score order, with each result including the plant's full syntax name, display name, family, genus, fuzzy match score, and a species-only `wikislug` URL when available.

## Maintenance Model

The intended maintenance model is collaborative. Humans with an interest in a given genus are encouraged to volunteer as the maintainer for that genus file. If no human maintainer is available, the genus will be maintained by an AI bot.

## Status

This repository is being built as a reusable foundation for Australian native plant data.

Current focus areas are:

- defining and documenting the plant syntax
- building the parsers in Python and C
- organizing genus files within family directories
- designing the JSON output for `mod_mynativeplant`

The syntax, parser, directory structure, and web module are the core pieces of the project, but the repository is still under active construction.
