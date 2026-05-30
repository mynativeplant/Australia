#!/usr/bin/env python3
"""Batch load plant syntax records into the family tree.

All syntax parsing should go through the shared C API or `bin/mnpparse`.
Do not add a separate parser here.

For each input record, the loader:

1. Parses the record using the repository plant syntax.
2. Resolves the genus against the existing `data/` directory tree.
3. Checks whether the exact plant syntax already exists anywhere in `data/`.
4. Appends the canonical record to `data/<family>/<genus>.txt` when it is new or
   richer than the matching taxon already present in `data/`.

The script writes a detailed report describing every decision it makes.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import TextIO


MNPARSE_BIN = Path(__file__).resolve().parents[1] / "bin" / "mnpparse"


def is_identifier_start(ch: str) -> bool:
    return ch.isalpha()


def is_genus_char(ch: str) -> bool:
    return ch.isalnum() or ch == "-"


def is_epithet_char(ch: str) -> bool:
    return ch.islower() or ch.isdigit() or ch == "-"


def skip_spaces(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def parse_rank(text: str) -> str | None:
    if text == "subsp":
        return "subsp"
    if text == "var":
        return "var"
    if text == "form":
        return "form"
    return None


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRecord:
    raw_input: str
    canonical: str
    taxon_key: str
    genus: str
    family: str
    target_path: Path
    kind: str
    cultivar_name: str | None = None
    common_name: str | None = None
    normalized: bool = False


@dataclass
class ExistingRecordIndex:
    exact_locations: dict[str, list[tuple[Path, int]]]
    taxon_locations: dict[str, list[tuple[Path, int]]]
    taxon_has_named: dict[str, bool]
    parse_errors: list[tuple[Path, int, str]]


@dataclass
class BatchStats:
    total_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    parsed_lines: int = 0
    parse_failures: int = 0
    unknown_genera: int = 0
    exact_duplicates: int = 0
    taxon_hits: int = 0
    richer_records_kept: int = 0
    less_detailed_skips: int = 0
    appended: int = 0
    created_files: int = 0


class SyntaxParser:
    def __init__(self, text: str):
        self.text = text.rstrip("\r\n")

    def parse(self) -> ParsedRecord:
        raw = self.text.strip()
        if not raw:
            raise ParseError("blank record")
        if raw.startswith("#"):
            raise ParseError("comment record")

        index = skip_spaces(self.text, 0)
        genus_start = index
        if index >= len(self.text) or not is_identifier_start(self.text[index]):
            raise ParseError("expected genus name")

        index += 1
        while index < len(self.text) and is_genus_char(self.text[index]):
            index += 1

        genus = self.text[genus_start:index]
        index = skip_spaces(self.text, index)
        if index >= len(self.text):
            raise ParseError("missing taxon expression")

        empty_hybrid = False
        sole_cultivar_parent = False
        if self.text[index] == ".":
            index += 1
            index = skip_spaces(self.text, index)
            base, index, kind = self._parse_species_or_infraspecific(genus, index)
        elif self.text[index] == "[":
            base, index, kind, empty_hybrid, sole_cultivar_parent = self._parse_hybrid(genus, index)
        else:
            raise ParseError("expected '.' for species or '[' for hybrid")

        cultivar_name = None
        common_name = None
        index = skip_spaces(self.text, index)
        if index < len(self.text) and self.text[index] == "(":
            cultivar_name, index = self._parse_parenthesized(index, "(", ")")
            index = skip_spaces(self.text, index)

        if index < len(self.text) and self.text[index] == "{":
            common_name, index = self._parse_parenthesized(index, "{", "}")
            index = skip_spaces(self.text, index)

        if index != len(self.text):
            raise ParseError("unexpected trailing text")

        if empty_hybrid and cultivar_name is None and common_name is None:
            raise ParseError("empty hybrid requires cultivar or common-name suffix")
        if sole_cultivar_parent and cultivar_name is None:
            raise ParseError("single cultivar parent requires a cultivar name")

        canonical = base
        if cultivar_name is not None:
            canonical += f"({cultivar_name})"
        if common_name is not None:
            canonical += f"{{{common_name}}}"

        return ParsedRecord(
            raw_input=self.text,
            canonical=canonical,
            taxon_key=base,
            genus=genus,
            family="",
            target_path=Path(),
            kind=kind,
            cultivar_name=cultivar_name,
            common_name=common_name,
            normalized=canonical != self.text.strip(),
        )

    def _parse_parenthesized(self, index: int, open_char: str, close_char: str) -> tuple[str, int]:
        if self.text[index] != open_char:
            raise ParseError(f"expected {open_char!r}")

        index += 1
        start = index
        while index < len(self.text) and self.text[index] != close_char:
            index += 1
        if index >= len(self.text):
            raise ParseError(f"missing closing {close_char!r}")

        value = self.text[start:index].strip()
        if not value:
            raise ParseError("empty suffix")

        return value, index + 1

    def _parse_species_or_infraspecific(self, genus: str, index: int) -> tuple[str, int, str]:
        species_start = index
        while index < len(self.text) and is_epithet_char(self.text[index]):
            index += 1
        if index == species_start:
            raise ParseError("missing species epithet")

        species = self.text[species_start:index]
        base = f"{genus}.{species}"
        kind = "species"

        index = skip_spaces(self.text, index)
        if index < len(self.text) and self.text[index] == ":":
            index += 1
            index = skip_spaces(self.text, index)
            rank_start = index
            while index < len(self.text) and self.text[index].isalpha():
                index += 1
            rank = parse_rank(self.text[rank_start:index])
            if rank is None or index >= len(self.text) or self.text[index] != ".":
                raise ParseError("invalid infraspecific rank")

            index += 1
            index = skip_spaces(self.text, index)
            epithet_start = index
            if index < len(self.text) and self.text[index] == "*":
                index += 1
            else:
                while index < len(self.text) and is_epithet_char(self.text[index]):
                    index += 1

            epithet = self.text[epithet_start:index]
            if not epithet:
                raise ParseError("missing infraspecific epithet")

            if rank == "subsp" and epithet == "*":
                epithet = species

            base = f"{genus}.{species}:{rank}.{epithet}"
            kind = "infraspecific"

        return base, index, kind

    def _parse_bare_parent_species(self, genus: str, index: int) -> tuple[str, int]:
        species_start = index
        while index < len(self.text) and is_epithet_char(self.text[index]):
            index += 1
        if index == species_start:
            raise ParseError("missing hybrid parent epithet")

        species = self.text[species_start:index]
        base = species

        index = skip_spaces(self.text, index)
        if index < len(self.text) and self.text[index] == ":":
            index += 1
            index = skip_spaces(self.text, index)
            rank_start = index
            while index < len(self.text) and self.text[index].isalpha():
                index += 1
            rank = parse_rank(self.text[rank_start:index])
            if rank is None or index >= len(self.text) or self.text[index] != ".":
                raise ParseError("invalid infraspecific rank in hybrid parent")

            index += 1
            index = skip_spaces(self.text, index)
            epithet_start = index
            if index < len(self.text) and self.text[index] == "*":
                index += 1
            else:
                while index < len(self.text) and is_epithet_char(self.text[index]):
                    index += 1

            epithet = self.text[epithet_start:index]
            if not epithet:
                raise ParseError("missing infraspecific epithet in hybrid parent")
            if rank == "subsp" and epithet == "*":
                epithet = species
            base = f"{species}:{rank}.{epithet}"

        return base, index

    def _parse_parent_expression(self, genus: str, index: int) -> tuple[str, int]:
        index = skip_spaces(self.text, index)
        if index >= len(self.text):
            raise ParseError("unexpected end of input in hybrid parent")

        if self.text[index] == "(":
            name, index = self._parse_parenthesized(index, "(", ")")
            return f"({name})", index

        if self.text[index] == "[":
            base, index, _, _ = self._parse_hybrid(genus, index)
            return base, index

        if self.text[index] == "?":
            return "?", index + 1

        parent, index = self._parse_bare_parent_species(genus, index)
        return parent, index

    def _parse_hybrid(self, genus: str, index: int) -> tuple[str, int, str, bool, bool]:
        if self.text[index] != "[":
            raise ParseError("expected '['")

        index += 1
        index = skip_spaces(self.text, index)

        if index < len(self.text) and self.text[index] == "]":
            return f"{genus}[]", index + 1, "hybrid", True, False

        if index < len(self.text) and self.text[index] == "?":
            probe = skip_spaces(self.text, index + 1)
            if probe < len(self.text) and self.text[probe] == "]":
                return f"{genus}[]", probe + 1, "hybrid", True, False

        parents: list[str] = []
        parent, index = self._parse_parent_expression(genus, index)
        parents.append(parent)

        index = skip_spaces(self.text, index)
        if index < len(self.text) and self.text[index] == "]":
            if not parent.startswith("("):
                raise ParseError("single cultivar parent requires a cultivar name")
            return f"{genus}[{parents[0]}]", index + 1, "hybrid", False, True

        if index >= len(self.text) or self.text[index] != "|":
            raise ParseError("hybrid expression must contain exactly two parents")
        index += 1
        index = skip_spaces(self.text, index)

        parent, index = self._parse_parent_expression(genus, index)
        parents.append(parent)

        if index >= len(self.text) or self.text[index] != "]":
            raise ParseError("missing closing ']' in hybrid expression")

        return f"{genus}[{parents[0]}|{parents[1]}]", index + 1, "hybrid", False, False


def parse_record(text: str) -> ParsedRecord:
    try:
        completed = subprocess.run(
            [str(MNPARSE_BIN), text],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise ParseError(f"mnpparse not found at {MNPARSE_BIN}") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip() or "mnpparse failed"
        raise ParseError(message) from error

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ParseError(f"mnpparse returned invalid JSON: {error.msg}") from error

    if payload.get("error") != "OK":
        raise ParseError(payload.get("error", "mnpparse failed"))

    parsed = SyntaxParser(payload["raw"]).parse()

    return ParsedRecord(
        raw_input=parsed.raw_input,
        canonical=parsed.canonical,
        taxon_key=parsed.taxon_key,
        genus=parsed.genus,
        family="",
        target_path=Path(),
        kind=parsed.kind,
        cultivar_name=parsed.cultivar_name,
        common_name=parsed.common_name,
        normalized=parsed.normalized,
    )


def load_genus_family_map(data_root: Path) -> dict[str, str]:
    genus_family: dict[str, str] = {}
    for family_dir in sorted((path for path in data_root.iterdir() if path.is_dir()), key=lambda path: path.name):
        for text_path in sorted(family_dir.glob("*.txt"), key=lambda path: path.name):
            genus = text_path.stem
            if genus == "Genus":
                continue
            previous = genus_family.get(genus)
            if previous is not None and previous != family_dir.name:
                raise ValueError(
                    f"conflicting family mapping for {genus!r}: {previous!r} vs {family_dir.name!r}"
                )
            genus_family[genus] = family_dir.name
    return genus_family


def load_existing_index(data_root: Path) -> ExistingRecordIndex:
    exact_locations: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    taxon_locations: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    taxon_has_named: dict[str, bool] = defaultdict(bool)
    parse_errors: list[tuple[Path, int, str]] = []

    for family_dir in sorted((path for path in data_root.iterdir() if path.is_dir()), key=lambda path: path.name):
        for text_path in sorted(family_dir.glob("*.txt"), key=lambda path: path.name):
            with text_path.open("r", encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    record = raw_line.rstrip("\r\n")
                    if not record or record.startswith("#"):
                        continue
                    try:
                        parsed = parse_record(record)
                    except ParseError as error:
                        parse_errors.append((text_path, line_number, str(error)))
                        exact_locations[record].append((text_path, line_number))
                        continue

                    exact_locations[parsed.canonical].append((text_path, line_number))
                    taxon_locations[parsed.taxon_key].append((text_path, line_number))
                    if parsed.cultivar_name is not None or parsed.common_name is not None:
                        taxon_has_named[parsed.taxon_key] = True

    return ExistingRecordIndex(
        exact_locations=dict(exact_locations),
        taxon_locations=dict(taxon_locations),
        taxon_has_named=dict(taxon_has_named),
        parse_errors=parse_errors,
    )


def format_locations(locations: list[tuple[Path, int]], root: Path) -> str:
    parts = [f"{path.relative_to(root)}:{line}" for path, line in locations]
    return ", ".join(parts)


def ensure_trailing_newline(path: Path, handle: TextIO) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb") as probe:
        probe.seek(-1, 2)
        last_byte = probe.read(1)
    if last_byte != b"\n":
        handle.write("\n")


def append_records(
    root: Path,
    staged_writes: dict[Path, list[str]],
    dry_run: bool,
    report: TextIO,
) -> tuple[int, int]:
    created_files = 0
    appended_records = 0

    for target_path in sorted(staged_writes, key=lambda path: path.as_posix()):
        records = staged_writes[target_path]
        if not records:
            continue

        if target_path.exists() and target_path.stat().st_size > 0:
            already_exists = True
        else:
            already_exists = False
            if not dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.touch(exist_ok=True)
                created_files += 1

        report.write(f"TARGET FILE: {target_path.relative_to(root)}\n")
        report.write(f"MODE: {'dry-run' if dry_run else 'append'}\n")
        report.write(f"RECORDS: {len(records)}\n")

        if dry_run:
            for record in records:
                report.write(f"  WOULD APPEND: {record}\n")
            appended_records += len(records)
            continue

        with target_path.open("a", encoding="utf-8", newline="\n") as handle:
            if already_exists:
                ensure_trailing_newline(target_path, handle)
            for record in records:
                handle.write(f"{record}\n")
                appended_records += 1
                report.write(f"  APPENDED: {record}\n")

    return created_files, appended_records


def load_batch(
    input_path: Path,
    root: Path,
    report_path: Path,
    dry_run: bool,
) -> int:
    data_root = root / "data"
    genus_family = load_genus_family_map(data_root)
    existing_index = load_existing_index(data_root)

    stats = BatchStats()
    staged_writes: dict[Path, list[str]] = defaultdict(list)
    staged_exact: set[str] = set()
    staged_taxon: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    staged_taxon_has_named: dict[str, bool] = defaultdict(bool)

    with input_path.open("r", encoding="utf-8") as input_handle, report_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as report:
        report.write(f"INPUT: {input_path}\n")
        report.write(f"ROOT: {root}\n")
        report.write(f"DRY RUN: {dry_run}\n")
        report.write(f"EXISTING FILES INDEXED: {len(existing_index.exact_locations)} exact keys\n")
        if existing_index.parse_errors:
            report.write(f"EXISTING PARSE WARNINGS: {len(existing_index.parse_errors)}\n")
            for path, line_number, message in existing_index.parse_errors[:20]:
                report.write(f"  {path.relative_to(root)}:{line_number}: {message}\n")
        report.write("\n")

        for line_number, raw_line in enumerate(input_handle, start=1):
            stats.total_lines += 1
            line = raw_line.rstrip("\r\n")
            stripped = line.strip()

            report.write(f"LINE {line_number}: {line}\n")
            if not stripped:
                stats.blank_lines += 1
                report.write("  RESULT: skipped blank line\n\n")
                continue
            if stripped.startswith("#"):
                stats.comment_lines += 1
                report.write("  RESULT: skipped comment line\n\n")
                continue

            try:
                parsed = parse_record(line)
            except ParseError as error:
                stats.parse_failures += 1
                report.write(f"  PARSE: failed\n")
                report.write(f"  REASON: {error}\n")
                report.write("  ACTION: skipped\n\n")
                continue

            stats.parsed_lines += 1
            report.write("  PARSE: ok\n")
            report.write(f"  CANONICAL: {parsed.canonical}\n")
            if parsed.normalized:
                report.write("  NORMALIZED: yes\n")
            else:
                report.write("  NORMALIZED: no\n")
            report.write(f"  TAXON: {parsed.taxon_key}\n")
            report.write(f"  GENUS: {parsed.genus}\n")
            if parsed.cultivar_name is not None:
                report.write(f"  CULTIVAR: {parsed.cultivar_name}\n")
            if parsed.common_name is not None:
                report.write(f"  COMMON: {parsed.common_name}\n")

            family = genus_family.get(parsed.genus)
            if family is None:
                stats.unknown_genera += 1
                report.write("  RESOLUTION: genus not present under data/\n")
                report.write("  ACTION: skipped\n\n")
                continue

            target_path = data_root / family / f"{parsed.genus}.txt"
            report.write(f"  FAMILY: {family}\n")
            report.write(f"  TARGET: {target_path.relative_to(root)}\n")

            exact_locations = existing_index.exact_locations.get(parsed.canonical, [])
            taxon_locations = existing_index.taxon_locations.get(parsed.taxon_key, [])
            staged_taxon_locations = staged_taxon.get(parsed.taxon_key, [])
            incoming_is_named = parsed.cultivar_name is not None or parsed.common_name is not None
            existing_has_named = existing_index.taxon_has_named.get(parsed.taxon_key, False)
            staged_has_named = staged_taxon_has_named.get(parsed.taxon_key, False)
            taxon_match = bool(taxon_locations or staged_taxon_locations)

            if exact_locations or parsed.canonical in staged_exact:
                stats.exact_duplicates += 1
                report.write("  DUPLICATE CHECK: exact record already exists\n")
                if exact_locations:
                    report.write(f"  EXISTING LOCATIONS: {format_locations(exact_locations, root)}\n")
                if parsed.canonical in staged_exact:
                    report.write("  EXISTING LOCATIONS: staged in this batch already\n")
                report.write("  ACTION: skipped\n\n")
                continue

            if taxon_match:
                stats.taxon_hits += 1
                report.write("  TAXON CHECK: same plant already exists in data/\n")
                if taxon_locations:
                    report.write(f"  TAXON LOCATIONS: {format_locations(taxon_locations, root)}\n")
                if staged_taxon_locations:
                    staged_desc = ", ".join(
                        f"{path.relative_to(root)} ({record})" for path, record in staged_taxon_locations
                    )
                    report.write(f"  TAXON LOCATIONS: staged in this batch: {staged_desc}\n")
                if not incoming_is_named and (existing_has_named or staged_has_named):
                    stats.less_detailed_skips += 1
                    report.write("  DECISION: skip because a more detailed record already exists\n")
                    report.write("  ACTION: skipped\n\n")
                    continue
                if incoming_is_named and taxon_match:
                    stats.richer_records_kept += 1
                    report.write("  DECISION: keep because incoming record is a named variant\n")
                else:
                    report.write("  DECISION: keep because this record is distinct at the same detail level\n")
                report.write("  DUPLICATE CHECK: no exact record found anywhere in data/\n")
                report.write("  TAXON CHECK: existing taxon match accepted because the new record is richer or distinct\n")
            else:
                report.write("  DUPLICATE CHECK: no exact record found anywhere in data/\n")
                report.write("  TAXON CHECK: no matching plant found in data/\n")

            staged_writes[target_path].append(parsed.canonical)
            staged_exact.add(parsed.canonical)
            staged_taxon[parsed.taxon_key].append((target_path, parsed.canonical))
            if incoming_is_named:
                staged_taxon_has_named[parsed.taxon_key] = True
            report.write("  ACTION: staged for append\n\n")

        created_files, appended_records = append_records(root, staged_writes, dry_run, report)
        stats.created_files = created_files
        stats.appended = appended_records

        report.write("\nSUMMARY\n")
        report.write(f"  total_lines: {stats.total_lines}\n")
        report.write(f"  blank_lines: {stats.blank_lines}\n")
        report.write(f"  comment_lines: {stats.comment_lines}\n")
        report.write(f"  parsed_lines: {stats.parsed_lines}\n")
        report.write(f"  parse_failures: {stats.parse_failures}\n")
        report.write(f"  unknown_genera: {stats.unknown_genera}\n")
        report.write(f"  exact_duplicates: {stats.exact_duplicates}\n")
        report.write(f"  taxon_hits: {stats.taxon_hits}\n")
        report.write(f"  richer_records_kept: {stats.richer_records_kept}\n")
        report.write(f"  less_detailed_skips: {stats.less_detailed_skips}\n")
        report.write(f"  appended_records: {stats.appended}\n")
        report.write(f"  created_files: {stats.created_files}\n")
        report.write(f"  dry_run: {dry_run}\n")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch-load parsed plant records into the matching data/<family>/<genus>.txt files."
    )
    parser.add_argument("input_file", type=Path, help="Input file containing one plant record per line.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root that contains the data/ directory.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write the detailed report here. Defaults to <input_file>.batch-report.txt next to the input.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not modify any data files; only produce the report.",
    )
    args = parser.parse_args()

    root = args.root
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()

    input_path = args.input_file
    if not input_path.is_absolute():
        input_path = (root / input_path).resolve()
    else:
        input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")

    report_path = args.report
    if report_path is None:
        report_path = input_path.with_name(f"{input_path.name}.batch-report.txt")
    if not report_path.is_absolute():
        report_path = (root / report_path).resolve()
    else:
        report_path = report_path.resolve()

    return load_batch(input_path, root, report_path, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
