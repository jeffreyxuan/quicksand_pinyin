#!/usr/bin/env python3
"""Rename font metadata and rebuild the font with otfcc."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from font_name_utils import (
    apply_rename_rules,
    compute_version,
    normalize_name_records,
    replace_version_placeholders,
)


DEFAULT_OTFCCDUMP = "otfccdump.exe"
DEFAULT_OTFCCBUILD = "otfccbuild.exe"


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
