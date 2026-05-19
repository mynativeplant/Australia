#!/usr/bin/env python3
"""Build a db_load-compatible flat text file from the family tree."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def escape_db_load_text(value: str) -> str:
    """Escape text for Berkeley DB -T input."""
    return value.replace("\\", "\\\\").replace("\r", r"\0d").replace("\n", r"\0a")


def iter_family_files(data_root: Path) -> Iterable[tuple[str, Path]]:
    for family_dir in sorted(
        (path for path in data_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        for text_path in sorted(family_dir.rglob("*.txt"), key=lambda path: path.as_posix()):
            yield family_dir.name, text_path


def build_db_load_file(data_root: Path, output_path: Path) -> int:
    if not data_root.exists():
        raise FileNotFoundError(f"data root does not exist: {data_root}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen: dict[str, tuple[str, Path, int]] = {}
    record_count = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for family, text_path in iter_family_files(data_root):
            with text_path.open("r", encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    key = raw_line.rstrip("\r\n")
                    if not key:
                        continue

                    previous = seen.get(key)
                    if previous is not None:
                        previous_family, previous_path, previous_line = previous
                        raise ValueError(
                            "duplicate plant syntax key: "
                            f"{key!r} in {text_path}:{line_number} "
                            f"(already seen in {previous_path}:{previous_line}, family {previous_family})"
                        )

                    seen[key] = (family, text_path, line_number)
                    out.write(f"{escape_db_load_text(key)}\n")
                    out.write(f"{escape_db_load_text(family)}\n")
                    record_count += 1

    return record_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a flat text file that db_load can ingest into a btree."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root that contains the data/ directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output text file. Defaults to db/plant-family.dbload.txt under --root.",
    )
    args = parser.parse_args()

    data_root = args.root / "data"
    output_path = args.output or (args.root / "db" / "plant-family.dbload.txt")
    if not output_path.is_absolute():
        output_path = args.root / output_path

    record_count = build_db_load_file(data_root, output_path)
    print(f"Wrote {record_count} records to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
