#!/usr/bin/env python3
"""Rebuild missing glyph instructions by combining otfccdump and ttfautohint."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_TTFAUTOHINT = r"C:\tool\ttfautohint\ttfautohint.exe"
DEFAULT_OTFCCDUMP = "otfccdump.exe"
DEFAULT_OTFCCBUILD = "otfccbuild.exe"


def parse_args() -> argparse.Namespace:
    """Summary: Parse CLI arguments for rehint workflow.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed arguments.

    Raises:
        SystemExit: Raised by argparse when required args are missing.

    Example:
        python src/py/ff_rehint.py -original res/Quicksand-Regular.ttf -input _output/Quicksand-Regular_pinyin.ttf -output _output/Quicksand-Regular_pinyin_rehint.ttf
    """
    parser = argparse.ArgumentParser(
        description=(
            "Detect glyphs that lost instructions after FontForge edits, "
            "rehint only those glyphs with ttfautohint data, and build output font."
        )
    )
    parser.add_argument("-original", required=True, help="Original TTF path")
    parser.add_argument("-input", required=True, help="Edited TTF path that may have lost instructions")
    parser.add_argument("-output", required=True, help="Output TTF path")
    parser.add_argument("--ttfautohint", default=DEFAULT_TTFAUTOHINT, help="Path to ttfautohint executable")
    parser.add_argument("--otfccdump", default=DEFAULT_OTFCCDUMP, help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default=DEFAULT_OTFCCBUILD, help="Path to otfccbuild executable")
    return parser.parse_args()


def format_cmd(cmd: list[str]) -> str:
    """Summary: Build a debug-friendly command string.

    Args:
        cmd: Command list for subprocess.

    Returns:
        str: Joined command line string.

    Example:
        format_cmd(["tool.exe", "a", "b"])
    """
    return " ".join(f'"{part}"' if " " in part else part for part in cmd)


def run_cmd(cmd: list[str], *, print_command: bool = False) -> None:
    """Summary: Execute a subprocess and relay output.

    Args:
        cmd: Command list.
        print_command: Whether to print full command line before execution.

    Returns:
        None

    Raises:
        RuntimeError: If command exits with non-zero status.

    Example:
        run_cmd(["otfccdump.exe", "-o", "a.json", "a.ttf"])
    """
    if print_command:
        print(f"$ {format_cmd(cmd)}")

    completed = subprocess.run(cmd, capture_output=True, text=True)

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit {completed.returncode}: {format_cmd(cmd)}")


def load_json(path: Path) -> dict[str, Any]:
    """Summary: Read JSON file into dictionary.

    Args:
        path: JSON file path.

    Returns:
        dict[str, Any]: Parsed JSON object.

    Raises:
        json.JSONDecodeError: If file content is invalid JSON.
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

    # Fallback for fonts carrying non-UTF8 bytes in name records.
    return json.loads(raw.decode("utf-8", errors="replace"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Summary: Write dictionary to JSON file.

    Args:
        path: JSON file path.
        data: JSON object.

    Returns:
        None

    Raises:
        OSError: If file cannot be written.

    Example:
        save_json(Path("out.json"), {"name": "demo"})
    """
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def has_instructions(glyph_entry: Any) -> bool:
    """Summary: Check whether a glyph entry has usable instructions.

    Args:
        glyph_entry: Glyph object from otfccdump JSON.

    Returns:
        bool: True when instruction list exists and is non-empty.

    Example:
        has_instructions({"instructions": ["SVTCA[y-axis]"]})
    """
    if not isinstance(glyph_entry, dict):
        return False
    instructions = glyph_entry.get("instructions")
    return isinstance(instructions, list) and len(instructions) > 0


def find_glyphs_missing_instructions(original: dict[str, Any], edited: dict[str, Any]) -> list[str]:
    """Summary: Find glyphs where instructions exist in original but are missing in edited font.

    Args:
        original: Original font JSON.
        edited: Edited font JSON.

    Returns:
        list[str]: Glyph names needing instruction rebuild.

    Example:
        names = find_glyphs_missing_instructions(orig_json, input_json)
    """
    original_glyf = original.get("glyf")
    edited_glyf = edited.get("glyf")
    if not isinstance(original_glyf, dict) or not isinstance(edited_glyf, dict):
        return []

    targets: list[str] = []
    for glyph_name, original_entry in original_glyf.items():
        if not has_instructions(original_entry):
            continue
        edited_entry = edited_glyf.get(glyph_name)
        if not has_instructions(edited_entry):
            targets.append(glyph_name)
    return targets


def apply_rehinted_instructions(
    edited: dict[str, Any],
    rehinted: dict[str, Any],
    glyph_names: list[str],
) -> tuple[int, list[str]]:
    """Summary: Copy rehinted instructions into edited JSON for target glyphs.

    Args:
        edited: Edited font JSON to mutate.
        rehinted: ttfautohint-generated font JSON.
        glyph_names: Glyph names that require rebuild.

    Returns:
        tuple[int, list[str]]: Applied count and glyphs still missing after rehint.

    Example:
        applied, missing = apply_rehinted_instructions(input_json, hinted_json, targets)
    """
    edited_glyf = edited.get("glyf")
    rehinted_glyf = rehinted.get("glyf")
    if not isinstance(edited_glyf, dict) or not isinstance(rehinted_glyf, dict):
        return 0, glyph_names

    applied = 0
    still_missing: list[str] = []

    for glyph_name in glyph_names:
        rehinted_entry = rehinted_glyf.get(glyph_name)
        edited_entry = edited_glyf.get(glyph_name)
        if not isinstance(edited_entry, dict) or not has_instructions(rehinted_entry):
            still_missing.append(glyph_name)
            continue

        edited_entry["instructions"] = list(rehinted_entry["instructions"])
        applied += 1

    return applied, still_missing


def ensure_exists(path: Path, label: str) -> None:
    """Summary: Ensure a required file exists.

    Args:
        path: File path to check.
        label: Human-readable file role for error message.

    Returns:
        None

    Raises:
        FileNotFoundError: If file does not exist.

    Example:
        ensure_exists(Path("font.ttf"), "input")
    """
    if not path.exists():
        raise FileNotFoundError(f"{label} file not found: {path}")


def main() -> int:
    """Summary: CLI entry point for selective instruction rebuild.

    Args:
        None

    Returns:
        int: Process exit code.

    Raises:
        Exception: Any unexpected runtime error.

    Example:
        python src/py/ff_rehint.py -original res/Quicksand-Regular.ttf -input _output/Quicksand-Regular_pinyin.ttf -output _output/Quicksand-Regular_pinyin_rehint.ttf
    """
    args = parse_args()

    original_path = Path(args.original).resolve()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    try:
        ensure_exists(original_path, "original")
        ensure_exists(input_path, "input")
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_root = Path("_tmp").resolve()
    tmp_root.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(prefix="rehint_", dir=tmp_root) as tmp_dir:
            tmp_path = Path(tmp_dir)

            original_json_path = tmp_path / "original.json"
            input_json_path = tmp_path / "input.json"
            hinted_font_path = tmp_path / "input_ttfautohint.ttf"
            hinted_json_path = tmp_path / "hinted.json"
            merged_json_path = tmp_path / "merged.json"

            run_cmd([args.otfccdump, "-o", str(original_json_path), str(original_path)])
            run_cmd([args.otfccdump, "-o", str(input_json_path), str(input_path)])

            original_json = load_json(original_json_path)
            input_json = load_json(input_json_path)

            targets = find_glyphs_missing_instructions(original_json, input_json)
            print(f"Glyphs needing rehint: {len(targets)}")

            if not targets:
                shutil.copy2(input_path, output_path)
                print(f"No missing instructions found. Copied input to output: {output_path}")
                return 0

            ttfautohint_cmd = [args.ttfautohint, str(input_path), str(hinted_font_path)]
            run_cmd(ttfautohint_cmd, print_command=True)

            run_cmd([args.otfccdump, "-o", str(hinted_json_path), str(hinted_font_path)])
            hinted_json = load_json(hinted_json_path)

            applied_count, still_missing = apply_rehinted_instructions(input_json, hinted_json, targets)
            print(f"Glyph instructions rebuilt: {applied_count}")

            if still_missing:
                preview = ", ".join(still_missing[:20])
                suffix = " ..." if len(still_missing) > 20 else ""
                print(
                    f"Warning: {len(still_missing)} glyphs still missing instructions after ttfautohint: {preview}{suffix}",
                    file=sys.stderr,
                )

            save_json(merged_json_path, input_json)
            run_cmd([args.otfccbuild, "-o", str(output_path), str(merged_json_path)])

            print(f"Done: {output_path}")
            return 0

    except FileNotFoundError as exc:
        print(f"Executable not found: {exc}", file=sys.stderr)
        return 3
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        return 4
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())


