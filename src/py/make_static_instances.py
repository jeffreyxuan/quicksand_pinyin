#!/usr/bin/env python3
"""Build default static-weight TTF instances from a variable font."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.varLib.instancer import instantiateVariableFont

DEFAULT_WEIGHTS = (300, 400, 500, 600, 700)


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
        python make_static_instances.py -input _output/ToneOZ-Quicksnow.ttf -output-dir _tmp/static
    """

    parser = argparse.ArgumentParser(
        description="Build default static instances (300/400/500/600/700) from a variable TTF."
    )
    parser.add_argument("-input", required=True, help="Input variable TTF path")
    parser.add_argument("-output-dir", required=True, help="Output directory for static TTFs")
    return parser.parse_args()


def sanitize_postscript_name(name: str) -> str:
    """Summary: Convert a display name into a PostScript-safe name.

    Args:
        name: Source display name.

    Returns:
        str: Name containing only ASCII letters, digits, hyphen, and underscore.

    Example:
        sanitize_postscript_name("ToneOZ-Quicksnow-W300")
    """

    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    sanitized = "".join(ch for ch in name if ch in allowed)
    return sanitized or "StaticFont"


def remove_name_ids(name_table: object, name_ids: set[int]) -> None:
    """Summary: Remove all existing name records for the specified name IDs.

    Args:
        name_table: Font `name` table object.
        name_ids: Name IDs to remove.

    Returns:
        None

    Example:
        remove_name_ids(font["name"], {1, 2, 4, 6})
    """

    name_table.names = [record for record in name_table.names if record.nameID not in name_ids]


def add_name_record(
    name_table: object,
    name_id: int,
    value: str,
    platform_id: int,
    encoding_id: int,
    language_id: int,
) -> None:
    """Summary: Append a new name record to the font.

    Args:
        name_table: Font `name` table object.
        name_id: OpenType name ID.
        value: String value to encode.
        platform_id: Name record platform ID.
        encoding_id: Name record encoding ID.
        language_id: Name record language ID.

    Returns:
        None

    Example:
        add_name_record(font["name"], 1, "ToneOZ-Quicksnow-W300", 3, 1, 0x0409)
    """

    record = NameRecord()
    record.nameID = name_id
    record.platformID = platform_id
    record.platEncID = encoding_id
    record.langID = language_id
    record.string = value.encode("utf-16-be") if platform_id == 3 else value.encode("mac_roman", errors="replace")
    name_table.names.append(record)


def apply_static_metadata(font: TTFont, family_name: str, weight: int) -> None:
    """Summary: Update a static instance to use standalone family naming.

    Args:
        font: Static TTFont instance to patch.
        family_name: Standalone family name for this static font.
        weight: Target usWeightClass value.

    Returns:
        None

    Example:
        apply_static_metadata(font, "ToneOZ-Quicksnow-W300", 300)
    """

    postscript_name = sanitize_postscript_name(family_name)
    version_string = ""
    if "name" in font:
        version_string = next(
            (str(record.toUnicode()) for record in font["name"].names if record.nameID == 5),
            "",
        )
    unique_id = f"{family_name};{version_string};{postscript_name}" if version_string else f"{family_name};{postscript_name}"

    if "name" in font:
        name_table = font["name"]
        remove_name_ids(name_table, {1, 2, 3, 4, 6, 16, 17, 25})
        for platform_id, encoding_id, language_id in ((1, 0, 0), (3, 1, 0x0409)):
            add_name_record(name_table, 1, family_name, platform_id, encoding_id, language_id)
            add_name_record(name_table, 2, "Regular", platform_id, encoding_id, language_id)
            add_name_record(name_table, 3, unique_id, platform_id, encoding_id, language_id)
            add_name_record(name_table, 4, family_name, platform_id, encoding_id, language_id)
            add_name_record(name_table, 6, postscript_name, platform_id, encoding_id, language_id)
            add_name_record(name_table, 16, family_name, platform_id, encoding_id, language_id)
            add_name_record(name_table, 17, "Regular", platform_id, encoding_id, language_id)

    if "OS/2" in font:
        font["OS/2"].usWeightClass = weight


def make_static_instance(input_ttf: Path, output_ttf: Path, weight: int) -> None:
    """Summary: Build one static TTF instance from a variable TTF.

    Args:
        input_ttf: Input variable TTF path.
        output_ttf: Output static TTF path.
        weight: Target weight value for the `wght` axis.

    Returns:
        None

    Raises:
        RuntimeError: If the variable font cannot be instantiated.

    Example:
        make_static_instance(Path("_output/font.ttf"), Path("_tmp/font-W300.ttf"), 300)
    """

    output_ttf.parent.mkdir(parents=True, exist_ok=True)
    family_name = f"{input_ttf.stem}-W{weight}"
    try:
        with TTFont(str(input_ttf)) as variable_font:
            static_font = instantiateVariableFont(variable_font, {"wght": float(weight)}, inplace=False)
            apply_static_metadata(static_font, family_name, weight)
            static_font.save(str(output_ttf))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to build static instance wght={weight}: {exc}") from exc
    print(f"Done: {output_ttf}")


def build_default_instances(input_ttf: Path, output_dir: Path) -> None:
    """Summary: Build default static instances from a variable TTF.

    Args:
        input_ttf: Input variable TTF path.
        output_dir: Output directory path.

    Returns:
        None

    Example:
        build_default_instances(Path("_output/font.ttf"), Path("_tmp/static"))
    """

    base_name = input_ttf.stem
    for weight in DEFAULT_WEIGHTS:
        output_ttf = output_dir / f"{base_name}-W{weight}.ttf"
        make_static_instance(input_ttf, output_ttf, weight)


def validate_args(input_ttf: Path, output_dir: Path) -> None:
    """Summary: Validate CLI paths before building static instances.

    Args:
        input_ttf: Input variable TTF path.
        output_dir: Output directory path.

    Returns:
        None

    Raises:
        ValueError: If any input path is invalid.

    Example:
        validate_args(Path("_output/font.ttf"), Path("_tmp/static"))
    """

    if not input_ttf.exists() or not input_ttf.is_file():
        raise ValueError(f"-input must be an existing file: {input_ttf}")
    if input_ttf.suffix.lower() != ".ttf":
        raise ValueError(f"-input must be a .ttf file: {input_ttf}")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"-output-dir must be a directory path: {output_dir}")


def main() -> int:
    """Summary: Run the static instance build CLI.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()
    input_ttf = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    try:
        validate_args(input_ttf, output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        build_default_instances(input_ttf, output_dir)
        return 0
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
