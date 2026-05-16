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

The helper script `scripts/init-family-layout.py` recreates the family directory tree and can also create a genus file inside a family directory.

Each `{GENUS}.txt` file may contain comments. A comment is any record whose first byte is `#`, or any blank record. All other records must contain a parsable plant record.

## Data Model

The plant repository is designed to keep species, hybrids, and cultivars together in one consistent structure. For a plant record, `list-plant` should return details such as:

- common name
- cultivar name
- parent plants for hybrids
- child relationships when the plant is a parent of another hybrid or cultivar

## Web Interface

In addition to the parser, this project is planned to include an Apache module called `mod_mynativeplant`. The module will return JSON lists in response to queries such as `list-genus` and `list-plant`.

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
