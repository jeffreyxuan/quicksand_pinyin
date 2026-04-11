#!/usr/bin/env python3
"""Build static-weight TTF instances from a variable font."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.varLib.instancer import instantiateVariableFont

MIN_ALLOWED_WEIGHT = 100
MAX_ALLOWED_WEIGHT = 900
DEFAULT_WEIGHT_STEP = 50


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


def parse_bool_arg(value: str) -> bool:
    """Summary: Parse a CLI boolean value.

    Args:
        value: Raw CLI string.

    Returns:
        bool: Parsed boolean value.

    Raises:
        argparse.ArgumentTypeError: If the value is not a supported boolean string.

    Example:
        parse_bool_arg("true")
    """

    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Example:
        python make_static_instances.py -input _output/ToneOZ-Quicksnow.ttf -output-dir _tmp/static
    """

    parser = argparse.ArgumentParser(description="Build static instances from a variable TTF.")
    parser.add_argument("-input", required=True, help="Input variable TTF path")
    parser.add_argument("-output-dir", required=True, help="Output directory for static TTFs")
    parser.add_argument(
        "-start",
        type=int,
        default=300,
        help="Start weight for output instances (default: 300)",
    )
    parser.add_argument(
        "-end",
        type=int,
        default=700,
        help="End weight for output instances (default: 700)",
    )
    parser.add_argument(
        "-step",
        type=int,
        default=DEFAULT_WEIGHT_STEP,
        help=f"Weight step for output instances (default: {DEFAULT_WEIGHT_STEP})",
    )
    parser.add_argument(
        "-merge-glyf",
        type=parse_bool_arg,
        default=True,
        help="Whether to merge simple glyf overlaps while keeping composite references (default: true)",
    )
    return parser.parse_args()


def iter_output_weights(start_weight: int, end_weight: int, step_weight: int) -> list[int]:
    """Summary: Build the inclusive output weight list.

    Args:
        start_weight: Minimum weight to output.
        end_weight: Maximum weight to output.
        step_weight: Step between output weights.

    Returns:
        list[int]: Output weights from start to end using a fixed step.

    Example:
        iter_output_weights(100, 200, 50)
    """

    return list(range(start_weight, end_weight + 1, step_weight))


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


def merge_simple_glyf_overlaps(font: TTFont) -> None:
    """Summary: Merge overlaps for simple glyf glyphs while preserving composite references.

    Args:
        font: Static TTFont instance to simplify in place.

    Returns:
        None

    Raises:
        RuntimeError: If the overlap-removal dependency is unavailable.

    Example:
        merge_simple_glyf_overlaps(font)
    """

    if "glyf" not in font:
        return

    try:
        from fontTools.ttLib.removeOverlaps import removeOverlaps
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "merge_glyf=True requires the optional dependency 'skia-pathops' "
            "(used by fontTools.ttLib.removeOverlaps)"
        ) from exc

    glyf_table = font["glyf"]
    simple_glyph_names = [
        glyph_name
        for glyph_name in font.getGlyphOrder()
        if (
            glyph_name in glyf_table
            and not glyf_table[glyph_name].isComposite()
            and glyf_table[glyph_name].numberOfContours > 0
        )
    ]
    if not simple_glyph_names:
        return

    removeOverlaps(font, glyphNames=simple_glyph_names, removeHinting=True, ignoreErrors=False)


def make_static_instance(input_ttf: Path, output_ttf: Path, weight: int, merge_glyf: bool = True) -> None:
    """Summary: Build one static TTF instance from a variable TTF.

    Args:
        input_ttf: Input variable TTF path.
        output_ttf: Output static TTF path.
        weight: Target weight value for the `wght` axis.
        merge_glyf: Whether to merge simple glyf overlaps while preserving composite references.

    Returns:
        None

    Raises:
        RuntimeError: If the variable font cannot be instantiated.

    Example:
        make_static_instance(Path("_output/font.ttf"), Path("_tmp/font-W100.ttf"), 100, True)
    """

    output_ttf.parent.mkdir(parents=True, exist_ok=True)
    family_name = f"{input_ttf.stem}-W{weight}"
    try:
        with TTFont(str(input_ttf)) as variable_font:
            static_font = instantiateVariableFont(variable_font, {"wght": float(weight)}, inplace=False)
            apply_static_metadata(static_font, family_name, weight)
            if merge_glyf:
                merge_simple_glyf_overlaps(static_font)
            static_font.save(str(output_ttf))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to build static instance wght={weight}: {exc}") from exc
    print(f"Done: {output_ttf}")


def build_default_instances(
    input_ttf: Path,
    output_dir: Path,
    start_weight: int = 300,
    end_weight: int = 700,
    step_weight: int = DEFAULT_WEIGHT_STEP,
    merge_glyf: bool = True,
) -> None:
    """Summary: Build default static instances from a variable TTF.

    Args:
        input_ttf: Input variable TTF path.
        output_dir: Output directory path.
        start_weight: Minimum weight to output.
        end_weight: Maximum weight to output.
        step_weight: Step between output weights.
        merge_glyf: Whether to merge simple glyf overlaps while preserving composite references.

    Returns:
        None

    Example:
        build_default_instances(Path("_output/font.ttf"), Path("_tmp/static"), 400, 600, 50, True)
    """

    base_name = input_ttf.stem
    for weight in iter_output_weights(start_weight, end_weight, step_weight):
        output_ttf = output_dir / f"{base_name}-W{weight}.ttf"
        make_static_instance(input_ttf, output_ttf, weight, merge_glyf=merge_glyf)


def validate_args(
    input_ttf: Path,
    output_dir: Path,
    start_weight: int,
    end_weight: int,
    step_weight: int,
) -> None:
    """Summary: Validate CLI paths before building static instances.

    Args:
        input_ttf: Input variable TTF path.
        output_dir: Output directory path.
        start_weight: Minimum weight to output.
        end_weight: Maximum weight to output.
        step_weight: Step between output weights.

    Returns:
        None

    Raises:
        ValueError: If any input path is invalid.

    Example:
        validate_args(Path("_output/font.ttf"), Path("_tmp/static"), 300, 700, 50)
    """

    if not input_ttf.exists() or not input_ttf.is_file():
        raise ValueError(f"-input must be an existing file: {input_ttf}")
    if input_ttf.suffix.lower() != ".ttf":
        raise ValueError(f"-input must be a .ttf file: {input_ttf}")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"-output-dir must be a directory path: {output_dir}")
    if start_weight < MIN_ALLOWED_WEIGHT:
        raise ValueError(f"-start must be >= {MIN_ALLOWED_WEIGHT}")
    if end_weight > MAX_ALLOWED_WEIGHT:
        raise ValueError(f"-end must be <= {MAX_ALLOWED_WEIGHT}")
    if start_weight > end_weight:
        raise ValueError("-start must be less than or equal to -end")
    if step_weight <= 0:
        raise ValueError("-step must be > 0")
    if start_weight % step_weight != 0:
        raise ValueError(f"-start must be a multiple of -step ({step_weight})")
    if end_weight % step_weight != 0:
        raise ValueError(f"-end must be a multiple of -step ({step_weight})")


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
    start_weight = int(args.start)
    end_weight = int(args.end)
    step_weight = int(args.step)
    merge_glyf = bool(args.merge_glyf)

    try:
        validate_args(input_ttf, output_dir, start_weight, end_weight, step_weight)
        output_dir.mkdir(parents=True, exist_ok=True)
        build_default_instances(
            input_ttf,
            output_dir,
            start_weight,
            end_weight,
            step_weight,
            merge_glyf=merge_glyf,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
