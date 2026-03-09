#!/usr/bin/env python3
"""Rename font metadata and rebuild the font with otfcc."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OTFCCDUMP = "otfccdump.exe"
DEFAULT_OTFCCBUILD = "otfccbuild.exe"
MAC_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


def parse_args() -> argparse.Namespace:
    """Summary: Parse CLI arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI args.

    Raises:
        SystemExit: Raised when required arguments are missing.

    Example:
        python src/py/ff_rename.py -input _output/in.ttf -output _output/out.ttf -namejson src/json/name_Quicksand-Regular.json
    """
    parser = argparse.ArgumentParser(
        description=(
            "Apply name table from JSON, update version/vendor/head fields, "
            "and rebuild the font."
        )
    )
    parser.add_argument("-input", required=True, help="Input font path")
    parser.add_argument("-output", required=True, help="Output font path")
    parser.add_argument("-namejson", required=True, help="Name table JSON path")
    parser.add_argument("--otfccdump", default=DEFAULT_OTFCCDUMP, help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default=DEFAULT_OTFCCBUILD, help="Path to otfccbuild executable")
    return parser.parse_args()


def run_cmd(cmd: list[str]) -> None:
    """Summary: Run external command and stream output.

    Args:
        cmd: Command list.

    Returns:
        None

    Raises:
        RuntimeError: If command exits with non-zero status.

    Example:
        run_cmd(["otfccdump.exe", "-o", "font.json", "font.ttf"])
    """
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed (exit {completed.returncode}): {joined}")


def load_json(path: Path) -> Any:
    """Summary: Load JSON from file with fallback decoding.

    Args:
        path: JSON file path.

    Returns:
        Any: Parsed JSON object.

    Raises:
        json.JSONDecodeError: If file cannot be parsed as JSON.
        OSError: If file cannot be read.

    Example:
        data = load_json(Path("font.json"))
    """
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "cp950", "gb18030"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))


def save_json(path: Path, data: Any) -> None:
    """Summary: Save JSON data to file.

    Args:
        path: Output JSON path.
        data: JSON object to write.

    Returns:
        None

    Raises:
        OSError: If file cannot be written.

    Example:
        save_json(Path("out.json"), {"ok": True})
    """
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_version(now: datetime | None = None) -> str:
    """Summary: Build version string in 0.YYMMDD format.

    Args:
        now: Datetime to use; defaults to current UTC time.

    Returns:
        str: Version string such as 0.260310.

    Example:
        compute_version()
    """
    current = now or datetime.now().astimezone()
    return f"0.{current.strftime('%y%m%d')}"


def compute_head_created(now: datetime | None = None) -> int:
    """Summary: Compute head.created in Mac epoch seconds.

    Args:
        now: Datetime to use; defaults to current UTC time.

    Returns:
        int: Rounded seconds since 1904-01-01 UTC.

    Example:
        compute_head_created()
    """
    current = now or datetime.now().astimezone()
    return int(round((current - MAC_EPOCH).total_seconds()))


def normalize_name_records(name_json: Any) -> list[dict[str, Any]]:
    """Summary: Extract name records list from name JSON.

    Args:
        name_json: Parsed name JSON object.

    Returns:
        list[dict[str, Any]]: Name records list.

    Raises:
        ValueError: If JSON format is unsupported.

    Example:
        normalize_name_records({"name": []})
    """
    if isinstance(name_json, dict) and isinstance(name_json.get("name"), list):
        return name_json["name"]
    if isinstance(name_json, list):
        return name_json
    raise ValueError("-namejson must be a list or an object containing a 'name' list.")


def replace_version_placeholders(name_records: list[dict[str, Any]], version: str) -> int:
    """Summary: Replace version placeholders and version strings in name records.

    Args:
        name_records: Name records to update in-place.
        version: Computed version string.

    Returns:
        int: Number of modified nameString entries.

    Example:
        replace_version_placeholders(records, "0.260310")
    """
    changed = 0
    for record in name_records:
        if not isinstance(record, dict):
            continue
        value = record.get("nameString")
        if not isinstance(value, str):
            continue

        new_value = value.replace("{}", version)
        if value.startswith("Version "):
            new_value = f"Version {version}"

        if new_value != value:
            record["nameString"] = new_value
            changed += 1
    return changed


def apply_rename_rules(font_json: dict[str, Any], name_records: list[dict[str, Any]], version: str) -> None:
    """Summary: Apply all required rename and metadata update rules.

    Args:
        font_json: Font JSON object from otfccdump.
        name_records: Name records to write into font_json.
        version: Version string in 0.YYMMDD format.

    Returns:
        None

    Example:
        apply_rename_rules(font_json, name_records, "0.260310")
    """
    font_json["name"] = name_records

    os2 = font_json.setdefault("OS_2", {})
    if isinstance(os2, dict):
        os2["achVendID"] = "TNOZ"

    head = font_json.setdefault("head", {})
    if isinstance(head, dict):
        head["created"] = compute_head_created()
        head["fontRevision"] = float(version)


def main() -> int:
    """Summary: CLI entry point.

    Args:
        None

    Returns:
        int: Process exit code.

    Raises:
        Exception: Any unexpected runtime error.

    Example:
        python src/py/ff_rename.py -input _output/in.ttf -output _output/out.ttf -namejson src/json/name_Quicksand-Regular.json
    """
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    namejson_path = Path(args.namejson).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2
    if not namejson_path.exists():
        print(f"Name JSON file not found: {namejson_path}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    version = compute_version()
    print(f"Computed version: {version}")

    try:
        with tempfile.TemporaryDirectory(prefix="rename_", dir=Path("_tmp").resolve()) as tmp_dir:
            tmp = Path(tmp_dir)
            dumped_json = tmp / "input.json"
            patched_json = tmp / "patched.json"

            run_cmd([args.otfccdump, "-o", str(dumped_json), str(input_path)])

            font_json = load_json(dumped_json)
            if not isinstance(font_json, dict):
                print("Input font JSON root is not an object.", file=sys.stderr)
                return 3

            name_json = load_json(namejson_path)
            name_records = normalize_name_records(name_json)
            changed_count = replace_version_placeholders(name_records, version)
            print(f"Name entries updated by version rule: {changed_count}")

            apply_rename_rules(font_json, name_records, version)
            save_json(patched_json, font_json)

            run_cmd([args.otfccbuild, "-o", str(output_path), str(patched_json)])
            print(f"Done: {output_path}")
            return 0

    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        return 5
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 6
    except FileNotFoundError as exc:
        print(f"Executable not found: {exc}", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())

