#!/usr/bin/env python3
"""Convert a TTF font into WOFF2 format."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont


def indent_stderr(stderr_text: str) -> str:
    """Summary: Indent stderr text for easier visual grouping.

    Args:
        stderr_text: Raw stderr text.

    Returns:
        str: Stderr text with each non-empty line prefixed by eight spaces.

    Example:
        indent_stderr("line1\nline2\n")
    """

    indented_lines: list[str] = []
    for line in stderr_text.splitlines(keepends=True):
        if line.strip():
            indented_lines.append(f"        {line}")
        else:
            indented_lines.append(line)
    return "".join(indented_lines)


def eprint(*args: object, **kwargs: object) -> None:
    """Summary: Print stderr text with 8-space indentation.

    Args:
        *args: Message parts to print.
        **kwargs: Extra print keyword arguments.

    Returns:
        None

    Example:
        eprint("Something went wrong")
    """

    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    text = sep.join(str(arg) for arg in args) + end
    print(indent_stderr(text), end="", file=sys.stderr, **kwargs)


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Example:
        python ttf_to_woff2.py -input res/Quicksand-VariableFont_wght.ttf -output _output/Quicksand-VariableFont_wght.woff2
    """

    parser = argparse.ArgumentParser(description="Convert a TTF font into WOFF2 format.")
    parser.add_argument("-input", required=True, help="Input TTF path")
    parser.add_argument("-output", required=True, help="Output WOFF2 path")
    return parser.parse_args()


def validate_paths(input_ttf: Path, output_woff2: Path) -> None:
    """Summary: Validate CLI input and output paths.

    Args:
        input_ttf: Source TTF path.
        output_woff2: Destination WOFF2 path.

    Returns:
        None

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If input or output extension is invalid.

    Example:
        validate_paths(Path("res/font.ttf"), Path("_output/font.woff2"))
    """

    if not input_ttf.exists() or not input_ttf.is_file():
        raise FileNotFoundError(f"Input TTF not found: {input_ttf}")
    if input_ttf.suffix.lower() != ".ttf":
        raise ValueError(f"Input must be .ttf: {input_ttf}")
    if output_woff2.suffix.lower() != ".woff2":
        raise ValueError(f"Output must be .woff2: {output_woff2}")


def convert_ttf_to_woff2(input_ttf: Path, output_woff2: Path) -> None:
    """Summary: Convert a TTF font into WOFF2.

    Args:
        input_ttf: Source TTF path.
        output_woff2: Destination WOFF2 path.

    Returns:
        None

    Raises:
        FileNotFoundError: If the input TTF does not exist.
        ValueError: If the file extensions are invalid.
        RuntimeError: If conversion or writing fails.

    Example:
        convert_ttf_to_woff2(Path("res/Quicksand-VariableFont_wght.ttf"), Path("_output/Quicksand-VariableFont_wght.woff2"))
    """

    validate_paths(input_ttf, output_woff2)
    output_woff2.parent.mkdir(parents=True, exist_ok=True)

    try:
        with TTFont(str(input_ttf)) as font:
            font.flavor = "woff2"
            font.save(str(output_woff2))
    except Exception as exc:  # noqa: BLE001
        output_woff2.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to convert TTF to WOFF2: {exc}") from exc

    print(f"Done: {output_woff2}")


def main() -> int:
    """Summary: Run the TTF-to-WOFF2 CLI.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()
    try:
        convert_ttf_to_woff2(Path(args.input).resolve(), Path(args.output).resolve())
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
